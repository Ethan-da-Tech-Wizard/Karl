# Functional Requirements Document (FRD) — Karl v2

## 1. User Interface Architecture (PyQt6)

### 1.1 Three-Column Layout

```
┌─────────────────┬──────────────────────────────────┬──────────────────┐
│  LEFT (240px)   │  CENTER (flexible)               │  RIGHT (340px)   │
│                 │                                  │                  │
│  Saved Sessions │  [Raw Token Archive — hidden]    │  System Prompt   │
│  ─────────────  │  ─────────────────────────────── │  ─────────────── │
│  Branches Tree  │  Diagnostic Lane (thought stream)│  Workflow Mode   │
│  ─────────────  │  ─────────────────────────────── │  Template        │
│  Knowledge Base │  Final Response + Input Row       │  RAG top-k       │
│  (RAG)          │  Workflow Report                  │  ─────────────── │
│                 │  Rating Row                       │  Hyperparameters │
│                 │  Agentic Controls                 │  ─────────────── │
│                 │                                   │  Curator / Train │
└─────────────────┴───────────────────────────────────┴──────────────────┘
                              Status Bar
```

All three columns are separated by resizable `QSplitter` handles.
The Raw Token Archive panel is collapsed by default (toggled via checkbox).

### 1.2 Panel Responsibilities

| Panel | Widget | Purpose |
|---|---|---|
| Left | `QListWidget` (sessions) | Click to load a saved conversation |
| Left | `QTreeWidget` (branches) | Tree view displaying user/assistant messages on all branches; click to jump active path |
| Left | `QListWidget` (KB) | Shows ingested document names and chunk counts |
| Left | `QPushButton` × 3 | New session, Save session, Ingest document |
| Center top | `QTextBrowser` (raw) | Pre-parser token stream — toggleable |
| Center mid | `QTextBrowser` (thought) | Live `<think>` stream from streaming parser |
| Center bot | `QTextBrowser` (chat) | Cleaned final response, with clickable anchor branch links next to YOU/KARL headers |
| Center bot | `QLineEdit` + buttons | Prompt input + Generate + Force Thought |
| Center bot | `QTextBrowser` (report) | Post-generation workflow report |
| Center bot | Rating buttons | 👍 Good / 👎 Bad / ✏️ Fix — feeds training curator |
| Center bot | Agentic controls | Auto-Loop checkbox, Run, Stop, status label |
| Right | `QTextEdit` | System prompt (editable, sticky across turns) |
| Right | `QComboBox` × 2 | Workflow and template selectors |
| Right | `QSpinBox` + `QCheckBox` | RAG top-k and contextual headers toggle |
| Right | `QDoubleSpinBox` × 2 | Temperature and Top-P |
| Right | `QSpinBox` | Max new tokens |
| Right | Downloader area | Registry model tiers list + download managers |
| Right | Curator stats + export | Training example count and export SFT/DPO buttons |
| Bottom | `QStatusBar` | Live state + last generation latency + active model/RAM metrics |

### 1.3 Rich Tooltips
Every interactive element carries a `setToolTip()` with:
- A bold title
- A full description of what the control does
- Where the relevant code lives (e.g., `core/interaction_loop.py`)
- Practical usage tips

---

## 2. Introspection & Logging

### 2.1 Streaming Parser (Inline State Machine)

Both `LLMThread` and `AgenticThread` implement the same inline streaming state machine:

```
token arrives → append to buffer
                    │
          ┌─────────▼──────────┐
          │  buffer contains   │
          │  <think> ?         │
          └─────────┬──────────┘
          YES       │ NO
          │         ▼
          │   emit new_chat_token
          │         │
          ▼         │
   in_thought=True  │
          │         │
   buffer contains  │
   </think> ?       │
          │ YES     │
          ▼         │
   emit new_thought_token
   in_thought=False
   emit remainder as new_chat_token
```

A suffix guard prevents flushing when a tag might be split across chunks:
```python
_OPEN_GUARDS  = ["<", "<t", "<th", "<thi", "<thin", "<think"]
_CLOSE_GUARDS = ["<", "</", "</t", "</th", "</thi", "</thin", "</think"]
if not any(buffer.endswith(s) for s in guards):
    emit(buffer); buffer = ""
```

### 2.2 Trace Logger (`app/utils/trace_logger.py`)

Every generation appends one JSON object to `data/logs/traces/trace_YYYY-MM-DD.jsonl`:

```json
{
  "timestamp": "2026-05-22T19:00:00Z",
  "execution_time_seconds": 4.21,
  "workflow": "general_chat",
  "template": "reasoning_minimal",
  "hyperparameters": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 512},
  "rag_context_used": ["chunk text 1", "chunk text 2"],
  "compiled_prompt": "<|im_start|>system\n…",
  "raw_output": "<think>…</think>The answer is…",
  "parsed_thought": "…",
  "parsed_response": "The answer is…"
}
```

### 2.3 Raw Token Archive (`data/logs/raw/*.tokens`)

Each generation writes a micro-timestamped `.tokens` file:
```
1716408000.123456    <think>
1716408000.124100    Let me consider
1716408000.125000    this carefully.
```
Format: `{unix_float}\t{token_text}` — one line per streaming chunk.

---

## 3. Generation Engine

### 3.1 Model Loader (`app/engine/model_loader.py`)

`ModelLoader` is a class-level singleton:
- `get_instance()` — loads model once, returns same object forever
- `reset_instance()` — forces reload on next `get_instance()` call
- Config: `n_ctx` loaded from `data/model_registry.json` based on active GGUF model tier, `verbose=False`
- Default model: `data/models/deepseek-r1-1.5b.gguf`

### 3.2 Generation Call Parameters

```python
llm(
    prompt,
    max_tokens=512,         # from UI spinner
    temperature=0.7,        # from UI spinner
    top_p=0.95,             # from UI spinner
    repeat_penalty=1.15,    # fixed — reduces repetition loops
    stream=True,            # enables token-by-token streaming
    stop=["<|im_end|>", "<|endoftext|>", "<|end_of_text|>"],
    echo=False              # prevents prompt echo in output
)
```

### 3.3 Context Window Management

Both threads implement `_trim_history()`:
- Budget: `(ModelLoader.n_ctx() - 1024) * 3` chars (~3 chars/token conservative estimate)
- Walks history newest-first, accumulating char count
- Stops when budget exceeded, always preserves seed message (index 0)
- Emits a notice to the Diagnostic Lane when trimming occurs

### 3.4 Truncation Chaining

If `finish_reason == "length"`:
- `LLMThread` emits `generation_finished(truncated=True)`
- `MainWindow` appends `{"role": "user", "content": "Continue."}` and fires a new `LLMThread`
- This repeats until the model stops naturally

---

## 4. Cognitive Manipulation Pathways

### 4.1 Editing `core/interaction_loop.py`
- `build_prompt(system_prompt, chat_history) -> str` — returns the full ChatML prompt string
- Hot-reloaded via `importlib.reload()` before every generation
- Default: ChatML format (`<|im_start|>` / `<|im_end|>`)

### 4.2 Force Thought Button
- Takes text from the prompt input box
- Appends `{"role": "assistant", "content": "<think>\n{text}\n</think>"}` to `chat_history`
- The model's next generation continues from this seeded reasoning premise

### 4.3 Editing `core/agentic_loop.py`
- `should_continue(iteration, last_response) -> bool` — stop condition
- `build_next_prompt(last_response, iteration) -> str` — next user turn content
- Both hot-reloaded between every agentic iteration

---

## 5. RAG Pipeline (`app/utils/rag_pipeline.py`)

| Step | Implementation |
|---|---|
| Text extraction | `fitz` (PDF), `docx` (DOCX), `open()` (all others) |
| Chunking | Word-based, 200 words/chunk, 50-word overlap |
| Embedding | `SentenceTransformer("all-MiniLM-L6-v2")` |
| Indexing | `faiss.IndexFlatL2(384)` |
| Persistence | `faiss.write_index()` + JSON metadata to `data/vector_db/` |
| Retrieval | Top-k L2 search, optional source filter, optional contextual headers |
| Eval metrics | `hit@1`, `hit@3`, `hit@k`, reciprocal rank via `eval_retrieval()` |

---

## 6. Training Data Curator (`app/utils/training_curator.py`)

- `save_example(system_prompt, user_msg, good_response, source)` — appends to `data/training/curated.jsonl`
- `get_stats()` — returns `{total, thumbs_up, corrected}`
- `export_unsloth(path)` — writes Unsloth-formatted JSONL with `conversations` field

---

## 7. Eval Harness (`eval/`)

| File | Purpose |
|---|---|
| `harness.py` | Loads datasets, runs generations, calls graders |
| `graders.py` | `keyword_hit`, `json_valid`, `groundedness`, `json_schema`, `regex_match` |
| `run_eval.py` | CLI: `python eval/run_eval.py --workflow grounded_answer --top_k 5` |
| `benchmark_rag.py` | Retrieval-only benchmark, outputs hit@k and MRR |
| `datasets/*.jsonl` | One dataset per workflow mode |
