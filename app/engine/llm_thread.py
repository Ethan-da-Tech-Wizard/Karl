import os
import time
import importlib
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
import core.interaction_loop

RAW_LOG_DIR = "data/logs/raw"
_RESPONSE_RESERVE = 1024
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

    def __init__(self, system_prompt, chat_history, hyperparams,
                 retrieved_chunks=None, start_in_thought=False,
                 workflow="general_chat", template="reasoning_minimal",
                 adapter_name=None):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.start_in_thought = start_in_thought  # True when continuing mid-thought
        self.workflow = workflow
        self.template = template
        self.adapter_name = adapter_name
        self.logger = TraceLogger()

    def _trim_history(self, history):
        """
        Prepares history for the prompt:
        1. Truncates any individual message > _MAX_MSG_CHARS (keeps the tail — most recent content)
        2. Drops oldest messages until the total fits in the budget
        3. Always keeps message[0] (the seed)
        """
        context_budget = ModelLoader.n_ctx()
        history_char_limit = (context_budget - _RESPONSE_RESERVE) * 3

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
            if running + entry_len > history_char_limit and kept:
                break
            kept.insert(0, msg)
            running += entry_len
        if capped and capped[0] not in kept:
            kept.insert(0, capped[0])
        return kept

    def run(self):
        try:
            importlib.reload(core.interaction_loop)

            llm = ModelLoader.get_instance(adapter_name=self.adapter_name)
            trimmed_history = self._trim_history(self.chat_history)
            prompt = core.interaction_loop.build_prompt(self.system_prompt, trimmed_history)

            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            start_time = time.time()
            raw_output = ""
            parsed_thought = ""
            parsed_response = ""
            # Prompt pre-seeds <think>\n so we ALWAYS start inside the thought block.
            # start_in_thought only used for continuation chains.
            in_thought = True if not self.start_in_thought else self.start_in_thought
            buffer = ""
            finish_reason = "stop"

            continuation_count = 0
            max_continuations = 5

            with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                while continuation_count <= max_continuations:
                    response_generator = llm(
                        prompt + raw_output,
                        max_tokens=self.hyperparams.get("max_tokens", 2048),
                        temperature=self.hyperparams.get("temperature", 0.7),
                        top_p=self.hyperparams.get("top_p", 0.95),
                        repeat_penalty=1.1,
                        stream=True,
                        # <|im_start|> stops the model from hallucinating a new conversation turn
                        stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"],
                        echo=False
                    )

                    finish_reason = "stop"
                    has_tokens = False

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

                        has_tokens = True
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

                    if finish_reason != "length" or not has_tokens:
                        break

                    self.new_thought_token.emit("\n[continuing...]\n")
                    continuation_count += 1

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
                rag_context=self.retrieved_chunks,
                model_name=ModelLoader.model_name(),
                adapter_name=getattr(ModelLoader, '_adapter_name', None),
                workflow=self.workflow,
                template=self.template,
            )

            self.generation_finished.emit(parsed_thought, parsed_response, truncated, ended_in_thought)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
