import os
import time
import importlib
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
import core.interaction_loop

RAW_LOG_DIR = "data/logs/raw"
_CONTEXT_BUDGET = 4096
_RESPONSE_RESERVE = 1024
_HISTORY_CHAR_LIMIT = (_CONTEXT_BUDGET - _RESPONSE_RESERVE) * 3
_MAX_MSG_CHARS = 1500   # Truncate any single message to this length before it enters the prompt

_OPEN_GUARDS  = ["<", "<t", "<th", "<thi", "<thin", "<think"]
_CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]


class LLMThread(QThread):
    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)
    # thought, response, truncated, ended_in_thought
    generation_finished = pyqtSignal(str, str, bool, bool)
    error_occurred = pyqtSignal(str)
    # List of (token_str, logprob_float) for the top alternative at each step
    token_logprobs_ready = pyqtSignal(list)

    def __init__(self, system_prompt, chat_history, hyperparams, retrieved_chunks=None,
                 start_in_thought=False, logit_bias=None):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.start_in_thought = start_in_thought
        self.logit_bias = logit_bias or {}
        self.logger = TraceLogger()

    def _trim_history(self, history):
        """
        Prepares history for the prompt:
        1. Truncates any individual message > _MAX_MSG_CHARS (keeps the tail — most recent content)
        2. Drops oldest messages until the total fits in the budget
        3. Always keeps message[0] (the seed)
        """
        def _cap(msg):
            content = msg.get("content", "")
            if len(content) > _MAX_MSG_CHARS:
                content = "[...truncated...] " + content[-_MAX_MSG_CHARS:]
            return {**msg, "content": content}

        capped = [_cap(m) for m in history]
        kept = []
        running = 0
        for msg in reversed(capped):
            entry_len = len(msg.get("content", ""))
            if running + entry_len > _HISTORY_CHAR_LIMIT and kept:
                break
            kept.insert(0, msg)
            running += entry_len
        if capped and capped[0] not in kept:
            kept.insert(0, capped[0])
        return kept

    def run(self):
        try:
            importlib.reload(core.interaction_loop)

            llm = ModelLoader.get_instance()
            trimmed_history = self._trim_history(self.chat_history)
            prompt = core.interaction_loop.build_prompt(self.system_prompt, trimmed_history)

            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            start_time = time.time()
            call_kwargs = dict(
                max_tokens=self.hyperparams.get("max_tokens", 512),
                temperature=self.hyperparams.get("temperature", 0.7),
                top_p=self.hyperparams.get("top_p", 0.95),
                repeat_penalty=1.15,
                stream=True,
                stop=["<|im_end|>"],
                logprobs=5,
            )
            if self.logit_bias:
                call_kwargs["logit_bias"] = self.logit_bias
            response_generator = llm(prompt, **call_kwargs)

            raw_output = ""
            parsed_thought = ""
            parsed_response = ""
            in_thought = self.start_in_thought
            buffer = ""
            finish_reason = "stop"
            collected_logprobs: list[tuple[str, float]] = []  # (token, top_logprob)

            with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                for chunk in response_generator:
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

                    # Collect logprob of the chosen token (top alternative)
                    lp_data = choice.get('logprobs')
                    if lp_data and isinstance(lp_data, dict):
                        token_lps = lp_data.get('top_logprobs')
                        if token_lps:
                            # token_lps is a list of dicts [{token: logprob, ...}]
                            top_entry = token_lps[0] if token_lps else {}
                            if top_entry:
                                top_token = next(iter(top_entry))
                                top_lp = top_entry[top_token]
                                collected_logprobs.append((text, float(top_lp)))

                    micro_ts = f"{time.time():.6f}"
                    raw_file.write(f"{micro_ts}\t{text}\n")
                    raw_file.flush()
                    self.new_raw_token.emit(text)

                    raw_output += text
                    buffer += text

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
                        if not any(buffer.endswith(s) for s in _CLOSE_GUARDS):
                            self.new_thought_token.emit(buffer)
                            parsed_thought += buffer
                            buffer = ""
                    else:
                        if not any(buffer.endswith(s) for s in _OPEN_GUARDS):
                            self.new_chat_token.emit(buffer)
                            parsed_response += buffer
                            buffer = ""

            # Flush remainder
            if buffer:
                if in_thought:
                    self.new_thought_token.emit(buffer)
                    parsed_thought += buffer
                else:
                    self.new_chat_token.emit(buffer)
                    parsed_response += buffer

            execution_time = time.time() - start_time
            truncated = (finish_reason == "length")
            # Pass whether we ended inside a thought block so continuation knows where to resume
            ended_in_thought = in_thought

            self.logger.log_generation(
                compiled_prompt=prompt,
                hyperparams=self.hyperparams,
                raw_output=raw_output,
                parsed_thought=parsed_thought,
                parsed_response=parsed_response,
                execution_time=execution_time,
                rag_context=self.retrieved_chunks
            )

            if collected_logprobs:
                self.token_logprobs_ready.emit(collected_logprobs)

            self.generation_finished.emit(parsed_thought, parsed_response, truncated, ended_in_thought)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
