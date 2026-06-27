# Karl — System Architecture

## 1. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Main UI Thread (PyQt6)                                             │
│                                                                     │
│  MainWindow                                                         │
│    ├── Sidebar (56px fixed)     app/ui/sidebar.py                  │
│    ├── QStackedWidget                                               │
│    │    ├── [0] WorkbenchWorkspace                                  │
│    │    ├── [1] PromptLabWorkspace                                  │
│    │    ├── [2] KnowledgeBaseWorkspace                              │
│    │    ├── [3] VisionWorkbench                                     │
│    │    ├── [4] TrainingStudioWorkspace                             │
│    │    ├── [5] EvalSuiteWorkspace                                  │
│    │    ├── [6] SwarmStudioWorkspace                                │
│    │    ├── [7] SystemConfigWorkspace                               │
│    │    ├── [8] DocsWorkspace                                       │
│    │    └── [9] FlywheelStudioWorkspace                             │
│    └── StatusBar (24px fixed)   app/ui/widgets/status_bar.py       │
│                                                                     │
│  AppState (shared, passed to all workspaces)   app/state.py        │
│    ├── rag:     RAGPipeline                                         │
│    ├── memory:  MemoryManager                                       │
│    ├── logger:  TraceLogger                                         │
│    ├── curator: TrainingCurator                                     │
│    ├── model_name: str                                              │
│    └── adapter_name: str | None                                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ WorkbenchWorkspace spawns QThreads
              ┌─────────────┴─────────────┐
              │                           │
         LLMThread                 AgenticThread
         (single shot)             (autonomous loop)
              │                           │
              ├── importlib.reload(core.interaction_loop)
              │                           ├── importlib.reload(core.agentic_loop)
              │                           │
              └── ModelLoader.get_instance() ── llama_cpp.Llama
                  (thread-safe singleton with Lock)
```

---

## 2. Workspace Architecture

Each workspace is a `QWidget` subclass in `app/ui/workspaces/`.
All workspaces receive a single `AppState` instance at construction.
Workspaces communicate primarily through `AppState` and never reference
`MainWindow`. A few UI integration points receive an explicit Workbench
reference from `MainWindow` after construction.

| Workspace | File | Owns |
|-----------|------|------|
| Workbench | `workbench/workspace.py` | `chat_history` (SessionTree), LLMThread, AgenticThread |
| Prompt Lab | `prompt_lab.py` | A/B run threads, prompt pairs, tokenizer view |
| Knowledge Base | `knowledge_base.py` | ingest controls, chunk inspector, RAG search testing |
| Vision Workbench | `vision_workbench.py` | screenshot/image reasoning, OCR, saved images |
| Training Studio | `training_studio/__init__.py` | dataset browser, export, TrainingThread, flywheel controls |
| Eval Suite | `eval_suite.py` | EvalThread, results display, grader controls |
| Swarm Studio | `swarm_studio.py` | task graph, file proposals, verification traces |
| System Config | `system_config/workspace.py` | model registry, generation defaults, theme, hardware |
| Docs | `docs.py` | local Codex reference browser |
| Flywheel Studio | `flywheel_studio.py` | telemetry and fine-tuning loop metrics |

`VisionWorkbench`, `SystemConfigWorkspace`, and `DocsWorkspace` additionally
hold a reference to `WorkbenchWorkspace` for tightly scoped UI actions such as
image-to-prompt handoff, generation default updates, and documentation prompt
insertion. These references are set explicitly by `MainWindow`; shared state
still flows through `AppState`.

---

## 3. The Hackable Core

All files in `core/` are hot-reloaded via `importlib.reload()` on every generation.
The user edits them directly. No restart required.

```
core/
├── interaction_loop.py    ← HOT-RELOADED every generation
│   └── build_prompt(system_prompt, chat_history) -> str
│       Returns the full ChatML-formatted prompt string.
│
├── agentic_loop.py        ← HOT-RELOADED every agentic iteration
│   ├── should_continue(iteration, last_response) -> bool
│   └── build_next_prompt(last_response, iteration) -> str
│
├── prompt_templates.py    ← HOT-RELOADED every generation
│   ├── TEMPLATES: dict[str, str]
│   └── get_template(name, **kwargs) -> str
│
├── workflows.py           ← read at startup + on workflow combo change
│   ├── WORKFLOWS: dict[str, dict]   (template, rag_top_k, output_schema, grader)
│   └── list_workflows() -> list[tuple[str, str]]
│
├── cognitive_parser.py    ← used by engine_test.py (batch post-processing only)
│   └── parse_thought_stream(raw_text) -> (thought, response)
│       State machine: handles any tag capitalisation, multiple blocks, unclosed tags
│
└── hardware_scout.py
    └── get_hardware_profile() -> {ram_gb, vram_gb, storage_gb}
```

---

## 4. Threading Model

| Thread | Class | Signals |
|--------|-------|---------|
| UI | `MainWindow` + workspaces | — (receives signals, updates widgets) |
| Single generation | `LLMThread(QThread)` | `new_thought_token`, `new_chat_token`, `new_raw_token`, `generation_finished`, `error_occurred` |
| Agentic loop | `AgenticThread(QThread)` | same + `iteration_finished`, `loop_finished` |
| RAG ingest | `_IngestThread(QThread)` in `knowledge_base.py` | `done`, `error` |
| Eval run | `_EvalThread(QThread)` in `eval_suite.py` | `progress`, `done`, `error` |
| LoRA training | `TrainingThread(QThread)` (Phase 3.3) | `loss`, `progress`, `done`, `error` |
| Prompt Lab run | `_RunThread(QThread)` in `prompt_lab.py` | `token`, `done`, `error` |

**Rule:** Never access Qt widgets from inside `run()`. Emit signals only.

---

## 5. The Model Singleton

```python
# app/engine/model_loader.py
ModelLoader.get_instance(model_path=None, adapter_name=None, draft_model_path=None) -> Llama
ModelLoader.reset_instance()                          # unloads model and draft handles
ModelLoader.model_name() -> str                       # active GGUF basename
ModelLoader.is_loaded() -> bool
ModelLoader.n_ctx() -> int                            # loaded context or registry fallback
ModelLoader.reset_circuit_breaker() -> None           # manual breaker reset
```

- Protected by `threading.RLock()`.
- Reads `data/active_model.json` on first call for GGUF filename and adapter.
- Falls back to `data/models/deepseek-r1-1.5b.gguf` if the specified file is missing and the fallback exists.
- Reads `n_ctx`, `n_batch`, quantization, RAM, and VRAM metadata from `data/model_registry.json`.
- Loads with `n_gpu_layers=-1`, `flash_attn=True`, `use_mmap=True`, and `use_mlock=True`.
- If host `mlock` limits reject locked memory, retries the same load with `use_mlock=False` and logs Linux ulimit guidance.
- If VRAM allocation fails, halves `n_ctx` down to a minimum of 2048 before surfacing a terminal load error.
- When multiple GPUs are visible, computes a proportional `tensor_split` from free VRAM and tries that before falling back to single-GPU loading.
- Optional speculative decoding loads a draft GGUF from `data/draft_model.json` or the supplied `draft_model_path`; if the installed `llama-cpp-python` lacks `draft_model`, Karl disables speculative decoding and keeps normal inference.
- The model-load circuit breaker trips OPEN after three terminal load failures, blocks repeated constructor attempts for 30 seconds, then permits one HALF_OPEN recovery attempt.
- Optional 8-bit KV cache uses `type_k` and `type_v` set to `GGML_TYPE_Q8_0` when `quantized_kv_cache` is enabled.

---

## 6. Streaming Parser (Inline in Both Threads)

The threads do NOT use `cognitive_parser.parse_thought_stream()`. They contain
an inline state machine that routes tokens in real time:

```
State: in_thought = True (pre-seeded by prompt "<think>\n")

For each token chunk:
  buffer += token
  emit new_raw_token(token)          ← always, before parsing
  write to .tokens archive file

  if "<think>" in buffer and not in_thought:
    in_thought = True
    flush pre-think text to new_chat_token
    reset buffer to post-<think> text

  if in_thought and "</think>" in buffer:
    in_thought = False
    flush thought text to new_thought_token
    reset buffer to post-</think> text

  if in_thought:
    if buffer does not end with close guard suffix:
      emit new_thought_token(buffer); buffer = ""

  else:
    if buffer does not end with open guard suffix:
      emit new_chat_token(buffer); buffer = ""

After generation loop:
  flush remaining buffer to appropriate signal
  emit generation_finished(thought, response, truncated, ended_in_thought)
```

Close guard suffixes: `["<", "</", "</t", "</th", "</thi", "</thin", "</think"]`
Open guard suffixes:  `["<", "<t", "<th", "<thi", "<thin", "<think"]`

Auto-continuation: if `finish_reason == "length"`, appends `raw_output` to prompt
and re-queries (up to 5 passes). `ended_in_thought` flag preserves parse state.

Both generation threads start a watchdog timer while streaming. If no token arrives
within `watchdog_timeout_seconds` (default 30s), the active generator is closed,
the model is reset best-effort, and `error_occurred` receives a timeout message.
Circuit-breaker-open failures are emitted as the plain operator-facing breaker
message rather than wrapped in a generic thread error prefix.

---

## 6.1 Event Broker

`app/engine/event_broker.py` is a thread-safe in-process pub/sub singleton used
for live telemetry fan-out without coupling UI widgets directly to engine loops.

```python
EventBroker.get_instance() -> EventBroker
EventBroker.subscribe(topic, callback) -> None
EventBroker.unsubscribe(topic, callback) -> None
EventBroker.publish(topic, data) -> None
```

Current engine topics include:

| Topic | Payload |
|-------|---------|
| `tokens:raw` | `{"token": str}` before parser routing. |
| `tokens:thought` | `{"token": str}` for `<think>` stream output. |
| `tokens:chat` | `{"token": str}` for final-answer stream output. |
| `generation:finished` | Parsed thought, response, truncation flags, and diagnostics. |
| `iteration:finished` | Agentic iteration index, thought, response, and diagnostics. |
| `loop:finished` | Agentic loop iteration count. |

Subscriber callbacks receive a dict payload. Exceptions raised by one subscriber
are suppressed so telemetry cannot break inference.

---

## 7. Data Flow: Single Generation

```
User input → WorkbenchWorkspace._send()
  │
  ├── 1. retrieve RAG chunks (if RAG checkbox enabled)
  │      AppState.rag.retrieve(query, top_k=AppState.rag_top_k,
  │                             threshold=AppState.rag_threshold)  ← Phase 2.1
  │
  ├── 2. add user message to chat_history (SessionTree)
  │      user_node = chat_history.add_message("user", text)
  │
  ├── 3. chat_view.push_user(text, user_node.id)
  │
  ├── 4. spawn LLMThread(system_prompt, list(chat_history), hyperparams, chunks)
  │
  └── LLMThread.run():
        ├── importlib.reload(core.interaction_loop)
        ├── llm = ModelLoader.get_instance()
        ├── trimmed = _trim_history(chat_history)
        ├── prompt = build_prompt(system_prompt, trimmed)
        ├── open .tokens archive file
        ├── streaming loop (with auto-continuation)
        ├── TraceLogger.log_generation(
        │     model_name=ModelLoader.model_name(),   ← Phase 1.1
        │     adapter_name=AppState.adapter_name,
        │     workflow=..., template=..., ...)
        └── emit generation_finished(thought, response, truncated, ended_in_thought)
              → WorkbenchWorkspace._on_done()
                  ├── node = chat_history.add_message("assistant", response)
                  ├── chat_view.finalize_stream(node.id)
                  ├── enable feedback buttons
                  └── status_changed.emit("idle", False)
```

---

## 8. Data Flow: Agentic Loop

```
WorkbenchWorkspace._start_agentic()
  → AgenticThread(system_prompt, list(chat_history), hyperparams)

AgenticThread.run():
  while not stop_requested:
    ├── emit new_thought_token("[LOOP iteration N]")
    ├── _trim_history()
    ├── build_prompt()
    ├── _run_single_generation()    ← same streaming logic as LLMThread
    ├── TraceLogger.log_generation()
    ├── chat_history.append(response)   ← response only; no <think>
    ├── emit iteration_finished(i, thought, response)
    ├── importlib.reload(core.agentic_loop)
    ├── if not should_continue(i, response): break
    └── chat_history.append({"role":"user", "content": build_next_prompt(response, i)})
  emit loop_finished(total)
      → WorkbenchWorkspace._on_loop_done()
          ├── merges new agentic turns back into main SessionTree
          └── chat_view re-renders all messages with branch IDs
```

---

## 9. Training Data Flow (Unsloth Path)

```
Workbench interaction
  → thumbs_up  → TrainingCurator.save_example(prompt, response, source="thumbs_up")
  → thumbs_down → save_example(..., source="thumbs_down")       ← Phase 2.2
  → corrected  → save_example(..., source="corrected")
  All written to: data/training/curated.jsonl

Training Studio → Export tab
  → SFT:  curator.export_unsloth(path)
          Output: {instruction, input, output, source, timestamp}
  → DPO:  curator.export_dpo(path)         ← Phase 4.2
          Output: {prompt, chosen, rejected}
          (pairs thumbs_up chosen with thumbs_down rejected on same prompt)

Training Studio → Train tab               ← Phase 3.3
  → DetectHFModel("data/hf_models/")
  → TrainingThread(adapter_name, config, dataset_path)
      → peft + trl SFTTrainer
      → emits loss per step → Training log view
      → saves adapter to data/adapters/<name>/
```

---

## 10. RAG Data Flow

```
Knowledge Base → ingest file
  RAGPipeline.ingest_file(path, chunk_size, overlap):  ← chunk_size/overlap: Phase 3.1
    ├── extract_text(path)      PDF / DOCX / TXT / MD / PY / CSV
    ├── chunk_text(text, chunk_size, overlap)
    ├── encoder.encode(chunks)  all-MiniLM-L6-v2
    ├── index.add(embeddings)   FAISS flat L2
    ├── documents.append({text, source_file, chunk_id, ingested_at})
    └── save_index()            writes index.faiss + metadata.json

On each generation (RAG enabled):
  retrieve(query, top_k, source_filter=None):
    ├── 1. Run Exact-Match Hybrid Search Heuristics (Distance 0.0, Rank 0):
    │      ├── Department checks: list/count employees in EVS, Marketing, IT, Finance, Admin
    │      ├── Alphanumeric ID checks: match codes like EMP001, EMP025
    │      ├── Chapter/Section checks: parse "19.3", "Chapter 20" (supports spaces/case)
    │      └── Topic keyword checks: parse titles like "continuing obligations", "final pay"
    ├── 2. Run Dense Vector Search (if exact matches don't satisfy top_k):
    │      ├── encoder.encode([query])
    │      └── index.search(query_vector, fetch_k)
    └── 3. Filter by distance threshold (AppState.rag_threshold)   ← Phase 2.1
```

---

## 11. Design System

The current UI theme contract is documented in `docs/06_ui_architecture.md`.
`app/ui/themes.py` owns named palettes and compiles QSS dynamically from the
active `AppState` theme preset, custom accent, theme mode, and layout preset.

```python
# app/ui/themes.py
THEMES = {...}                  # named palettes
PALETTE = THEMES["Karl Obsidian Core"]
MONO = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace"
get_theme_colors(state) -> dict
get_theme_stylesheet(state) -> str
```

Default `Focused Workbench` layout uses 12 px outer workspace padding and 10 px
standard spacing. Styling hooks are object names such as `#workspace-root`,
`#sidebar`, `#panel`, `#section-header`, `#btn-primary`, and `#reasoning-view`.

---

## 12. File System Layout

```
data/
├── model_registry.json        ← source-controlled; 4 tiers; n_ctx: 4096–32768
├── active_model.json          ← written at runtime (gitignored)
├── models/                    ← gitignored (.gguf files)
├── hf_models/                 ← gitignored (HuggingFace weights for LoRA training)
├── adapters/                  ← gitignored (trained LoRA adapters)
├── logs/
│   ├── traces/                ← gitignored (JSONL, one per day, rotates at 50 MB)
│   └── raw/                   ← gitignored (.tokens files, one per generation)
├── sessions/                  ← gitignored (saved conversation JSON)
├── training/                  ← gitignored (curated.jsonl, export files)
├── prompt_pairs/              ← gitignored (Prompt Lab saved pairs, Phase 3.2)
└── vector_db/
    ├── index.faiss            ← gitignored
    └── metadata.json          ← gitignored
```

---

## 13. Advanced Introspection & Optimization

### 13.1 BPE Tokenizer Visualizer
Exposes live byte-pair encoding structure:
- **Encoding API**: Calls the active model's `.tokenize(text.encode())` dynamically via Python bindings.
- **Classification Rules**: Splits returned tokens into categories:
  * `special`: structural tokens (like `<think>`, `</think>`, or ChatML markers) — colored in red
  * `punctuation`: standard symbols — colored in blue/cyan
  * `word-start`: starting characters of standard words — colored in purple
  * `continuation`: subword fragments — colored in orange
- **Live Statistics**: Displays the total count of tokens and generation speed (tokens/sec) next to panel headers in the Workbench and Prompt Lab.

### 13.2 Cognitive Roll-Up Compression
Automatic context budget compression that triggers when the context window usage reaches a threshold:
- **Trigger**: When prompt + generated tokens exceed **80% of `n_ctx`** (the active model's registry limit).
- **Execution**: Runs a separate low-temperature summarization query using the local model to condense past reasoning thoughts inside the active path.
- **Continuation**: Replaces the redundant historical thought stream with the summary block, restoring the budget without interrupting response formatting.

### 13.3 Adapter Steerability & Pre-seeding
Manages generation parameters dynamically based on the active LoRA overlay:
- **Greeting Adapters**: If the active adapter is `"custom_greeting"`, short greeting queries (e.g. `"hi"`, `"hello"`) skip thought pre-seeding (`<think>\n`), allowing immediate direct responses.
- **Math Solver Adapters**: If the active adapter is `"math_solver"`, the compiler pre-seeds `<think>\n` to force standard chain-of-thought formatting.
- **RAG Integration**: Preserves custom pirate system prompts or injected RAG context strings instead of overriding with static defaults when adapters are loaded.

---

## 14. VS Code / Code OSS Bridge

Karl has two user-facing shells over the same local engine:

```
PyQt6 desktop app
  -> MainWindow / workspaces
  -> AppState
  -> engine threads, RAG, trace logger, training curator, ModelLoader

VS Code / Code OSS extension
  -> vscode-extension/extension.js webview
  -> ws://localhost:<port>
  -> app/engine/websocket_server.py
  -> engine threads, RAG, trace logger, training curator, ModelLoader
```

The extension is intentionally a thin editor client. It owns editor-native
behavior such as command registration, selection capture, webview rendering,
and opening diffs. Karl owns model execution, training, retrieval, traces,
evals, adapters, and agent orchestration.

Current bridge class:

```python
# app/engine/websocket_server.py
class WebSocketServerManager:
    get_instance(port=8080) -> WebSocketServerManager
    reset_instance() -> None
```

The bridge runs as WSS using Karl-managed localhost certificates from
`data/ssl/localhost.crt` and `data/ssl/localhost.key`. Startup tries the preferred
port and then the next nine ports to survive local conflicts. Service discovery is
written to `~/.karl/service_discovery.json`.

Connections must present a valid token in the WebSocket URL query string. Tokens
live in `data/bridge_token.json`, may be supplied by `KARL_BRIDGE_TOKEN`, and carry
RBAC scopes such as `read:telemetry`, `read:kb`, `write:kb`, and `admin:execute`.
Each incoming frame is validated as JSON-RPC 2.0 before dispatch:

| Error | Condition |
|-------|-----------|
| `-32700` Parse error | Invalid JSON frame. |
| `-32600` Invalid Request | Non-object request, missing `jsonrpc: "2.0"`, or missing method. |
| `-32601` Method not found | Method not in the bridge registry. |
| `-32602` Invalid params | Required method parameters missing or malformed. |
| `-32603` Internal error | Handler exception; details are returned in `error.data`. |

Current JSON-RPC methods:

| Method | Engine path | Purpose |
|--------|-------------|---------|
| `get_runtime_status` | `WebSocketServerManager._runtime_status()` | Return active model, adapter, context, RAM, bridge clients, and running state. |
| `list_models` | `WebSocketServerManager._list_models()` | Return registered and locally installed GGUF models with active/install state. |
| `set_active_model` | `WebSocketServerManager._set_active_model()` | Write `data/active_model.json` and reset `ModelLoader` for the next generation. |
| `list_prompt_pairs` | `WebSocketServerManager._list_prompt_pairs()` | Read saved Prompt Lab pairs from `data/prompt_pairs/`. |
| `get_prompt_pair` | `WebSocketServerManager._get_prompt_pair()` | Load one saved Prompt Lab pair. |
| `save_prompt_pair` | `WebSocketServerManager._save_prompt_pair()` | Save a named A/B prompt pair using Karl's Prompt Lab schema. |
| `delete_prompt_pair` | `WebSocketServerManager._delete_prompt_pair()` | Delete one saved Prompt Lab pair. |
| `submit_task` | `SwarmOrchestratorThread` | Run the local Architect/Coder/Tester swarm against a workspace path. |
| `submit_chat` | `LLMThread` or `AgenticThread` | Stream local chat or agentic-loop output to the editor. |
| `stop_task` | active QThread | Stop the running swarm/chat task. |
| `compute_diff` | `prompt_lab.generate_char_diff_html` | Produce Prompt Lab diff HTML. |
| `list_codex_topics` | `data/codex_library/` | List local reference topics. |
| `get_codex_content` | `data/codex_library/` | Return one local reference page. |

Current notifications:

| Notification | Meaning |
|--------------|---------|
| `status_update` | Log/status message. |
| `task_plan_created` | Architect generated a task plan. |
| `file_edited` | Coder produced replacement content for a file. |
| `test_result` | Tester command passed or failed. |
| `finished_swarm` | Multi-agent run ended. |
| `chat_thought_token` | Reasoning token from `<think>` stream. |
| `chat_response_token` | Final answer token. |
| `chat_finished` | Chat generation completed. |

File writes from agents are transactional from the editor's point of view:

1. WebSocket server emits `file_edited`.
2. Extension creates `<target>.original` if one does not already exist.
3. Extension writes proposed content to the target file.
4. Extension opens a VS Code diff between backup and modified file.
5. User accepts by deleting the backup or rolls back by restoring it.

This keeps autonomous code edits visible and reversible. Future multi-file
agent runs should extend the same idea with a task ID and a transaction manifest
so an entire run can be accepted or reverted as one unit.

The detailed extension product plan and API roadmap live in
[`docs/08_vscode_extension.md`](08_vscode_extension.md).
