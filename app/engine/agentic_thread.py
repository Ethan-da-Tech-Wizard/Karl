import logging
import os
import time
import psutil
import re
import threading
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.hot_reload import compile_and_reload
from app.engine.model_loader import CircuitBreakerOpenException, ModelLoader
from app.engine.kv_cache import kv_cache_stats, log_cache_stats
from app.engine.event_broker import EventBroker
from app.utils.trace_logger import TraceLogger
import core.interaction_loop
import core.agentic_loop

RAW_LOG_DIR = "data/logs/raw"

# Reserve this many tokens for the next generation's output.
# The rest of the budget is used for history.
_RESPONSE_RESERVE = 1024  # max_tokens headroom
_WATCHDOG_TIMEOUT_SECONDS = 30.0
_WATCHDOG_ERROR = (
    "Inference Watchdog Timeout: Token generation froze for more than 30s. "
    "Inference terminated safely."
)

logger = logging.getLogger("karl.agentic_thread")

# Set to True on Stage 3 emergency; cleared when GPU cools below 85°C.
_thermal_suspended: bool = False


def _get_gpu_temp() -> float | None:
    """Return the hottest GPU temp across all NVML-monitored GPUs, or None."""
    try:
        from core.hardware_scout import get_hardware_profile
        temps = [
            g["temperature_c"]
            for g in get_hardware_profile().get("gpu_list", [])
            if "temperature_c" in g
        ]
        return max(temps) if temps else None
    except Exception:
        return None


class AgenticThread(QThread):
    """
    Runs Karl in autonomous agentic mode.
    It loops: generate → parse → check stop condition → inject next prompt → repeat.
    The hackable stop condition and next-prompt logic live in core/agentic_loop.py.
    """
    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)                  # M7: every character pre-parser
    # iteration_index, thought, response, diagnostics
    iteration_finished = pyqtSignal(int, str, str, dict)
    live_stats = pyqtSignal(int, float)
    loop_finished = pyqtSignal(int)
    reload_notice = pyqtSignal(str)   # module name that was hot-reloaded
    error_occurred = pyqtSignal(str)
    context_stats = pyqtSignal(int, int, int, int)  # prompt_tokens, history_tokens, rag_tokens, budget
    status_update = pyqtSignal(str, bool)           # (text, active)

    def __init__(self, system_prompt, initial_history, hyperparams,
                 retrieved_chunks=None, workflow="general_chat",
                 template="reasoning_minimal", adapter_name=None, model_name=None):
        """Create an autonomous generation loop worker.

        Args:
            system_prompt: Base system prompt for each iteration.
            initial_history: Starting role/content messages copied into the loop.
            hyperparams: Inference parameters and optional watchdog timeout.
            retrieved_chunks: Optional RAG chunks injected into prompts.
            workflow: Trace workflow name.
            template: Trace prompt template name.
            adapter_name: Optional LoRA adapter for ModelLoader.
            model_name: Optional display/trace model name override.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = list(initial_history)   # copy so we can mutate safely
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.workflow = workflow
        self.template = template
        self.adapter_name = adapter_name
        self.model_name = model_name
        self.logger = TraceLogger()
        self._stop_requested = False
        self.watchdog_timeout_seconds = float(
            self.hyperparams.get("watchdog_timeout_seconds", _WATCHDOG_TIMEOUT_SECONDS)
        )
        self.last_token_timestamp = time.time()
        self._watchdog_timed_out = False
        self._watchdog_error_emitted = False
        self._watchdog_stop = threading.Event()
        self._active_response_generator = None

    def request_stop(self):
        """Request cooperative cancellation and stop the watchdog."""
        self._stop_requested = True
        self._watchdog_stop.set()

    def _mark_token_activity(self):
        self.last_token_timestamp = time.time()

    def _emit_watchdog_timeout(self):
        if self._watchdog_error_emitted:
            return
        self._watchdog_error_emitted = True
        self.error_occurred.emit(_WATCHDOG_ERROR)

    def _cleanup_after_watchdog_timeout(self, llm=None):
        self._stop_requested = True
        self._watchdog_timed_out = True
        self._emit_watchdog_timeout()
        generator = self._active_response_generator
        close_fn = getattr(generator, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass
        reset_fn = getattr(llm, "reset", None)
        if callable(reset_fn):
            try:
                reset_fn()
            except Exception:
                pass

    def _start_watchdog(self, llm=None) -> threading.Thread:
        self._watchdog_stop.clear()
        self._watchdog_timed_out = False
        self._watchdog_error_emitted = False
        self._mark_token_activity()

        def _monitor():
            while not self._watchdog_stop.wait(0.25):
                if self._stop_requested:
                    return
                if time.time() - self.last_token_timestamp > self.watchdog_timeout_seconds:
                    self._cleanup_after_watchdog_timeout(llm)
                    return

        thread = threading.Thread(target=_monitor, name="karl-agentic-watchdog", daemon=True)
        thread.start()
        return thread

    def _stop_watchdog(self, thread: threading.Thread | None):
        self._watchdog_stop.set()
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

    def _token_count(self, llm, text: str) -> int:
        if not text:
            return 0
        try:
            return len(llm.tokenize(text.encode("utf-8"), add_bos=False))
        except TypeError:
            return len(llm.tokenize(text.encode("utf-8")))
        except Exception as exc:
            logger.warning("Tokenizer count failed; falling back to character estimate: %s", exc)
            return max(1, len(text) // 3)

    def _message_token_count(self, llm, msg) -> int:
        role = msg.get("role", "")
        content = msg.get("content", "")
        return self._token_count(llm, f"<|im_start|>{role}\n{content}<|im_end|>\n")

    def _strip_historical_thoughts(self, history, llm, budget):
        """
        Iterates through history (oldest to newest) and strips <think> blocks
        from assistant turns until the total token count fits the budget.
        Always preserves the very last assistant turn's thoughts if it exists.
        """
        # Find all assistant turns with think blocks, except the most recent one
        assistant_indices = []
        for i, msg in enumerate(history):
            if msg.get("role") == "assistant" and "<think>" in msg.get("content", "") and "</think>" in msg.get("content", ""):
                assistant_indices.append(i)
        
        if not assistant_indices:
            return history
            
        # Don't strip the most recent one to maintain active reasoning continuity
        targets = assistant_indices[:-1]
        
        optimized_history = list(history)
        
        for idx in targets:
            # Check current total
            total = sum(self._message_token_count(llm, m) for m in optimized_history)
            if total <= budget:
                break
                
            content = optimized_history[idx]["content"]
            # Strip <think>...</think> including the tags
            new_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            optimized_history[idx] = {**optimized_history[idx], "content": new_content}
            
        return optimized_history

    def _trim_history(self, history, system_prompt, llm):
        """
        Trims the chat history so the compiled prompt stays inside the context budget.
        
        1. Cognitive Context Pruning: strips <think> blocks from old assistant turns
        2. Standard Trimming: drops oldest messages until history fits in the budget
        
        Always keeps the first user message (the seed) and the most recent turns.
        """
        context_budget = ModelLoader.context_limit()
        base_tokens = self._token_count(llm, system_prompt)
        budget = max(256, context_budget - _RESPONSE_RESERVE - base_tokens)

        # ── Phase 1: Cognitive Context Pruning ───────────────────────────────
        # Strip older thoughts first to reclaim space while keeping dialogue turns
        processed = self._strip_historical_thoughts(history, llm, budget)

        # ── Phase 2: Standard Trimming ───────────────────────────────────────
        # Walk backwards through history accumulating tokenizer-measured size.
        # Always keep at least the first message (index 0) as the seed.
        kept = []
        running = 0
        for msg in reversed(processed):
            entry_len = self._message_token_count(llm, msg)
            if running + entry_len > budget and kept:
                break  # Stop adding older messages
            kept.insert(0, msg)
            running += entry_len

        # Always preserve seed (first message)
        if history and history[0] not in kept:
            kept.insert(0, history[0])

        if len(kept) < len(history):
            self.new_thought_token.emit(
                f"\n[Context Trim: kept {len(kept)}/{len(history)} messages to fit context window]\n"
            )
        return kept

    def _run_single_generation(self, llm, prompt, raw_file, thermal_enabled: bool = False):
        """Runs streaming generation, continuing automatically if truncated."""
        global _thermal_suspended
        raw_output = ""
        parsed_thought = ""
        parsed_response = ""
        # Prompt pre-seeds <think>\n -- always start in thought mode
        in_thought = True
        buffer = ""
        first_token_time = None
        gen_token_count = 0

        continuation_count = 0
        max_continuations = 5
        compression_reset_count = 0
        max_compression_resets = 2
        state_transitioned = False

        # Snapshot cache state and wall-clock start before the first generation.
        _init_cache_stats = kv_cache_stats(llm, prompt)
        _gen_start = time.perf_counter()

        while continuation_count <= max_continuations:
            # Stage 3 emergency check at each continuation boundary
            if thermal_enabled:
                _ct = _get_gpu_temp()
                if _ct is not None and _ct >= 100.0:
                    _thermal_suspended = True
                    raise RuntimeError(
                        f"Emergency Thermal Suspension: GPU reached {_ct:.1f}°C."
                    )

            # Dynamic Parameter Scheduling
            current_temp = self.hyperparams.get("temperature", 0.7)
            current_top_p = self.hyperparams.get("top_p", 0.95)
            
            if self.hyperparams.get("enable_dynamic_scheduling", True):
                if in_thought:
                    current_temp = self.hyperparams.get("thinking_temperature", 0.8)
                else:
                    current_temp = self.hyperparams.get("answering_temperature", 0.1)
                    current_top_p = 0.1 # High precision for answering

            response_gen = llm(
                prompt + raw_output,
                max_tokens=self.hyperparams.get("max_tokens", 2048),
                temperature=current_temp,
                top_p=current_top_p,
                repeat_penalty=1.1,
                stream=True,
                stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"],
                echo=False
            )
            self._active_response_generator = response_gen
            watchdog_thread = self._start_watchdog(llm)

            finish_reason = "stop"
            has_tokens = False
            state_transitioned = False

            try:
                for chunk in response_gen:
                    if self._watchdog_timed_out or self._stop_requested:
                        break
                    if 'choices' not in chunk or not chunk['choices']:
                        continue

                    choice = chunk['choices'][0]
                    fr = choice.get('finish_reason')
                    if fr is not None:
                        finish_reason = fr

                    text = choice.get('text', '')
                    if not text:
                        continue

                    self._mark_token_activity()

                    if first_token_time is None:
                        first_token_time = time.perf_counter()

                    chunk_tokens = len(llm.tokenize(text.encode('utf-8'), add_bos=False))
                    gen_token_count += chunk_tokens
                    elapsed = time.perf_counter() - first_token_time
                    speed = gen_token_count / elapsed if elapsed > 0 else 0.0
                    self.live_stats.emit(gen_token_count, speed)

                    has_tokens = True
                    raw_output += text
                    buffer += text

                    # M7: write raw token before parsing
                    micro_ts = f"{time.time():.6f}"
                    raw_file.write(f"{micro_ts}\t{text}\n")
                    raw_file.flush()
                    self.new_raw_token.emit(text)
                    EventBroker.get_instance().publish("tokens:raw", {"token": text})

                    if "<think>" in buffer and not in_thought:
                        in_thought = True
                        pre_think = buffer.split("<think>")[0]
                        if pre_think:
                            self.new_chat_token.emit(pre_think)
                            EventBroker.get_instance().publish("tokens:chat", {"token": pre_think})
                            parsed_response += pre_think
                        buffer = buffer.split("<think>", 1)[1]

                    if in_thought and "</think>" in buffer:
                        in_thought = False
                        parts = buffer.split("</think>", 1)
                        if parts[0]:
                            self.new_thought_token.emit(parts[0])
                            EventBroker.get_instance().publish("tokens:thought", {"token": parts[0]})
                            parsed_thought += parts[0]
                        buffer = parts[1]

                        if self.hyperparams.get("enable_dynamic_scheduling", True):
                            logger.info("Agentic Dynamic Scheduler: detected </think>, switching to ANSWERING profile")
                            state_transitioned = True
                            break

                    _OPEN_GUARDS  = ["<", "<t", "<th", "<thi", "<thin", "<think"]
                    _CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]

                    if in_thought:
                        if not any(buffer.endswith(s) for s in _CLOSE_GUARDS):
                            self.new_thought_token.emit(buffer)
                            EventBroker.get_instance().publish("tokens:thought", {"token": buffer})
                            parsed_thought += buffer
                            buffer = ""
                    else:
                        if not any(buffer.endswith(s) for s in _OPEN_GUARDS):
                            self.new_chat_token.emit(buffer)
                            EventBroker.get_instance().publish("tokens:chat", {"token": buffer})
                            parsed_response += buffer
                            buffer = ""
            finally:
                self._stop_watchdog(watchdog_thread)
                _close_fn = getattr(response_gen, "close", None)
                if callable(_close_fn):
                    _close_fn()
                self._active_response_generator = None

            if self._watchdog_timed_out:
                break

            if self._stop_requested:
                break

            if state_transitioned:
                continue

            if finish_reason != "length" or not has_tokens:
                break

            # Check if we need to do cognitive roll-up compression
            current_tokens_count = len(llm.tokenize((prompt + raw_output).encode('utf-8')))
            context_budget = ModelLoader.context_limit()
            
            compressed = False
            if current_tokens_count > 0.8 * context_budget and parsed_thought:
                self.new_thought_token.emit("\n[Context full — compressing cognitive state...]\n")
                try:
                    compress_prompt = (
                        "<|im_start|>system\n"
                        "You are a cognitive compression tool. Summarize the reasoning steps, calculations, "
                        "and findings established in the thinking process below. Write a dense, concise summary "
                        "in one short paragraph so that the reasoning can proceed from that point. "
                        "Do not solve the problem yourself, just summarize the current train of thought.\n"
                        f"Thinking process to summarize:\n{parsed_thought}\n<|im_end|>\n"
                        "<|im_start|>assistant\n"
                        "<think>\n"
                    )
                    comp_res = llm(
                        compress_prompt,
                        max_tokens=300,
                        temperature=0.1,
                        stop=["</think>", "<|im_end|>"],
                        echo=False
                    )
                    summary = comp_res['choices'][0]['text'].strip()
                    summary = summary.replace("<think>", "").replace("</think>", "")
                    
                    parsed_thought = f"[Summary of thoughts so far: {summary}]"
                    raw_output = f"<think>\n{parsed_thought}\n"
                    in_thought = True # Resume in thought mode
                    compressed = True
                    self.new_thought_token.emit(f"\n[Compressed state: {parsed_thought}]\n")
                except Exception as ce:
                    logger.warning("Cognitive compression failed: %s", ce)
                    self.new_thought_token.emit("\n[continuing...]\n")
            else:
                self.new_thought_token.emit("\n[continuing...]\n")
            
            if compressed and compression_reset_count < max_compression_resets:
                compression_reset_count += 1
                continuation_count = 0
            else:
                if compressed:
                    self.new_thought_token.emit("\n[Compression reset limit reached — continuing with normal continuation budget.]\n")
                continuation_count += 1

        # flush remainder
        if buffer:
            if in_thought:
                self.new_thought_token.emit(buffer)
                EventBroker.get_instance().publish("tokens:thought", {"token": buffer})
                parsed_thought += buffer
            else:
                self.new_chat_token.emit(buffer)
                EventBroker.get_instance().publish("tokens:chat", {"token": buffer})
                parsed_response += buffer

        # Log KV-cache hit statistics now that we have TTFT.
        _ttft_ms = (
            round((first_token_time - _gen_start) * 1000, 2)
            if first_token_time is not None
            else None
        )
        _ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        log_cache_stats({**_init_cache_stats, "ttft_ms": _ttft_ms}, _ts)

        return raw_output, parsed_thought, parsed_response, first_token_time

    def run(self):
        """Run iterative generation until stop condition, max iterations, or error.

        CircuitBreakerOpenException is converted into error_occurred with the
        operator-facing circuit-breaker message.
        """
        # ── CPU Core Pinning ──────────────────────────────────────────────────
        # Pin inference to physical cores to optimize TPS.
        original_affinity = None
        try:
            original_affinity = psutil.Process().cpu_affinity()
            p_count = psutil.cpu_count(logical=False)
            if p_count:
                physical_cores = list(range(p_count))
                psutil.Process().cpu_affinity(physical_cores)
                logger.debug(f"AgenticThread pinned to physical cores: {physical_cores}")
        except Exception as e:
            logger.warning(f"Could not set CPU affinity: {e}")

        try:
            core.interaction_loop = compile_and_reload(
                core.interaction_loop,
                "core/interaction_loop.py",
                self.reload_notice.emit,
                logger,
            )
            core.agentic_loop = compile_and_reload(
                core.agentic_loop,
                "core/agentic_loop.py",
                self.reload_notice.emit,
                logger,
            )

            model_path = None
            if self.model_name:
                model_path = os.path.join("data", "models", self.model_name)
            llm = ModelLoader.acquire_instance(model_path=model_path, adapter_name=self.adapter_name)
            
            # Fetch the actual (potentially fallback-scaled) context limit
            actual_context_budget = ModelLoader.context_limit()

            iteration = 0

            global _thermal_suspended
            while not self._stop_requested:
                # ── Thermal config & hysteresis gate ─────────────────────────────
                from app.engine import config_store
                cfg = config_store.get_ui_config()
                thermal_enabled = cfg.get("thermal_protection_enabled", True)

                if thermal_enabled and _thermal_suspended:
                    t = _get_gpu_temp()
                    if t is None or t >= 85.0:
                        raise RuntimeError(
                            f"GPU thermal suspension active ({t}°C). "
                            "Generation blocked until GPU cools below 85°C."
                        )
                    _thermal_suspended = False
                # ─────────────────────────────────────────────────────────────────

                # Build and emit iteration header
                self.new_thought_token.emit(f"\n{'='*40}\n[AGENTIC LOOP — Iteration {iteration + 1}]\n{'='*40}\n")
                self.new_chat_token.emit(f"\n[Iteration {iteration + 1}]\n")

                # Inject RAG context into system prompt if present
                system_prompt = self.system_prompt
                context_str = "(No context retrieved.)"
                if self.retrieved_chunks:
                    context_str = "\n".join(self.retrieved_chunks)
                    if "{rag_context}" in system_prompt:
                        system_prompt = system_prompt.replace("{rag_context}", context_str)
                    else:
                        system_prompt += "\n\nRetrieved Context:\n" + context_str

                # Trim history to fit context before building prompt
                trimmed_history = self._trim_history(self.chat_history, system_prompt, llm)
                prompt = core.interaction_loop.build_prompt(system_prompt, trimmed_history)

                # Emit context budget stats for the HUD
                try:
                    hist_tokens = sum(self._message_token_count(llm, m) for m in trimmed_history)
                    rag_tokens  = self._token_count(llm, context_str) if self.retrieved_chunks else 0
                    sys_tokens  = self._token_count(llm, system_prompt)
                    self.context_stats.emit(sys_tokens + hist_tokens + rag_tokens, hist_tokens, rag_tokens, actual_context_budget)
                except Exception:
                    pass

                # Tokenize prompt to get accurate prompt token count
                prompt_tokens = len(llm.tokenize(prompt.encode('utf-8')))

                start = time.perf_counter()
                # M7: open raw archive file for this iteration
                os.makedirs(RAW_LOG_DIR, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                raw_log_path = os.path.join(RAW_LOG_DIR, f"agentic_{ts}_iter{iteration}.tokens")
                with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                    raw, thought, response, first_token_time = self._run_single_generation(
                        llm, prompt, raw_file, thermal_enabled=thermal_enabled
                    )
                end = time.perf_counter()

                prefill_time = (first_token_time - start) if first_token_time is not None else (end - start)
                if prefill_time <= 0:
                    prefill_time = 0.001
                prefill_tps = prompt_tokens / prefill_time

                generation_time = (end - first_token_time) if first_token_time is not None else 0.0
                generation_tokens = len(llm.tokenize(raw.encode('utf-8'), add_bos=False))
                if generation_time <= 0:
                    generation_tps = generation_tokens / 0.001 if generation_tokens > 0 else 0.0
                else:
                    generation_tps = generation_tokens / generation_time

                total_time = end - start
                total_tokens = prompt_tokens + generation_tokens
                total_tps = total_tokens / total_time if total_time > 0 else 0.0

                diagnostics = {
                    "prompt_tokens": prompt_tokens,
                    "prefill_time": prefill_time,
                    "prefill_tps": prefill_tps,
                    "generation_tokens": generation_tokens,
                    "generation_time": generation_time,
                    "generation_tps": generation_tps,
                    "total_time": total_time,
                    "total_tps": total_tps,
                }

                if self._stop_requested:
                    break

                gpu_temp = _get_gpu_temp()
                throttle_reasons = []
                try:
                    from core.hardware_scout import get_hardware_profile
                    for gpu in get_hardware_profile().get("gpu_list", []):
                        for alert in gpu.get("alerts", []):
                            if alert not in throttle_reasons:
                                throttle_reasons.append(alert)
                except Exception:
                    pass

                cooling_duration = 0.0
                # ── Multi-Stage Thermal Cooldown ──────────────────────────────────
                if thermal_enabled and gpu_temp is not None:
                    cooling_start = time.perf_counter()
                    if gpu_temp >= 100.0:
                        _thermal_suspended = True
                        raise RuntimeError(
                            f"Emergency Thermal Suspension: GPU reached {gpu_temp:.1f}°C."
                        )
                    elif gpu_temp >= 98.0:
                        self.status_update.emit(
                            f"GPU temperature critical ({gpu_temp:.1f}°C). Cooling down for 15s...", True
                        )
                        for _ in range(150):
                            if self._stop_requested:
                                break
                            time.sleep(0.1)
                        cooling_duration = time.perf_counter() - cooling_start
                        self.status_update.emit("idle", False)
                    elif gpu_temp >= 95.0:
                        self.status_update.emit(
                            f"GPU temperature hot ({gpu_temp:.1f}°C). Cooling down for 5s...", True
                        )
                        for _ in range(50):
                            if self._stop_requested:
                                break
                            time.sleep(0.1)
                        cooling_duration = time.perf_counter() - cooling_start
                        self.status_update.emit("idle", False)
                # ─────────────────────────────────────────────────────────────────

                # Log this iteration
                self.logger.log_generation(
                    compiled_prompt=prompt,
                    hyperparams=self.hyperparams,
                    raw_output=raw,
                    parsed_thought=thought,
                    parsed_response=response,
                    execution_time=total_time,
                    rag_context=self.retrieved_chunks,
                    model_name=ModelLoader.model_name(),
                    adapter_name=getattr(ModelLoader, '_active_adapter', None),
                    workflow=self.workflow,
                    template=self.template,
                    diagnostics=diagnostics,
                    gpu_temp_c=gpu_temp,
                    throttle_reasons=throttle_reasons,
                    cooling_duration_sec=cooling_duration,
                )

                # Store only the response — not the think block — to keep context lean
                self.chat_history.append({"role": "assistant", "content": response})

                self.iteration_finished.emit(iteration, thought, response, diagnostics)
                EventBroker.get_instance().publish("iteration:finished", {
                    "iteration": iteration,
                    "thought": thought,
                    "response": response,
                    "diagnostics": diagnostics
                })

                iteration += 1

                # Hot-reload stop condition and check it
                core.agentic_loop = compile_and_reload(
                    core.agentic_loop,
                    "core/agentic_loop.py",
                    self.reload_notice.emit,
                    logger,
                )
                if not core.agentic_loop.should_continue(iteration, response):
                    break

                # Build next user turn and inject it
                next_prompt_content = core.agentic_loop.build_next_prompt(response, iteration)
                self.chat_history.append({"role": "user", "content": next_prompt_content})

            self.loop_finished.emit(iteration)
            EventBroker.get_instance().publish("loop:finished", {
                "total_iterations": iteration
            })

        except CircuitBreakerOpenException as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"Agentic Error: {str(e)}")
        finally:
            ModelLoader.unlock_instance()
            # Restore original CPU affinity
            if original_affinity:
                try:
                    psutil.Process().cpu_affinity(original_affinity)
                except Exception as e:
                    logger.debug(f"Could not restore CPU affinity: {e}")
