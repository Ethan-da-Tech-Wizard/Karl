import os
import time
import importlib
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
import core.interaction_loop
import core.agentic_loop

RAW_LOG_DIR = "data/logs/raw"

_CONTEXT_BUDGET = 4096
_RESPONSE_RESERVE = 1024
_MAX_MSG_CHARS  = 1500   # hard-cap on any single message before tokenising

class AgenticThread(QThread):
    """
    Runs Karl in autonomous agentic mode.
    It loops: generate → parse → check stop condition → inject next prompt → repeat.
    The hackable stop condition and next-prompt logic live in core/agentic_loop.py.
    """
    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)                  # M7: every character pre-parser
    iteration_finished = pyqtSignal(int, str, str)
    loop_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        system_prompt,
        initial_history,
        hyperparams,
        workflow="general_chat",
        template="custom_prompt",
    ):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = list(initial_history)   # copy so we can mutate safely
        self.hyperparams = hyperparams
        self.workflow = workflow
        self.template = template
        self.logger = TraceLogger()
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def _trim_history_exact(self, llm, system_prompt, history, max_tokens, n_ctx):
        """
        Token-accurate trimmer: uses llm.tokenize() to count real tokens and
        removes the oldest messages (preserving the seed at index 0) until
        the compiled prompt fits within (n_ctx - max_tokens).
        """
        def _cap(msg):
            content = msg.get("content", "")
            if len(content) > _MAX_MSG_CHARS:
                content = "[...truncated...] " + content[-_MAX_MSG_CHARS:]
            return {**msg, "content": content}

        capped = [_cap(m) for m in history]

        def get_token_count(hist):
            compiled = core.interaction_loop.build_prompt(system_prompt, hist)
            return len(llm.tokenize(compiled.encode("utf-8"), special=True))

        target = n_ctx - min(max(256, max_tokens), n_ctx - 256)
        current = list(capped)
        count = get_token_count(current)

        while count > target and len(current) > 2:
            current.pop(1)   # drop oldest non-seed message
            count = get_token_count(current)

        if len(current) < len(history):
            self.new_thought_token.emit(
                f"\n[Context Trim: kept {len(current)}/{len(history)} messages]\n"
            )
        return current, count

    def _run_single_generation(self, llm, prompt, raw_file):
        """Runs streaming generation, continuing automatically if truncated."""
        raw_output = ""
        parsed_thought = ""
        parsed_response = ""
        # Automatically detect if we should start in thought mode based on prompt ending
        in_thought = False
        if prompt.endswith("<think>") or prompt.endswith("<think>\n"):
            in_thought = True
        buffer = ""

        continuation_count = 0
        max_continuations = 5

        while continuation_count <= max_continuations:
            prompt_tokens = len(llm.tokenize((prompt + raw_output).encode("utf-8"), special=True))
            available_for_gen = _CONTEXT_BUDGET - prompt_tokens
            if available_for_gen < 64:
                self.error_occurred.emit(
                    f"The agentic loop context is too large for this model's "
                    f"{_CONTEXT_BUDGET}-token window "
                    f"(prompt: {prompt_tokens} tokens). "
                    f"Try lowering max tokens or starting a shorter loop seed."
                )
                break

            requested_max_tokens = self.hyperparams.get("max_tokens", _RESPONSE_RESERVE)
            actual_max_tokens = min(requested_max_tokens, max(64, available_for_gen - 10))

            response_gen = llm(
                prompt + raw_output,
                max_tokens=actual_max_tokens,
                temperature=self.hyperparams.get("temperature", 0.7),
                top_p=self.hyperparams.get("top_p", 0.95),
                repeat_penalty=1.1,
                stream=True,
                stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"],
                echo=False
            )

            finish_reason = "stop"
            has_tokens = False

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

            if finish_reason != "length" or not has_tokens:
                break

            self.new_thought_token.emit("\n[continuing...]\n")
            continuation_count += 1

        # flush remainder
        if buffer:
            if in_thought:
                self.new_thought_token.emit(buffer)
                parsed_thought += buffer
            else:
                self.new_chat_token.emit(buffer)
                parsed_response += buffer

        return raw_output, parsed_thought, parsed_response

    def run(self):
        try:
            importlib.reload(core.interaction_loop)
            importlib.reload(core.agentic_loop)

            llm = ModelLoader.get_instance()
            iteration = 0

            while not self._stop_requested:
                # Build and emit iteration header
                self.new_thought_token.emit(f"\n{'='*40}\n[AGENTIC LOOP — Iteration {iteration + 1}]\n{'='*40}\n")
                self.new_chat_token.emit(f"\n[Iteration {iteration + 1}]\n")

                # Token-accurate trim before building prompt
                max_tokens = self.hyperparams.get("max_tokens", 512)
                trimmed_history, _ = self._trim_history_exact(
                    llm, self.system_prompt, self.chat_history, max_tokens, _CONTEXT_BUDGET
                )
                prompt = core.interaction_loop.build_prompt(self.system_prompt, trimmed_history)

                start = time.time()
                # M7: open raw archive file for this iteration
                os.makedirs(RAW_LOG_DIR, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                raw_log_path = os.path.join(RAW_LOG_DIR, f"agentic_{ts}_iter{iteration}.tokens")
                with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                    raw, thought, response = self._run_single_generation(llm, prompt, raw_file)
                elapsed = time.time() - start

                if self._stop_requested:
                    break

                # Log this iteration
                self.logger.log_generation(
                    compiled_prompt=prompt,
                    hyperparams=self.hyperparams,
                    raw_output=raw,
                    parsed_thought=thought,
                    parsed_response=response,
                    execution_time=elapsed,
                    rag_context=[f"agentic_iteration_{iteration}"],
                    workflow=self.workflow,
                    template=self.template,
                )

                # Store only the response — not the think block — to keep context lean
                self.chat_history.append({"role": "assistant", "content": response})

                self.iteration_finished.emit(iteration, thought, response)

                iteration += 1

                # Hot-reload stop condition and check it
                importlib.reload(core.agentic_loop)
                if not core.agentic_loop.should_continue(iteration, response):
                    break

                # Build next user turn and inject it
                next_prompt_content = core.agentic_loop.build_next_prompt(response, iteration)
                self.chat_history.append({"role": "user", "content": next_prompt_content})

            self.loop_finished.emit(iteration)

        except Exception as e:
            self.error_occurred.emit(f"Agentic Error: {str(e)}")
