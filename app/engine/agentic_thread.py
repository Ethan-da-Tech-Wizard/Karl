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

# Reserve this many tokens for the next generation's output.
# The rest of the budget is used for history.
_CONTEXT_BUDGET = 4096
_RESPONSE_RESERVE = 1024  # max_tokens headroom
_HISTORY_CHAR_LIMIT = (_CONTEXT_BUDGET - _RESPONSE_RESERVE) * 3  # ~1 token ≈ 3 chars (conservative)

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

    def __init__(self, system_prompt, initial_history, hyperparams):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = list(initial_history)   # copy so we can mutate safely
        self.hyperparams = hyperparams
        self.logger = TraceLogger()
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def _trim_history(self, history, system_prompt):
        """
        Trims the chat history so the compiled prompt stays inside the context budget.
        Always keeps the first user message (the seed) and the most recent turns.
        """
        base_len = len(system_prompt)
        budget = _HISTORY_CHAR_LIMIT - base_len

        # Walk backwards through history accumulating character count.
        # Always keep at least the first message (index 0) as the seed.
        kept = []
        running = 0
        for msg in reversed(history):
            entry_len = len(msg.get("content", ""))
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
        """Runs one streaming generation. Returns (raw, thought, response)."""
        response_gen = llm(
            prompt,
            max_tokens=self.hyperparams.get("max_tokens", 1024),
            temperature=self.hyperparams.get("temperature", 0.7),
            top_p=self.hyperparams.get("top_p", 0.95),
            repeat_penalty=1.15,
            stream=True,
            stop=["<|im_end|>"]
        )

        raw_output = ""
        parsed_thought = ""
        parsed_response = ""
        in_thought = False
        buffer = ""

        for chunk in response_gen:
            if self._stop_requested:
                break
            if 'choices' not in chunk or not chunk['choices']:
                continue
            text = chunk['choices'][0].get('text', '')
            if not text:
                continue

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

            if in_thought:
                if not any(buffer.endswith(s) for s in ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]):
                    self.new_thought_token.emit(buffer)
                    parsed_thought += buffer
                    buffer = ""
            else:
                self.new_chat_token.emit(buffer)
                parsed_response += buffer
                buffer = ""

        # flush
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

                # Trim history to fit context before building prompt
                trimmed_history = self._trim_history(self.chat_history, self.system_prompt)
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
                    rag_context=[f"agentic_iteration_{iteration}"]
                )

                # Update history with this iteration's output
                full_context = f"<think>\n{thought}\n</think>\n{response}" if thought else response
                self.chat_history.append({"role": "assistant", "content": full_context})

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
