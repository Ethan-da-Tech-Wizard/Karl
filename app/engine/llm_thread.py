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

    def __init__(
        self,
        system_prompt,
        chat_history,
        hyperparams,
        retrieved_chunks=None,
        start_in_thought=False,
        workflow="general_chat",
        template="custom_prompt",
    ):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.start_in_thought = start_in_thought  # True when continuing mid-thought
        self.workflow = workflow
        self.template = template
        self.logger = TraceLogger()

    def _trim_history_exact(self, llm, system_prompt, history, max_tokens, n_ctx):
        """
        Dynamically trims history message by message (from oldest to newest, preserving the seed at index 0)
        until the token count of the compiled prompt is <= (n_ctx - max_tokens).
        """
        def _cap(msg):
            content = msg.get("content", "")
            if len(content) > _MAX_MSG_CHARS:
                content = "[...truncated...] " + content[-_MAX_MSG_CHARS:]
            return {**msg, "content": content}

        capped = [_cap(m) for m in history]
        
        def get_prompt_token_count(hist):
            compiled = core.interaction_loop.build_prompt(system_prompt, hist)
            tokens = llm.tokenize(compiled.encode('utf-8'), special=True)
            return len(tokens)

        # Target prompt size: leave at least a minimum of 256 tokens for generation,
        # but try to leave max_tokens if possible.
        target_prompt_limit = n_ctx - max(256, max_tokens)
        
        current_history = list(capped)
        token_count = get_prompt_token_count(current_history)
        
        while token_count > target_prompt_limit and len(current_history) > 2:
            # Keep index 0 (the seed), remove the oldest subsequent message
            current_history.pop(1)
            token_count = get_prompt_token_count(current_history)
            
        if len(current_history) < len(history):
            self.new_thought_token.emit(
                f"\n[Context Trim: kept {len(current_history)}/{len(history)} messages to fit context window]\n"
            )
            
        return current_history, token_count

    def run(self):
        try:
            importlib.reload(core.interaction_loop)

            llm = ModelLoader.get_instance()
            max_tokens = self.hyperparams.get("max_tokens", 512)
            trimmed_history, _ = self._trim_history_exact(
                llm, self.system_prompt, self.chat_history, max_tokens, _CONTEXT_BUDGET
            )
            prompt = core.interaction_loop.build_prompt(self.system_prompt, trimmed_history)

            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            # --- Safety clamp: make sure prompt + max_tokens fits in n_ctx ----
            prompt_tokens = len(llm.tokenize(prompt.encode("utf-8"), special=True))
            available_for_gen = _CONTEXT_BUDGET - prompt_tokens
            if available_for_gen < 64:
                self.error_occurred.emit(
                    f"The knowledge base context is too large for this model's "
                    f"{_CONTEXT_BUDGET}-token window "
                    f"(prompt: {prompt_tokens} tokens). "
                    f"Try reducing Chunks (top-k) to 1 or 2 in Configure, "
                    f"or clear the knowledge base and re-ingest a smaller file."
                )
                return
            # Clamp so prompt+generation always fits
            actual_max_tokens = min(max_tokens, max(64, available_for_gen - 10))
            # ---------------------------------------------------------------------

            start_time = time.time()
            raw_output = ""
            parsed_thought = ""
            parsed_response = ""
            # Automatically detect if we should start in thought mode based on prompt ending
            in_thought = self.start_in_thought
            if not in_thought and (prompt.endswith("<think>") or prompt.endswith("<think>\n")):
                in_thought = True
            buffer = ""
            finish_reason = "stop"

            continuation_count = 0
            max_continuations = 5

            with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                while continuation_count <= max_continuations:
                    response_generator = llm(
                        prompt + raw_output,
                        max_tokens=actual_max_tokens,
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
                workflow=self.workflow,
                template=self.template,
            )

            self.generation_finished.emit(parsed_thought, parsed_response, truncated, ended_in_thought)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
