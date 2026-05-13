import os
import time
import importlib
from datetime import datetime, timezone
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.model_loader import ModelLoader
from app.utils.trace_logger import TraceLogger
import core.interaction_loop

RAW_LOG_DIR = "data/logs/raw"


class LLMThread(QThread):
    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)                 # M7: every character pre-parser
    generation_finished = pyqtSignal(str, str)       # thought, response
    error_occurred = pyqtSignal(str)

    def __init__(self, system_prompt, chat_history, hyperparams, retrieved_chunks=None):
        super().__init__()
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.hyperparams = hyperparams
        self.retrieved_chunks = retrieved_chunks or []
        self.logger = TraceLogger()

    def run(self):
        try:
            importlib.reload(core.interaction_loop)
            
            llm = ModelLoader.get_instance()
            prompt = core.interaction_loop.build_prompt(self.system_prompt, self.chat_history)
            
            # M7: Open raw token archive file
            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            start_time = time.time()
            response_generator = llm(
                prompt,
                max_tokens=self.hyperparams.get("max_tokens", 512),
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

            with open(raw_log_path, "w", encoding="utf-8") as raw_file:
                for chunk in response_generator:
                    if 'choices' not in chunk or not chunk['choices']:
                        continue
                    text = chunk['choices'][0].get('text', '')
                    if not text:
                        continue

                    # M7: Write raw token immediately, before any parsing
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
                        if not any(buffer.endswith(s) for s in ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]):
                            self.new_thought_token.emit(buffer)
                            parsed_thought += buffer
                            buffer = ""
                    else:
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

            self.logger.log_generation(
                compiled_prompt=prompt,
                hyperparams=self.hyperparams,
                raw_output=raw_output,
                parsed_thought=parsed_thought,
                parsed_response=parsed_response,
                execution_time=execution_time,
                rag_context=self.retrieved_chunks
            )

            self.generation_finished.emit(parsed_thought, parsed_response)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
