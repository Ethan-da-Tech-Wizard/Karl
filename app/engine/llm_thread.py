import json
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
from app.engine.task_supervisor import TaskSupervisor
from app.engine.streaming_parser import StreamingThoughtParser
from app.utils.trace_logger import TraceLogger
import core.interaction_loop

RAW_LOG_DIR = "data/logs/raw"
_PERF_LOG = "data/logs/performance_telemetry.jsonl"
_PERF_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB rotation threshold
_RESPONSE_RESERVE = 1024
_MAX_MSG_CHARS = 100000   # Truncate any single message to this length before it enters the prompt

_WATCHDOG_TIMEOUT_SECONDS = 30.0
_WATCHDOG_ERROR = (
    "Inference Watchdog Timeout: Token generation froze for more than 30s. "
    "Inference terminated safely."
)


logger = logging.getLogger("karl.llm_thread")

# Set to True on Stage 3 emergency; cleared when GPU cools below 85°C.
_thermal_suspended: bool = False


def _free_vram_mb() -> float | None:
    """Return the minimum free VRAM across all GPUs, or None if unavailable."""
    try:
        from core.hardware_scout import get_hardware_profile
        gpus = get_hardware_profile().get("gpu_list", [])
        if not gpus:
            return None
        return min(g.get("memory_free_mb", float("inf")) for g in gpus)
    except Exception:
        return None


def _write_performance_telemetry(entry: dict) -> None:
    """
    Append a structured JSONL entry to the performance telemetry log.
    Rotates the log file to .1 when it reaches 5 MB to limit disk overhead.
    """
    try:
        os.makedirs("data/logs", exist_ok=True)
        if os.path.exists(_PERF_LOG) and os.path.getsize(_PERF_LOG) >= _PERF_LOG_MAX_BYTES:
            rotated = _PERF_LOG + ".1"
            if os.path.exists(rotated):
                os.remove(rotated)
            os.rename(_PERF_LOG, rotated)
        with open(_PERF_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


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


class LLMThread(QThread):
    """Single-shot inference worker that streams raw, thought, and answer tokens."""

    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)
    # thought, response, truncated, ended_in_thought, diagnostics
    generation_finished = pyqtSignal(str, str, bool, bool, dict)
    live_stats = pyqtSignal(int, float)
    reload_notice = pyqtSignal(str)   # module name that was hot-reloaded
    error_occurred = pyqtSignal(str)
    context_stats = pyqtSignal(int, int, int, int)  # prompt_tokens, history_tokens, rag_tokens, budget
    rag_context_used = pyqtSignal(list)             # List[dict] attribution records
    tool_call_started = pyqtSignal(str, str)        # server_name, tool_name
    status_update = pyqtSignal(str, bool)           # (text, active)

    def __init__(self, system_prompt, chat_history, hyperparams,
                 retrieved_chunks=None, start_in_thought=False,
                 workflow="general_chat", template="reasoning_minimal",
                 adapter_name=None, model_name=None):
        """Create a generation worker.

        Args:
            system_prompt: System prompt passed into core.interaction_loop.
            chat_history: ChatML-style role/content messages.
            hyperparams: Inference parameters including temperature, top_p,
                max_tokens, and optional watchdog_timeout_seconds.
            retrieved_chunks: Optional RAG chunks or attribution dicts.
            start_in_thought: Continue parsing as thought text after a length stop.
            workflow: Trace workflow name.
            template: Trace prompt template name.
            adapter_name: Optional LoRA adapter to load through ModelLoader.
            model_name: Optional GGUF filename override. When provided the thread
                calls ``ModelLoader.get_instance(model_path=...)`` with an
                absolute path under ``data/models/``, allowing custom agent
                profiles to use a different base model without changing the
                global active-model selection.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.start_in_thought = start_in_thought  # True when continuing mid-thought
        self.workflow = workflow
        self.template = template
        self.adapter_name = adapter_name
        self.model_name = model_name  # optional GGUF filename override for custom agents
        self.logger = TraceLogger()
        self.enable_tools = False
        self._stop_requested = False
        self.watchdog_timeout_seconds = float(
            self.hyperparams.get("watchdog_timeout_seconds", _WATCHDOG_TIMEOUT_SECONDS)
        )
        self.last_token_timestamp = time.time()
        self._watchdog_timed_out = False
        self._watchdog_error_emitted = False
        self._watchdog_stop = threading.Event()
        self._active_response_generator = None
        self.task_id: str | None = None

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
        if self.task_id:
            try:
                TaskSupervisor.instance().fail(self.task_id, _WATCHDOG_ERROR)
            except Exception:
                pass
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

        thread = threading.Thread(target=_monitor, name="karl-llm-watchdog", daemon=True)
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
        # Include light ChatML-style overhead so trimming tracks the built prompt
        # more closely than raw content length.
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

    def _trim_history(self, history, llm, system_prompt=""):
        """
        Prepares history for the prompt:
        1. Truncates any individual message > _MAX_MSG_CHARS (keeps the tail)
        2. Cognitive Context Pruning: strips <think> blocks from old assistant turns
        3. Standard Trimming: drops oldest messages until history fits in the budget
        4. Always keeps message[0] (the seed)
        """
        context_budget = ModelLoader.context_limit()
        system_tokens = self._token_count(llm, system_prompt)
        history_token_limit = max(256, context_budget - _RESPONSE_RESERVE - system_tokens)

        def _cap(msg):
            content = msg.get("content", "")
            if len(content) > _MAX_MSG_CHARS:
                content = "[...truncated...] " + content[-_MAX_MSG_CHARS:]
            return {**msg, "content": content}

        capped = [_cap(m) for m in history]
        
        # ── Phase 1: Cognitive Context Pruning ───────────────────────────────
        # Strip older thoughts first to reclaim space while keeping dialogue turns
        processed = self._strip_historical_thoughts(capped, llm, history_token_limit)
        
        # ── Phase 2: Standard Trimming ───────────────────────────────────────
        kept = []
        running = 0
        for msg in reversed(processed):
            entry_len = self._message_token_count(llm, msg)
            if running + entry_len > history_token_limit and kept:
                break
            kept.insert(0, msg)
            running += entry_len
        if capped and capped[0] not in kept:
            kept.insert(0, capped[0])
        return kept

    def _response_reserve(self) -> int:
        try:
            max_tokens = int(self.hyperparams.get("max_tokens", _RESPONSE_RESERVE))
        except Exception:
            max_tokens = _RESPONSE_RESERVE
        return min(max(128, max_tokens), _RESPONSE_RESERVE)

    def _build_prompt_with_context_budget(self, llm, system_prompt: str, history: list[dict]):
        """
        Compile the prompt and enforce a final tokenizer-measured budget.

        _trim_history() is intentionally conservative, but RAG/system prompt
        expansion and a huge seed message can still overflow the loaded context.
        This final pass degrades oldest context first, then truncates the lone
        remaining message/system prompt only as a last resort.
        """
        budget = max(256, ModelLoader.context_limit() - self._response_reserve())
        working_history = [dict(m) for m in history]
        working_system = system_prompt
        changed = False

        def _compile():
            prompt_text = core.interaction_loop.build_prompt(working_system, working_history)
            return prompt_text, self._token_count(llm, prompt_text)

        prompt, tokens = _compile()

        while working_history and tokens > budget:
            if len(working_history) > 1:
                working_history.pop(0)
                changed = True
            else:
                content = working_history[0].get("content", "")
                if len(content) <= 256:
                    break
                keep = max(256, len(content) // 2)
                working_history[0] = {
                    **working_history[0],
                    "content": "[...truncated to fit context...]\n" + content[-keep:],
                }
                changed = True
            prompt, tokens = _compile()

        while tokens > budget and len(working_system) > 512:
            keep = max(512, len(working_system) // 2)
            working_system = (
                working_system[:keep]
                + "\n\n[System/RAG context truncated to fit model context.]"
            )
            changed = True
            prompt, tokens = _compile()

        if changed:
            self.new_thought_token.emit(
                "\n[Context budget: prompt was reduced to fit the loaded model window.]\n"
            )

        return prompt, working_history, working_system, tokens, budget

    def run(self):
        """Load the model, stream tokens, write traces, and emit completion signals.

        CircuitBreakerOpenException is converted into error_occurred with the
        operator-facing circuit-breaker message.
        """
        supervisor = TaskSupervisor.instance()
        if self.task_id is None:
            self.task_id = supervisor.register("LLM generation", cancellable=self)

        # ── CPU Core Pinning ──────────────────────────────────────────────────
        # Pin inference to physical cores to optimize TPS. os.sched_setaffinity(0, ...)
        # targets the calling thread specifically, preventing process-wide races.
        original_affinity = None
        try:
            import os
            import psutil
            if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
                original_affinity = os.sched_getaffinity(0)
                p_count = psutil.cpu_count(logical=False)
                if p_count:
                    physical_cores = list(range(p_count))
                    os.sched_setaffinity(0, physical_cores)
                    logger.debug(f"LLMThread pinned to physical cores: {physical_cores}")
        except Exception as e:
            logger.warning(f"Could not set CPU affinity: {e}")

        # ── Thermal config & hysteresis gate ─────────────────────────────────
        global _thermal_suspended
        from app.engine import config_store
        cfg = config_store.get_ui_config()
        thermal_enabled = cfg.get("thermal_protection_enabled", True)

        if thermal_enabled and _thermal_suspended:
            t = _get_gpu_temp()
            if t is None or t >= 85.0:
                self.error_occurred.emit(
                    f"GPU thermal suspension active ({t}°C). "
                    "Generation blocked until GPU cools below 85°C."
                )
                supervisor.fail(self.task_id, "Thermal suspension active")
                return
            _thermal_suspended = False
        # ─────────────────────────────────────────────────────────────────────

        try:
            core.interaction_loop = compile_and_reload(
                core.interaction_loop,
                "core/interaction_loop.py",
                self.reload_notice.emit,
                logger,
            )

            if self.model_name:
                model_path = os.path.join("data", "models", self.model_name)
                llm = ModelLoader.acquire_instance(
                    model_path=model_path, adapter_name=self.adapter_name
                )
            else:
                llm = ModelLoader.acquire_instance(adapter_name=self.adapter_name)
            
            # Fetch the actual (potentially fallback-scaled) context limit
            actual_context_budget = ModelLoader.context_limit()

            # If retrieved_chunks is list of dicts, format it to list of strings early to prevent TypeError in context_str join
            rag_attribution_chunks = None
            if self.retrieved_chunks and isinstance(self.retrieved_chunks[0], dict):
                rag_attribution_chunks = list(self.retrieved_chunks)
                self.retrieved_chunks = [c["text"] for c in self.retrieved_chunks]

            system_prompt = self.system_prompt
            context_str = "(No context retrieved.)"
            if self.retrieved_chunks:
                context_str = "\n".join(self.retrieved_chunks)
            
            if "{rag_context}" in system_prompt:
                system_prompt = system_prompt.replace("{rag_context}", context_str)
            elif self.retrieved_chunks:
                system_prompt += "\n\nRetrieved Context:\n" + context_str
            trimmed_history = self._trim_history(self.chat_history, llm, system_prompt)
            prompt, trimmed_history, system_prompt, prompt_tokens, _prompt_budget = (
                self._build_prompt_with_context_budget(llm, system_prompt, trimmed_history)
            )

            # Emit context budget stats for the HUD
            try:
                hist_tokens = sum(self._message_token_count(llm, m) for m in trimmed_history)
                rag_tokens  = self._token_count(llm, context_str) if self.retrieved_chunks else 0
                sys_tokens  = self._token_count(llm, system_prompt)
                self.context_stats.emit(sys_tokens + hist_tokens + rag_tokens, hist_tokens, rag_tokens, actual_context_budget)
            except Exception:
                pass

            # Emit RAG attribution if chunks are dicts (post-Prompt-14 format)
            if rag_attribution_chunks is not None:
                self.rag_context_used.emit(rag_attribution_chunks)

            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            # Snapshot cache state BEFORE inference so we can report how many tokens
            # will be served from the KV-cache vs freshly evaluated this turn.
            _init_cache_stats = kv_cache_stats(llm, prompt)
            _vram_before_mb = _free_vram_mb()

            start_time = time.perf_counter()
            first_token_time = None
            gen_token_count = 0
            raw_output = ""
            # Determine starting mode for the streaming parser.
            if self.start_in_thought:
                in_thought = self.start_in_thought  # continuation chains honour explicit flag
            else:
                # If the compiled prompt ends with <think> (ignoring trailing whitespace/newlines),
                # we pre-seeded it, so we start in thought mode.
                in_thought = prompt.rstrip().endswith("<think>")
            parser = StreamingThoughtParser(
                in_thought=in_thought,
                thought_cb=self.new_thought_token.emit,
                chat_cb=self.new_chat_token.emit,
            )
            finish_reason = "stop"

            continuation_count = 0
            max_continuations = 5
            state_transition_count = 0
            max_state_transitions = 3
            compression_reset_count = 0
            max_compression_resets = 2
            state_transitioned = False

            with open(raw_log_path, "w", encoding="utf-8") as raw_file:
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
                        if parser.in_thought:
                            current_temp = self.hyperparams.get("thinking_temperature", 0.8)
                        else:
                            current_temp = self.hyperparams.get("answering_temperature", 0.1)
                            current_top_p = 0.1 # High precision for answering
                    
                    response_generator = llm(
                        prompt + raw_output,
                        max_tokens=self.hyperparams.get("max_tokens", 2048),
                        temperature=current_temp,
                        top_p=current_top_p,
                        repeat_penalty=1.1,
                        stream=True,
                        # <|im_start|> stops the model from hallucinating a new conversation turn
                        stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"],
                        echo=False
                    )
                    self._active_response_generator = response_generator
                    watchdog_thread = self._start_watchdog(llm)

                    finish_reason = "stop"
                    has_tokens = False
                    state_transitioned = False

                    try:
                        for chunk in response_generator:
                            if self._watchdog_timed_out or self._stop_requested:
                                break
                            if 'choices' not in chunk or not chunk['choices']:
                                continue

                            choice = chunk['choices'][0]

                            # Track finish_reason from every chunk (last non-None wins)
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
                            micro_ts = f"{time.time():.6f}"
                            raw_file.write(f"{micro_ts}\t{text}\n")
                            raw_file.flush()
                            self.new_raw_token.emit(text)
                            EventBroker.get_instance().publish("tokens:raw", {"token": text})

                            raw_output += text
                            dynamic_scheduling = self.hyperparams.get("enable_dynamic_scheduling", True)
                            parse_result = parser.feed(
                                text,
                                defer_after_think_close=dynamic_scheduling,
                            )
                            if parse_result.closed_think and dynamic_scheduling:
                                if state_transition_count < max_state_transitions:
                                    logger.info("Dynamic Scheduler: detected </think>, switching to ANSWERING profile")
                                    state_transition_count += 1
                                    state_transitioned = True
                                    break
                                else:
                                    logger.warning("Dynamic Scheduler: max state transitions reached; continuing current generation turn.")
                    finally:
                        self._stop_watchdog(watchdog_thread)
                        close_fn = getattr(response_generator, "close", None)
                        if callable(close_fn):
                            close_fn()
                        self._active_response_generator = None

                    if self._watchdog_timed_out:
                        # _cleanup_after_watchdog_timeout() already called
                        # supervisor.fail() from the watchdog thread; a bare
                        # return here is safe since the task record is already
                        # closed out (fail() is a no-op once status != RUNNING).
                        return

                    if state_transitioned:
                        continue

                    if finish_reason != "length" or not has_tokens:
                        break

                    # Check if we need to do cognitive roll-up compression
                    current_tokens_count = len(llm.tokenize((prompt + raw_output).encode('utf-8')))
                    context_budget = ModelLoader.context_limit()
                    
                    compressed = False
                    if current_tokens_count > 0.8 * context_budget and parser.parsed_thought:
                        self.new_thought_token.emit("\n[Context full — compressing cognitive state...]\n")
                        try:
                            compress_prompt = (
                                "<|im_start|>system\n"
                                "You are a cognitive compression tool. Summarize the reasoning steps, calculations, "
                                "and findings established in the thinking process below. Write a dense, concise summary "
                                "in one short paragraph so that the reasoning can proceed from that point. "
                                "Do not solve the problem yourself, just summarize the current train of thought.\n"
                                f"Thinking process to summarize:\n{parser.parsed_thought}\n<|im_end|>\n"
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
                            
                            parser.parsed_thought = f"[Summary of thoughts so far: {summary}]"
                            parser.buffer = ""
                            raw_output = f"<think>\n{parser.parsed_thought}\n"
                            parser.in_thought = True # Resume in thought mode
                            compressed = True
                            self.new_thought_token.emit(f"\n[Compressed state: {parser.parsed_thought}]\n")
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

            # Flush remainder
            parser.flush()

            # MCP Tool loop — if enabled and model emitted tool calls, execute and continue
            if self.enable_tools:
                from app.engine.tool_executor import parse_tool_calls, execute_tool_calls
                from app.engine.mcp_client import MCPClientManager
                MAX_TOOL_TURNS = 5
                tool_turn = 0
                executed_calls = set()
                # Allow-list of (server, tool) pairs actually offered to the model.
                # parse_tool_calls() scans the *entire* generated text, which can
                # include content copied verbatim from RAG-retrieved documents --
                # without this check, a document containing a forged <tool_call>
                # tag would get executed as an indirect prompt injection.
                try:
                    allowed_tools = {
                        (t.get("server_name", ""), t.get("name", ""))
                        for t in MCPClientManager.get_instance().list_tools()
                    }
                except Exception as exc:
                    logger.warning("Could not fetch MCP tool allow-list: %s", exc)
                    allowed_tools = set()
                while tool_turn < MAX_TOOL_TURNS:
                    all_calls = parse_tool_calls(parser.parsed_response + parser.parsed_thought)
                    # Filter to only calls we haven't executed yet, and only ones
                    # actually offered to the model this session.
                    calls = []
                    for c in all_calls:
                        if c["name"] != "done" and (c["server"], c["name"]) not in allowed_tools:
                            logger.warning(
                                "Ignoring tool call not in offered tool set: server=%r name=%r",
                                c["server"], c["name"],
                            )
                            continue
                        call_key = (c["server"], c["name"], frozenset(c["args"].items()))
                        if call_key not in executed_calls:
                            calls.append(c)
                            executed_calls.add(call_key)
                    
                    if not calls or all(c["name"] == "done" for c in calls):
                        break
                    for c in calls:
                        if c["name"] != "done":
                            self.tool_call_started.emit(c.get("server", ""), c["name"])
                    results = execute_tool_calls(calls)
                    tool_result_text = "\n".join(results)
                    self.new_chat_token.emit(f"\n[Tool Results]\n{tool_result_text}\n")
                    parser.parsed_response += f"\n[Tool Results]\n{tool_result_text}\n"
                    # Continue generation with tool results as context
                    prompt = prompt + raw_output + tool_result_text
                    raw_output = ""
                    tool_gen = llm(prompt, max_tokens=self.hyperparams.get("max_tokens", 2048),
                                   temperature=self.hyperparams.get("temperature", 0.7),
                                   stream=False, stop=["<|im_end|>"], echo=False)
                    continuation = tool_gen["choices"][0]["text"]
                    parser.parsed_response += continuation
                    self.new_chat_token.emit(continuation)
                    raw_output = continuation
                    tool_turn += 1

            end_time = time.perf_counter()
            prefill_time = (first_token_time - start_time) if first_token_time is not None else (end_time - start_time)
            if prefill_time <= 0:
                prefill_time = 0.001
            prefill_tps = prompt_tokens / prefill_time

            generation_time = (end_time - first_token_time) if first_token_time is not None else 0.0
            generation_tokens = len(llm.tokenize(raw_output.encode('utf-8'), add_bos=False))
            if generation_time <= 0:
                generation_tps = generation_tokens / 0.001 if generation_tokens > 0 else 0.0
            else:
                generation_tps = generation_tokens / generation_time

            total_time = end_time - start_time
            total_tokens = prompt_tokens + generation_tokens
            total_tps = total_tokens / total_time if total_time > 0 else 0.0

            _vram_after_mb = _free_vram_mb()
            _vram_delta: float | None = (
                round(_vram_before_mb - _vram_after_mb, 1)
                if _vram_before_mb is not None and _vram_after_mb is not None
                else None
            )

            _cache_diag = {**_init_cache_stats, "ttft_ms": round(prefill_time * 1000, 2)}
            log_cache_stats(_cache_diag, ts)

            _kv_hits = int(_init_cache_stats.get("tokens_from_cache") or 0)

            diagnostics = {
                "prompt_tokens": prompt_tokens,
                "prefill_time": prefill_time,
                "prefill_tps": prefill_tps,
                "generation_tokens": generation_tokens,
                "generation_time": generation_time,
                "generation_tps": generation_tps,
                "total_time": total_time,
                "total_tps": total_tps,
                "kv_cache": _cache_diag,
            }

            _write_performance_telemetry({
                "ts":                      ts,
                "model":                   ModelLoader.model_name(),
                "prefill_tokens_count":    prompt_tokens,
                "prefill_duration_sec":    round(prefill_time, 4),
                "generation_tokens_count": generation_tokens,
                "generation_duration_sec": round(generation_time, 4),
                "tokens_per_second":       round(generation_tps, 2),
                "kv_cache_hits":           _kv_hits,
                "vram_usage_mb_delta":     _vram_delta,
            })

            truncated = (finish_reason == "length")
            # Pass whether we ended inside a thought block so continuation knows where to resume
            ended_in_thought = parser.in_thought

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

            self.logger.log_generation(
                compiled_prompt=prompt,
                hyperparams=self.hyperparams,
                raw_output=raw_output,
                parsed_thought=parser.parsed_thought,
                parsed_response=parser.parsed_response,
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

            self.generation_finished.emit(parser.parsed_thought, parser.parsed_response, truncated, ended_in_thought, diagnostics)
            EventBroker.get_instance().publish("generation:finished", {
                "thought": parser.parsed_thought,
                "response": parser.parsed_response,
                "truncated": truncated,
                "ended_in_thought": ended_in_thought,
                "diagnostics": diagnostics
            })
            supervisor.finish(self.task_id)

        except CircuitBreakerOpenException as e:
            self.error_occurred.emit(str(e))
            supervisor.fail(self.task_id, str(e))
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
            supervisor.fail(self.task_id, str(e))
        finally:
            ModelLoader.unlock_instance()
            # Restore original CPU affinity
            if original_affinity:
                try:
                    import os
                    if hasattr(os, "sched_setaffinity"):
                        os.sched_setaffinity(0, original_affinity)
                except Exception as e:
                    logger.debug(f"Could not restore CPU affinity: {e}")
