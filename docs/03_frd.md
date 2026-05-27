# Functional Requirements Document - Karl

## 1. UI Requirements

### 1.1 Navigation

The main window has a persistent top navigation bar with:

- `chat`
- `configure`
- `tuning`
- theme picker

### 1.2 Chat Page

The Chat page must provide:

- Saved session list.
- New thread button.
- Save session button.
- Knowledge-base file list.
- Ingest context button.
- Reasoning pane receiving streamed thought text.
- Hide/show control for the reasoning pane.
- Response pane receiving final answer text.
- Prompt input.
- Stop button.
- Send button.
- Approve button.
- Teach button.

### 1.3 Configure Page

The Configure page must provide:

- Workflow mode selector.
- System prompt editor.
- Theme selector.
- RAG top-k selector.
- Temperature control.
- Top-p control.
- Max-token control.
- Manual reflect button.
- Halt-loop button.
- Loop status label.
- Model-upgrade notification/button when applicable.

### 1.4 Tuning Page

The Tuning page must provide:

- Curated dataset count.
- Approved/corrected example counts.
- ShareGPT/Unsloth export button.
- Validation guidance.
- QLoRA notes.
- Links to hackable Python files.

## 2. Generation Requirements

### 2.1 Prompt Assembly

`core/interaction_loop.py` must build ChatML prompts with:

```text
<|im_start|>system
...
<|im_end|>
<|im_start|>user
...
<|im_end|>
<|im_start|>assistant
<think>
```

### 2.2 Worker Thread

`LLMThread` must:

- hot-reload `core.interaction_loop`
- load the model through `ModelLoader`
- trim history token-accurately
- clamp max generation tokens to fit context
- stream with `echo=False`
- archive raw chunks before parsing
- route thought and response tokens through signals
- log a trace when complete
- emit `generation_finished`

### 2.3 Stop Tokens

Generation calls must include stop tokens for ChatML and Qwen-derived models:

```python
["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"]
```

### 2.4 Auto-Continuation

When `finish_reason == "length"`, the engine threads continue internally for
up to five passes by appending current raw output to the prompt. Continuation
must preserve the parser's thought/response state.

## 3. Streaming Parser Requirements

The streaming parser must:

- start in thought mode when the prompt ends with `<think>`
- detect `<think>` and `</think>` even when tags arrive across chunks
- emit thought text to `new_thought_token`
- emit final answer text to `new_chat_token`
- always flush the final buffer

Guard suffixes:

```python
_OPEN_GUARDS = ["<", "<t", "<th", "<thi", "<thin", "<think"]
_CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]
```

## 4. Agentic Reflect Loop Requirements

`AgenticThread` must:

- hot-reload `core.interaction_loop`
- hot-reload `core.agentic_loop`
- run until stop is requested or `should_continue()` returns false
- trim history token-accurately
- clamp generation tokens to context window
- archive raw chunks per iteration
- log every iteration
- emit `iteration_finished`
- emit `loop_finished`

`MainWindow` must update visible chat history and loop prompt markers when
iterations complete.

## 5. RAG Requirements

`RAGPipeline` must:

- lazily load the sentence-transformer encoder
- persist FAISS index and metadata
- ingest PDF, DOCX, text/code/markdown, CSV, XLSX, and XLS files
- chunk regular text by words
- chunk tabular files by rows
- support `retrieve(query, top_k, source_filter=None)`
- support `retrieve_with_metadata()`
- support `eval_retrieval()`

Retrieval must over-fetch candidates and rerank by keyword overlap.

## 6. Trace Logging Requirements

`TraceLogger.log_generation()` must write JSONL records with:

- `timestamp`
- `execution_time_seconds`
- `workflow`
- `template`
- `hyperparameters`
- `rag_context_used`
- `compiled_prompt`
- `raw_output`
- `parsed_thought`
- `parsed_response`

## 7. Training Curator Requirements

Training examples must be stored as JSONL records with:

```json
{
  "timestamp": "...",
  "source": "approved",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

The exporter must write one JSON object per line:

```json
{"messages": [...]}
```

The validator must:

- require file existence
- require a non-empty dataset
- warn/error on low example counts
- validate roles and non-empty content
- estimate token length
- report corrected-example balance
- detect near-duplicates

## 8. Eval Requirements

The eval harness must:

- load JSONL cases
- resolve context from RAG, context file, or inline context
- render workflow templates
- run the local model unless `--dry-run` is selected
- apply a named grader
- print a summary
- optionally save reports to `eval/results/`

Supported graders:

- `exact_match`
- `json_valid`
- `keyword_hit`
- `groundedness`
- `not_in_context`
