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
_MAX_MSG_CHARS = 100000   # Truncate any single message to this length before it enters the prompt

_OPEN_GUARDS  = ["<", "<t", "<th", "<thi", "<thin", "<think"]
_CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]


class LLMThread(QThread):
    new_thought_token = pyqtSignal(str)
    new_chat_token = pyqtSignal(str)
    new_raw_token = pyqtSignal(str)
    # thought, response, truncated, ended_in_thought, diagnostics
    generation_finished = pyqtSignal(str, str, bool, bool, dict)
    live_stats = pyqtSignal(int, float)
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
            system_prompt = self.system_prompt
            context_str = "(No context retrieved.)"
            if self.retrieved_chunks:
                context_str = "\n".join(self.retrieved_chunks)
            
            if "{rag_context}" in system_prompt:
                system_prompt = system_prompt.replace("{rag_context}", context_str)
            elif self.retrieved_chunks:
                system_prompt += "\n\nRetrieved Context:\n" + context_str
            prompt = core.interaction_loop.build_prompt(system_prompt, trimmed_history)

            # Tokenize prompt to get accurate prompt token count
            prompt_tokens = len(llm.tokenize(prompt.encode('utf-8')))

            os.makedirs(RAW_LOG_DIR, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            raw_log_path = os.path.join(RAW_LOG_DIR, f"{ts}.tokens")

            start_time = time.time()
            first_token_time = None
            gen_token_count = 0
            raw_output = ""
            parsed_thought = ""
            parsed_response = ""
            # Determine starting mode for the streaming parser.
            # Base model: interaction_loop pre-seeds <think>\n → start inside thought block.
            # Adapter active: interaction_loop does NOT pre-seed <think> → start in chat mode
            # and detect <think> naturally if the adapter generates one.
            adapter_active = bool(getattr(ModelLoader, "_active_adapter", None))
            if self.start_in_thought:
                in_thought = self.start_in_thought  # continuation chains honour explicit flag
            elif adapter_active:
                in_thought = False   # adapter generates <think> from scratch if it wants one
            else:
                in_thought = True    # base model: prompt already pre-seeded <think>\n
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

                        if first_token_time is None:
                            first_token_time = time.time()

                        chunk_tokens = len(llm.tokenize(text.encode('utf-8'), add_bos=False))
                        gen_token_count += chunk_tokens
                        elapsed = time.time() - first_token_time
                        speed = gen_token_count / elapsed if elapsed > 0 else 0.0
                        self.live_stats.emit(gen_token_count, speed)

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

                    # Check if we need to do cognitive roll-up compression
                    current_tokens_count = len(llm.tokenize((prompt + raw_output).encode('utf-8')))
                    context_budget = ModelLoader.n_ctx()
                    
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
                            self.new_thought_token.emit(f"\n[Compressed state: {parsed_thought}]\n")
                        except Exception as ce:
                            print(f"[LLMThread] Cognitive compression failed: {ce}")
                            self.new_thought_token.emit("\n[continuing...]\n")
                    else:
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

            end_time = time.time()
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

            truncated = (finish_reason == "length")
            # Pass whether we ended inside a thought block so continuation knows where to resume
            ended_in_thought = in_thought

            self.logger.log_generation(
                compiled_prompt=prompt,
                hyperparams=self.hyperparams,
                raw_output=raw_output,
                parsed_thought=parsed_thought,
                parsed_response=parsed_response,
                execution_time=total_time,
                rag_context=self.retrieved_chunks,
                model_name=ModelLoader.model_name(),
                adapter_name=getattr(ModelLoader, '_adapter_name', None),
                workflow=self.workflow,
                template=self.template,
                diagnostics=diagnostics,
            )

            self.generation_finished.emit(parsed_thought, parsed_response, truncated, ended_in_thought, diagnostics)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
