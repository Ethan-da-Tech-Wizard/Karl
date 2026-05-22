# Karl — System Architecture & Data Flow

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Main UI Thread (PyQt6)                                             │
│                                                                     │
│  MainWindow                                                         │
│    ├── Left Panel: MemoryManager + RAGPipeline                      │
│    ├── Center: thought_display + chat_display + raw_display         │
│    └── Right: system_prompt + workflow/template combos + spinners   │
└────────────────────┬────────────────────────────────────────────────┘
                     │ spawns QThread
       ┌─────────────┴─────────────┐
       │                           │
  LLMThread                 AgenticThread
  (single shot)             (autonomous loop)
       │                           │
       ├── importlib.reload()      ├── importlib.reload()
       │   core/interaction_loop   │   core/interaction_loop
       │                           │   core/agentic_loop
       │                           │
       ├── ModelLoader.get_instance() (singleton)
       │      └── llama_cpp.Llama("data/models/deepseek-r1-1.5b.gguf")
       │
       ├── Streaming loop:
       │   token → buffer → state machine →
       │     new_thought_token(str)  →  thought_display
       │     new_chat_token(str)     →  chat_display
       │     new_raw_token(str)      →  raw_display + .tokens file
       │
       ├── TraceLogger.log_generation() → data/logs/traces/*.jsonl
       └── generation_finished(thought, response, truncated, in_thought)
                     │
             MainWindow.handle_generation_finished()
               ├── append to chat_history
               ├── enable rating buttons
               ├── update workflow report panel
               ├── update status bar
               └── if truncated → fire continuation LLMThread
```

---

## 2. The Hackable Core

```
core/
├── interaction_loop.py    ← HOT-RELOADED every generation
│   └── build_prompt(system_prompt, chat_history) -> str
│       Returns the full ChatML-formatted prompt string.
│       Modify this to change prompt format, add prefix injections,
│       or implement custom history manipulation.
│
├── agentic_loop.py        ← HOT-RELOADED every agentic iteration
│   ├── should_continue(iteration, last_response) -> bool
│   │   Stop condition. Return False to end the loop.
│   └── build_next_prompt(last_response, iteration) -> str
│       Content of the next USER turn injected into history.
│
├── prompt_templates.py    ← HOT-RELOADED every generation
│   ├── TEMPLATES: dict[str, str]   Named system prompt templates
│   ├── get_template(name, **kwargs) -> str
│   └── list_templates() -> list[str]
│
├── workflows.py           ← Read at startup + on combo change
│   ├── WORKFLOWS: dict[str, dict]  Named workflow configurations
│   ├── get_workflow(name) -> dict
│   └── list_workflows() -> list[tuple[str, str]]
│
├── cognitive_parser.py    ← Used by engine_test.py (batch mode only)
│   └── parse_thought_stream(raw_text) -> (thought, response)
│
└── hardware_scout.py      ← Run once at startup via UpgradeCheckThread
    └── get_hardware_profile() -> {ram_gb, vram_gb, storage_gb}
```

All files in `core/` are reloaded via `importlib.reload()` — save the file
and click Generate. No restart required.

---

## 3. Threading Model

| Thread | Class | Signals emitted |
|---|---|---|
| UI | `MainWindow` | — (receives signals, updates widgets) |
| Single generation | `LLMThread(QThread)` | `new_thought_token`, `new_chat_token`, `new_raw_token`, `generation_finished`, `error_occurred` |
| Agentic loop | `AgenticThread(QThread)` | same as above + `iteration_finished`, `loop_finished` |
| Upgrade check | `UpgradeCheckThread(QThread)` | `upgrade_available`, `no_upgrade` |
| Upgrade download | `UpgradeDownloadThread(QThread)` | `progress`, `finished`, `error` |

**Thread safety rule:** Never access UI widgets directly from inside `run()`. Only emit signals.

---

## 4. Data Flow: Single Generation

```
User types prompt → send_message()
  │
  ├── 1. Retrieve RAG chunks (if top_k > 0)
  │      RAGPipeline.retrieve(query, top_k) → list[str]
  │
  ├── 2. Build system prompt
  │      If workflow ≠ general_chat: get_template(tpl_name, rag_context=…)
  │      Else: system_prompt_input.toPlainText() + appended chunks
  │
  ├── 3. Append user message to chat_history
  │
  ├── 4. Spawn LLMThread(system_prompt, chat_history, hyperparams, chunks)
  │
  └── LLMThread.run():
        ├── importlib.reload(core.interaction_loop)
        ├── ModelLoader.get_instance()         # singleton — loads once
        ├── _trim_history(chat_history)        # context budget enforcement
        ├── build_prompt(system_prompt, trimmed_history)
        ├── llm(prompt, stream=True, …)
        ├── Streaming loop:
        │     for chunk in response_generator:
        │       raw_file.write(token)          # .tokens archive
        │       emit new_raw_token(token)
        │       state_machine(buffer, token)   # routes to thought/chat
        └── TraceLogger.log_generation(…)
              emit generation_finished(…)
```

---

## 5. Data Flow: Agentic Loop

```
start_agentic_loop() → AgenticThread(system_prompt, chat_history, hyperparams)
  │
  AgenticThread.run():
    ├── importlib.reload(core.interaction_loop)
    ├── importlib.reload(core.agentic_loop)
    ├── ModelLoader.get_instance()
    │
    └── while not stop_requested:
          ├── _trim_history()
          ├── build_prompt()
          ├── _run_single_generation()         # same streaming logic as LLMThread
          ├── TraceLogger.log_generation()
          ├── chat_history.append(response)
          ├── emit iteration_finished(i, thought, response)
          │
          ├── importlib.reload(core.agentic_loop)   # hot-reload stop condition
          ├── if not should_continue(i, response): break
          │
          └── next_prompt = build_next_prompt(response, i)
                chat_history.append({"role": "user", "content": next_prompt})

    emit loop_finished(total_iterations)
```

---

## 6. RAG Data Flow

```
User clicks "Ingest Document" → ingest_document()
  │
  RAGPipeline.ingest_file(filepath):
    ├── extract_text(filepath)         # format-specific extractor
    ├── chunk_text(text, 200, 50)      # 200-word chunks, 50-word overlap
    ├── encoder.encode(chunks)         # all-MiniLM-L6-v2 → float32 vectors
    ├── index.add(embeddings)          # FAISS flat L2 index
    ├── documents.append(metadata)    # {text, source_file, chunk_id, ingested_at}
    └── save_index()                   # faiss.write_index() + JSON metadata

On each generation (top_k > 0):
  RAGPipeline.retrieve(query, top_k):
    ├── encoder.encode([query])
    ├── index.search(query_vector, fetch_k)
    └── return list[str]               # with optional [Source: file | Chunk N] headers
```

---

## 7. File System Layout

```
data/
├── models/
│   └── deepseek-r1-1.5b.gguf     # ~1GB GGUF model (gitignored)
├── model_registry.json            # Tier definitions (source-controlled)
├── active_model.json              # Written at runtime on upgrade
├── logs/
│   ├── traces/
│   │   └── trace_YYYY-MM-DD.jsonl  # One JSONL log per day (gitignored)
│   └── raw/
│       └── *.tokens                 # One file per generation (gitignored)
├── sessions/
│   └── *.json                       # Saved conversations (gitignored)
├── training/
│   └── curated.jsonl                # Training curator output (gitignored)
└── vector_db/
    ├── index.faiss                  # Persisted FAISS index (gitignored)
    └── metadata.json                # Chunk metadata (gitignored)
```
