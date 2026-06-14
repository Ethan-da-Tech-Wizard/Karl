import logging
import os
import time
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.hot_reload import compile_and_reload
from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
import core.interaction_loop
import core.agentic_loop

RAW_LOG_DIR = "data/logs/raw"

# Reserve this many tokens for the next generation's output.
# The rest of the budget is used for history.
_RESPONSE_RESERVE = 1024  # max_tokens headroom

logger = logging.getLogger("karl.agentic_thread")


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

    def __init__(self, system_prompt, initial_history, hyperparams,
                 retrieved_chunks=None, workflow="general_chat",
                 template="reasoning_minimal", adapter_name=None, model_name=None):
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

    def request_stop(self):
        self._stop_requested = True

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

    def _trim_history(self, history, system_prompt, llm):
        """
        Trims the chat history so the compiled prompt stays inside the context budget.
        Always keeps the first user message (the seed) and the most recent turns.
        """
        context_budget = ModelLoader.context_limit()
        base_tokens = self._token_count(llm, system_prompt)
        budget = max(256, context_budget - _RESPONSE_RESERVE - base_tokens)

        # Walk backwards through history accumulating tokenizer-measured size.
        # Always keep at least the first message (index 0) as the seed.
        kept = []
        running = 0
        for msg in reversed(history):
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

    def _run_single_generation(self, llm, prompt, raw_file):
        """Runs streaming generation, continuing automatically if truncated."""
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

        while continuation_count <= max_continuations:
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

            finish_reason = "stop"
            has_tokens = False
            state_transitioned = False

            for chunk in response_gen:
                if self._stop_requested:
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

                if first_token_time is None:
                    first_token_time = time.time()

                chunk_tokens = len(llm.tokenize(text.encode('utf-8'), add_bos=False))
                gen_token_count += chunk_tokens
                elapsed = time.time() - first_token_time
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

                if "<think>" in buffer and not in_thought:
                    in_thought = True
                    pre_think = buffer.split("<think>")[0]
                    if pre_think:
                        self.new_chat_token.emit(pre_think)
                        parsed_response += pre_think
                    buffer = buffer.split("<think>", 1)[1]

                if in_thought and "</think>" in buffer:
                    in_thought = False
                    parts = buffer.split("</think>", 1)
                    if parts[0]:
                        self.new_thought_token.emit(parts[0])
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
                        parsed_thought += buffer
                        buffer = ""
                else:
                    if not any(buffer.endswith(s) for s in _OPEN_GUARDS):
                        self.new_chat_token.emit(buffer)
                        parsed_response += buffer
                        buffer = ""

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
                parsed_thought += buffer
            else:
                self.new_chat_token.emit(buffer)
                parsed_response += buffer

        return raw_output, parsed_thought, parsed_response, first_token_time

    def run(self):
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
            llm = ModelLoader.get_instance(model_path=model_path, adapter_name=self.adapter_name)
            ModelLoader.lock_instance()
            iteration = 0

            while not self._stop_requested:
                # Build and emit iteration header
                self.new_thought_token.emit(f"\n{'='*40}\n[AGENTIC LOOP — Iteration {iteration + 1}]\n{'='*40}\n")
                self.new_chat_token.emit(f"\n[Iteration {iteration + 1}]\n")

                # Inject RAG context into system prompt if present
                system_prompt = self.system_prompt
                if self.retrieved_chunks:
                    context_str = "\n".join(self.retrieved_chunks)
                    if "{rag_context}" in system_prompt:
                        system_prompt = system_prompt.replace("{rag_context}", context_str)
                    else:
                        system_prompt += "\n\nRetrieved Context:\n" + context_str

                # Trim history to fit context before building prompt
                trimmed_history = self._trim_history(self.chat_history, system_prompt, llm)
                prompt = core.interaction_loop.build_prompt(system_prompt, trimmed_history)

                # Tokenize prompt to get accurate prompt token count
                prompt_tokens = len(llm.tokenize(prompt.encode('utf-8')))

                start = time.time()
                # M7: open raw archive file for this iteration
                os.makedirs(RAW_LOG_DIR, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                raw_log_path = os.path.join(RAW_LOG_DIR, f"agentic_{ts}_iter{iteration}.tokens")
                with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                    raw, thought, response, first_token_time = self._run_single_generation(llm, prompt, raw_file)
                end = time.time()

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
                )

                # Store only the response — not the think block — to keep context lean
                self.chat_history.append({"role": "assistant", "content": response})

                self.iteration_finished.emit(iteration, thought, response, diagnostics)

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

        except Exception as e:
            self.error_occurred.emit(f"Agentic Error: {str(e)}")
        finally:
            ModelLoader.unlock_instance()
