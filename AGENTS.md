# AGENTS.md — Handoff Document for AI Agents

> **Written for AI coding agents. Read this before touching any code.**
> This file describes the exact current state of the repo — what is done,
> what is incomplete, what is broken, and what must be built next.
> Every claim here is accurate as of the last Phase 1 commit.

---

## What Is Karl?

Karl is a privacy-first, offline LLM **Introspection Environment** for prompt engineers.
It runs DeepSeek-R1 locally via `llama-cpp-python` (compiled from source, no pre-built
binaries). Karl exposes the model's raw reasoning in real time, logs every generation
to an immutable JSONL trace, and lets the user manipulate prompt construction via
hot-reloadable Python scripts.

**Target platform:** Arch Linux (and any modern Linux). Not Windows.
**Philosophy:** "UI for convenience, Code for control, Introspection for insight."

---

## Architecture Overview

Karl is a PyQt6 application with a sidebar-based multi-workspace layout.

```
MainWindow
├── Sidebar (fixed 56px)          app/ui/sidebar.py
├── QStackedWidget                 ← one child per workspace
│   ├── [0] WorkbenchWorkspace     app/ui/workspaces/workbench/workspace.py
│   ├── [1] PromptLabWorkspace     app/ui/workspaces/prompt_lab.py
│   ├── [2] KnowledgeBaseWorkspace app/ui/workspaces/knowledge_base.py
│   ├── [3] VisionWorkbench        app/ui/workspaces/vision_workbench.py
│   ├── [4] TrainingStudioWorkspace app/ui/workspaces/training_studio/__init__.py
│   ├── [5] EvalSuiteWorkspace     app/ui/workspaces/eval_suite.py
│   ├── [6] SwarmStudioWorkspace   app/ui/workspaces/swarm_studio.py
│   ├── [7] SystemConfigWorkspace  app/ui/workspaces/system_config/workspace.py
│   ├── [8] DocsWorkspace          app/ui/workspaces/docs.py
│   └── [9] FlywheelStudioWorkspace app/ui/workspaces/flywheel_studio.py
└── StatusBar (fixed 24px)         app/ui/widgets/status_bar.py
```

### AppState — Shared State Container

`app/state.py` is instantiated once in `MainWindow.__init__()` and passed to every
workspace constructor. Workspaces communicate through it; they never reference
`MainWindow` directly.

```python
class AppState:
    rag:          RAGPipeline       # persistent FAISS vector DB
    memory:       MemoryManager     # session save/load
    logger:       TraceLogger       # JSONL generation log
    curator:      TrainingCurator   # curated training examples
    model_name:   str               # updated by SystemConfigWorkspace on model load
    adapter_name: str | None        # updated when a LoRA adapter is active
    generating:   bool              # set by WorkbenchWorkspace during generation
```

### Design System

All styling is generated from `app/ui/themes.py`:
- `THEMES` dict: named palettes with accent, surface, text, semantic, glow, and motion tokens
- `PALETTE` alias: Karl Obsidian Core defaults
- `MONO` string: JetBrains Mono → Fira Code → Cascadia Code → Consolas → Courier New
- `get_theme_stylesheet(state)` compiles dynamic QSS from theme, accent, mode, and layout preset
- Default workspace outer padding is 12px in Focused Workbench layout
- Object names (`#workspace-root`, `#sidebar`, `#panel`, `#section-header`, `#btn-primary`, etc.) are the hook points in QSS
- Sidebar and custom icon buttons set accessible names/descriptions for screen readers

### The Extension Points (Hackable Core)

These files are hot-reloaded on every generation via `importlib.reload()`.
The user is expected to edit them directly. Do NOT add complex dependencies here.

| File | Controls |
|------|----------|
| `core/interaction_loop.py` | `build_prompt(system, history) -> str` — ChatML construction |
| `core/prompt_templates.py` | Named prompt templates. `get_template(name, **kwargs) -> str` |
| `core/workflows.py` | Workflow definitions (template, RAG top-k, output schema, grader) |
| `core/cognitive_parser.py` | `parse_thought_stream(raw) -> (thought, response)` — state machine |
| `core/agentic_loop.py` | `should_continue(iter, response)` and `build_next_prompt(response, iter)` |

### Editor Extension Integration

Karl is equipped with a native VS Code/Code OSS editor extension (`vscode-extension/`) that acts as a client to the running Karl PyQt6 desktop application.

* **Architecture**: The extension is a Webview panel that executes HTML5/JavaScript UI logic, proxying RPC calls to Karl's WebSocket server over local secure ports.
* **Message Protocol (`postMessage`)**: The Webview and VS Code host communicate via JSON messages. The host forwards connections and editor status telemetry (`cockpit_state_update`) to the Webview and processes workspace file writes (`queue_file_edit`) proposed by the agents.
* **Performance Rendering**: To prevent DOM fragmentation, tokens are appended directly to existing `.token-appear` nodes. Scroll recalculations are throttled using `requestAnimationFrame` to avoid layout reflow thrashing.
* **Focus Management**: Switching workspaces within the extension automatically focuses the primary inputs (`chatInput`, `objective`, or `kbQuery`) to keep the user's hands on the keyboard.

### Threading Model

- `LLMThread(QThread)` — single-shot generation. `app/engine/llm_thread.py`
- `AgenticThread(QThread)` — autonomous multi-iteration loop. `app/engine/agentic_thread.py`
- Both emit: `new_thought_token(str)`, `new_chat_token(str)`, `new_raw_token(str)`
- `LLMThread` additionally emits: `generation_finished(thought, response, truncated, ended_in_thought)`
- `AgenticThread` additionally emits: `iteration_finished(index, thought, response)`, `loop_finished(total)`
- Both emit: `error_occurred(str)`
- Both also publish non-UI telemetry through `EventBroker` topics such as
  `tokens:raw`, `tokens:thought`, `tokens:chat`, `generation:finished`,
  `iteration:finished`, and `loop:finished`.
- **Rule:** Never touch UI widgets from inside `run()`. Emit signals only.
- `WorkbenchWorkspace` owns `chat_history` and creates/destroys threads.

### The Streaming Parser (Inline, Both Threads)

The threads do NOT call `cognitive_parser.parse_thought_stream()` — they contain their
own inline streaming state machine that routes tokens in real time:

1. Prompt pre-seeds `<think>\n`, so `in_thought = True` at start
2. Token accumulates into `buffer`
3. Suffix guards prevent flushing mid-tag:
   `["<", "<t", "<th", "<thi", "<thin", "<think"]` for open guard
   `["<", "</", "</t", "</th", "</thi", "</thin", "</think"]` for close guard
4. `</think>` detection → `in_thought = False`, routes remainder to `new_chat_token`
5. Auto-continuation: if `finish_reason == "length"`, appends `raw_output` to prompt and
   re-queries the model (up to 5 passes)
6. Everything is flushed on loop exit

`cognitive_parser.parse_thought_stream()` is used for batch post-processing only
(e.g., `engine_test.py`). It is a state machine that handles any tag capitalisation,
multiple `<think>` blocks, and unclosed tags.

### ModelLoader

`app/engine/model_loader.py` — thread-safe singleton.

```python
ModelLoader.get_instance(model_path=None, adapter_name=None, draft_model_path=None) -> Llama
ModelLoader.reset_instance()              # unloads active model and draft handles
ModelLoader.model_name() -> str           # basename of loaded GGUF
ModelLoader.is_loaded()  -> bool
ModelLoader.n_ctx()      -> int           # loaded context or registry fallback
```

- Protected by `threading.RLock()` — safe to call from engine/UI threads
- Reads `data/active_model.json` at first call to determine which GGUF to load
- Falls back to `deepseek-r1-1.5b.gguf` if the specified file is missing
- Reads `n_ctx` and `n_batch` from `data/model_registry.json` for the active model
- Loads with GPU offload (`n_gpu_layers=-1`), memory mapping, and memory locking
- If host `mlock` limits fail, retries with `use_mlock=False` and logs ulimit guidance
- If VRAM allocation fails, halves `n_ctx` down to 2048 before surfacing a terminal error
- On multi-GPU hosts, tries a free-VRAM-proportional `tensor_split` before single-GPU fallback
- Supports optional draft-model speculative decoding and optional 8-bit KV cache (`type_k`/`type_v`)
- Circuit breaker trips after 3 terminal load failures and blocks repeated reload attempts for 30 seconds

### The Trace Logger

`app/utils/trace_logger.py` writes JSONL to `data/logs/traces/trace_YYYY-MM-DD.jsonl`.
Rotation threshold is configurable via the `log_rotation_size_mb` config key
(default **10 MB**; the module constant `_MAX_BYTES` is 50 MB but the config
default takes precedence). Each entry has this schema:

```json
{
  "id": "uuid4",
  "session_id": "uuid4",
  "timestamp": "ISO8601",
  "timing": {
    "total_seconds": 0.0,
    "prefill_seconds": 0.0,
    "generation_seconds": 0.0,
    "prefill_tps": 0.0,
    "generation_tps": 0.0,
    "total_tps": 0.0,
    "prompt_tokens": 0,
    "generation_tokens": 0
  },
  "gpu_temp_c": null,
  "throttle_reasons": [],
  "cooling_duration_sec": 0.0,
  "model": "model-filename.gguf",
  "adapter": null,
  "workflow": "general_chat",
  "template": "reasoning_minimal",
  "hyperparams": { "temperature": 0.7, "top_p": 0.95, "max_tokens": 2048 },
  "system_prompt": "",
  "compiled_prompt": "...",
  "thinking": "...",
  "response": "...",
  "raw_output": "...",
  "rag_chunks": [],
  "feedback": "none | thumbs_up | thumbs_down | corrected",
  "corrected_response": null,
  "warning": "(optional — present only when thermal throttle was detected)"
}
```

This schema is the Unsloth SFT/DPO source. `feedback` + `corrected_response` drive the
training curator export.

**Encryption & archival:** On rotation, `_archive_log()` gzip-compresses the file
in RAM, then Fernet-encrypts it (PBKDF2-HMAC-SHA256, 100 000 iterations, salt =
hardware motherboard UUID). The key is zeroed via `_zero_bytes()` on a mutable
`bytearray`. `mlockall(MCL_CURRENT | MCL_FUTURE)` prevents the key from being
paged to disk during encryption; `munlockall()` releases the lock immediately after.
Encrypted archives land in `data/logs/archive/` with a `.jsonl.enc` suffix.

**Retention:** `enforce_retention_policy()` deletes `.jsonl`, `.gz`, `.enc`, and
`.tokens` files older than `log_retention_days` (default 30), then enforces a
`max_log_disk_size_mb` quota (default 1024 MB) by deleting oldest-first.

### The RAG Pipeline

`app/utils/rag_pipeline.py` — persistent FAISS index + SQLite metadata.
See `docs/02_rag_pipeline.md` for the full technical reference.

- Embedding model: `all-MiniLM-L6-v2` (sentence-transformers)
- Vector index: `data/vector_db/index.faiss` (FAISS `IndexIDMap2`, flat L2)
- Metadata: `data/vector_db/meta.db` (SQLite WAL) — migrated from legacy `metadata.json`
- `ingest_file(path, chunk_size=200, overlap=50)` — PDF/DOCX/TXT/MD/PY/CSV → chunk → embed
- `ingest_text(text, source_name, chunk_size, overlap)` — ingest a raw string
- `retrieve(query, top_k=3, source_filter=None, distance_threshold=None) -> list[str]`
- `retrieve_with_metadata(query, top_k, ...) -> list[dict]` — includes `distance`, `rank`
- `retrieve_sparse(query, top_k=5, ...) -> list[dict]` — TF-IDF cosine similarity
- `retrieve_hybrid(query, top_k=3, rrf_constant=60, use_reranker=False, rerank_candidates=15) -> list[dict]`
  — Reciprocal Rank Fusion of dense + sparse; optional CrossEncoder reranking
- `eval_retrieval(query, expected_ids, top_k) -> dict` — hit@1, hit@3, hit@k, MRR

### The Training Curator

`app/utils/training_curator.py` — captures training examples.
See `docs/03_training_curator.md` for the full technical reference.

- Saves to `data/training/curated.jsonl` (HuggingFace chat format)
- `save_example(system_prompt, user_msg, good_response, source)` — source one of:
  `thumbs_up`, `corrected`, `thumbs_down`, `eval_chosen`, `eval_rejected`
- `export_unsloth(output_path) -> str` — balanced SFT JSONL, `{"messages": [...]}`
- `export_dpo(output_path) -> str` — paired `{prompt, chosen, rejected}` JSONL
- `save_eval_result(report) -> str` — persists eval report; auto-generates DPO pairs
- `list_eval_results() -> list[dict]` — metadata for all saved eval reports

---

## Current State — What Is Done vs. Incomplete

### ✅ Fully Implemented

| Component | File(s) |
|-----------|---------|
| Sidebar navigation | `app/ui/sidebar.py` |
| Design system + QSS | `app/ui/themes.py` |
| AppState container | `app/state.py` |
| Status bar (model, state, RAM) | `app/ui/widgets/status_bar.py` |
| Main window shell | `app/ui/main_window.py` |
| WorkbenchWorkspace — chat, docks, sessions, params drawer, branching, feedback | `app/ui/workspaces/workbench/workspace.py` |
| KnowledgeBaseWorkspace — drag/drop ingest, source list, chunk inspector, search tester, sandbox | `app/ui/workspaces/knowledge_base.py` |
| PromptLabWorkspace — A/B streaming, saved pairs, diff view, tokenizer, model compare | `app/ui/workspaces/prompt_lab.py` |
| VisionWorkbench — saved images, OCR, and screenshot reasoning | `app/ui/workspaces/vision_workbench.py` |
| TrainingStudioWorkspace — flywheel, dataset, SFT/DPO export, LoRA/QLoRA, auto-train, Mini-GPT | `app/ui/workspaces/training_studio/__init__.py` |
| EvalSuiteWorkspace — dataset editor, run progress, result tree, grader controls | `app/ui/workspaces/eval_suite.py` |
| SwarmStudioWorkspace — task graph, file proposals, verification traces | `app/ui/workspaces/swarm_studio.py` |
| SystemConfigWorkspace — model registry, quantization, defaults, MCP, theme, observability, hardware | `app/ui/workspaces/system_config/workspace.py` |
| DocsWorkspace — local Codex reference browser | `app/ui/workspaces/docs.py` |
| FlywheelStudioWorkspace — telemetry and fine-tuning loop metrics | `app/ui/workspaces/flywheel_studio.py` |
| ModelLoader thread-safety | `app/engine/model_loader.py` |
| cognitive_parser state machine | `core/cognitive_parser.py` |
| Trace logger (new schema + rotation) | `app/utils/trace_logger.py` |
| LLMThread streaming + auto-continuation | `app/engine/llm_thread.py` |
| AgenticThread loop + hot-reload | `app/engine/agentic_thread.py` |
| RAG pipeline (persistent FAISS) | `app/utils/rag_pipeline.py` |
| Training curator (Unsloth SFT export) | `app/utils/training_curator.py` |
| Eval harness + 5 graders | `eval/harness.py`, `eval/graders.py` |
| Hardware scout | `core/hardware_scout.py` |
| AppState persistence (save_to_disk / load_from_disk) | `app/state.py`, `app/engine/config_store.py` |
| Agent profile registry with reload + custom agents | `app/ui/workspaces/workbench/profiles.py` |

> **All previously noted ⚠️ issues have been resolved.** The two items below are the
> only remaining functional gaps (by design — they require HF weights and GPU infrastructure
> that are not included in the repo):

### ⚠️ Implemented but Requires External Assets

| Issue | File | What's Required |
|-------|------|-----------------|
| LoRA/QLoRA training | `app/ui/workspaces/training_studio/__init__.py` | HuggingFace model weights in `data/hf_models/`; `peft`+`trl` installed |
| Speculative decoding | `app/engine/model_loader.py` | Compatible draft GGUF in `data/draft_model.json`; `llama-cpp-python` with draft support |



---

## Completion Plan

Work proceeds in strict phase order.
**Do not start Phase N+1 until Phase N is fully committed and pushed.**

The plan is intentionally broken into sub-phases where the work is complex,
architecturally significant, or high-risk. Simple phases (1, 2, 5) are done in
one commit. Complex phases (3, 4) are split into isolated sub-commits so that a
failure in one sub-phase cannot corrupt the others.

---

> **Progress Legend:** ✅ = completed · 🔨 = in progress · ⬚ = not started
> **All phases complete. Karl is fully built.**


### ✅ Phase 1 — Wire It Together *(completed)*
**One commit. Six targeted bug fixes. No new architecture, no new files.**
All items are in existing files. All are mechanical. Do them together.

1. Fix `llm_thread.py` trace_logger call: pass `model_name=ModelLoader.model_name()`,
   `adapter_name`, `workflow`, `template`
2. Fix `agentic_thread.py`: same fields; also replace synthetic
   `rag_context=[f"agentic_iteration_{n}"]` with actual `[]`
3. Model-aware context budget: add `ModelLoader.n_ctx() -> int` that reads `n_ctx`
   from `data/model_registry.json` for the loaded model; both threads use it instead
   of hardcoded `_CONTEXT_BUDGET = 4096`
4. `memory_manager.save_session()`: strip `<think>...</think>` from all assistant
   content before writing to disk
5. `eval/harness.py`: add `ModelLoader.is_loaded()` guard at top of `run()`;
   implement `progress_cb(current, total)` call inside the case loop
6. Workbench params drawer: collapsible `QWidget` above input bar exposing
   temperature, top-p, max-tokens spinboxes; writes to `self._hyperparams`

---

### ✅ Phase 2 — Complete the Data Pipeline
**One commit. Five wiring tasks. Connects existing components.**

1. Add `rag_threshold: float` and `rag_top_k: int` to `AppState`;
   KB workspace writes them; Workbench reads them at `retrieve()` call
2. Add thumbs-down button to Workbench feedback row;
   wire to `curator.save_example(source="thumbs_down")`
3. Connect `MemoryManager` to Workbench: left sessions list, `save_session()` on
   new session / exit, `load_session()` on click
4. When user rates a generation, update the `feedback` field on that trace log entry
   (rewrite the last line of the JSONL file)
5. `training_curator.export_unsloth()`: return path string only; remove tuple

---

### ✅ Phase 2.5a — UX Polish: Workbench
**One commit. Layout and visual hierarchy only. No new functionality.**
Phase 1 and 2 must be complete first — both add controls to Workbench (params drawer,
sessions panel, thumbs-down button). Polish an incomplete interface and you polish it twice.

Rules for this phase and all 2.5 sub-phases:
- No new features, no new signals, no new data
- Every change is spacing, sizing, proportion, visual hierarchy, or removing clutter
- If a change requires new logic, it belongs in a different phase

Tasks:
1. Reasoning panel / chat panel split ratio — verify it feels balanced at 1280×768
2. Chat message bubbles — padding, font size, role label weight and spacing
3. Input area — height, placeholder text, send button prominence vs ghost buttons
4. Params drawer — open/close animation feel, control alignment inside drawer
5. Sessions panel — row height, selected state, new session button placement
6. Feedback row — thumbs-up/down/correct buttons spaced and weighted correctly
7. Overall: nothing cramped, nothing orphaned, clear visual flow top to bottom

---

### ✅ Phase 2.5b — UX Polish: Knowledge Base + Prompt Lab
**One commit. Two workspaces, similar visual language.**

Knowledge Base:
1. Left panel: source list row height, stats label placement, ingest controls grouping
2. Chunk size/overlap controls (added in 3.1) — pre-polish their layout here
3. Right panel: search input + button alignment, results view typography and spacing
4. Threshold/top-k controls — inline with labels, not a wall of fields

Prompt Lab:
1. A/B columns — equal width, header labels clear, no visual competition
2. System prompt editors — height proportional, not dominant
3. Output panels — monospace, sufficient line height, scrollable without feeling cramped
4. Run buttons — weighted correctly relative to output panels
5. Diff view placeholder space (Phase 3.2 will fill it) — reserve it cleanly

---

### ✅ Phase 2.5c — UX Polish: Training Studio + Eval Suite *(completed)*
**One commit. Both are data-heavy tabbed workspaces.**

Training Studio:
1. Stats row — numbers prominent, not buried in muted text
2. Dataset tab: list rows scannable, preview panel proportioned
3. Export tab: section headers clear, buttons weighted to action importance
4. Train tab: config rows consistent alignment, LoRA params readable at a glance
5. Training log view — fixed height, monospace, not competing with config

Eval Suite:
1. Left panel: dataset path row compact, summary stats prominent after run
2. Results tree: column widths useful (case name wide, pass narrow, response truncated cleanly)
3. Detail panel: proportioned so you can read a full result without scrolling constantly
4. Progress bar placement and visual weight during run

---

### ✅ Phase 2.5d — System Config + Global Consistency Pass *(completed)*
**One commit. Simplest workspace + cross-workspace audit.**

System Config:
1. Four tabs — labels clear, no ambiguity about what each contains
2. Settings rows — label width consistent, controls right-aligned, units visible
3. Model list display — filename, size, active indicator
4. Hardware readout — values prominent, labels muted

Global pass (review all workspaces together):
1. Margin/padding consistency — every workspace uses the same outer padding (12px)
2. Section header style — all use the same `#section-header` object name and spacing
3. Separator usage — `_hline()` used consistently, not overused
4. Font sizes — body 10pt, muted labels 9pt, section headers 8pt everywhere
5. Button hierarchy — primary/ghost/danger used correctly and consistently
6. Scrollbar visibility — thin, present when needed, not intrusive

---

### ✅ Phase 3.1 — Small Workspace Fixes *(completed)*
**One commit. Two mechanical additions. Low risk.**

1. KB workspace: add chunk_size and overlap spinboxes before ingest button;
   pass values to `ingest_file(filepath, chunk_size, overlap)`
2. Eval Suite: connect EvalSuiteWorkspace progress bar to `progress_cb` now
   implemented in `harness.run()`

---

### ✅ Phase 3.2 — Prompt Lab Completion *(completed)*
**One commit. Self-contained UI feature. Medium risk.**

1. After both A/B runs complete, render character-level diff of the two outputs
   (use `difflib.ndiff` or similar; color-code additions/deletions inline)
2. Save/load named prompt pairs to `data/prompt_pairs/<name>.json`;
   add a pairs list in the Prompt Lab left panel

---

### ✅ Phase 3.3 — LoRA / QLoRA Training Thread *(completed)*
**One commit. Highest-risk phase. Isolated for safety.**
Do not mix with 3.1 or 3.2 changes.

Dependencies required: `peft`, `trl`, `transformers`, `datasets`
HF model weights must be in `data/hf_models/`

1. Detect HF model presence; if absent, show clear download instructions and
   disable Train button — export must still work regardless
2. `TrainingThread(QThread)` running `trl.SFTTrainer`; emits `loss(step, value)`,
   `progress(step, total)`, `done(adapter_path)`, `error(msg)`
3. Training Studio wires thread signals to loss log view and progress bar
4. Trained adapter saved to `data/adapters/<name>/`
5. `ModelLoader` gains adapter load/unload capability
6. QLoRA path: if `bitsandbytes` available, offer 4-bit quantised training via checkbox

Exit criterion: training runs on a 5-example dataset, loss curve visible, adapter saved.

---

### ✅ Phase 3.4 — System Config Model Registry Browser *(completed)*
**One commit. Self-contained workspace enhancement. Low risk.**

1. Read `data/model_registry.json`; render tier table (name, RAM req, n_ctx, file size)
2. Download button per tier: `requests` stream to `data/models/` with progress bar
3. On download complete, set as active model via `ModelLoader.reset_instance()` +
   write `data/active_model.json`

---

### ✅ Phase 4.1 — Tokenizer Visualization *(completed)*
**One commit. Self-contained display feature. Low risk.**

1. Add tokenizer panel to Prompt Lab (or collapsible drawer in Workbench)
2. Call `ModelLoader.get_instance().tokenize(text.encode())` on input text
3. Render tokens as colored inline spans with token IDs on hover
4. Color tokens by rough type: punctuation, word-start, subword continuation, special

---

### ✅ Phase 4.2 — DPO Export Completion *(completed)*
**One commit. Depends on Phase 2.2 (thumbs-down) being complete.**

1. `training_curator.export_dpo(path)`: pair thumbs_up (chosen) with thumbs_down
   (rejected) on same prompt; write `{prompt, chosen, rejected}` JSONL
2. Training Studio Export tab: wire DPO button to new method
3. Output must be loadable by Unsloth without modification — verify against schema

---

### ✅ Phase 4.3 — Session Branching *(completed)*
**One commit. Highest architectural risk. Must be fully isolated.**
Read the R18 risk entry in `docs/07_risk_register.md` before touching this.

`chat_history` is currently `list[dict]`. This phase changes it to a tree.
All `chat_history` references must be replaced atomically in a single commit.
Do not introduce partial state.

1. `app/utils/session_tree.py`: `SessionNode(role, content, id, children[])`,
   `SessionTree` with active-path cursor, serialise/deserialise to JSON
2. Replace `self.chat_history: list[dict]` in `WorkbenchWorkspace` with `SessionTree`
3. Update `_trim_history()` to walk the active path of the tree
4. Add "branch from here" action on messages in `ChatView`
5. Branch navigator panel: shows tree of branches, switches active path on click
6. Update `MemoryManager` to serialise/deserialise `SessionTree`

Exit criterion: user can fork at any message, explore alternate path, navigate back.

---

### ✅ Phase 5 — Documentation, Tests, Accuracy  *(completed)*
**One commit. No code risk. Do last.**

1. Rewrote `README.md` for Linux/Arch — no PowerShell, no Windows paths
2. Rewrote `docs/01–03` and `docs/06` to match current architecture
3. `docs/04_architecture.md`, `docs/05_scope_and_milestones.md`,
   `docs/07_risk_register.md` — verified and updated to match completed Phase 4 state
4. `docs/05_multi_agent_swarm.md` — full reference for the Architect/Coder/Tester
   pipeline, dependency layering, cherry-pick review, self-correction loop, security
   sandbox, codebase memory integration, and Qt signal table
5. `docs/07_evaluation_suite.md` — complete reference for EvalHarness, all 5 graders,
   the eval-failure DPO curation pipeline, context resolution priority, and the
   Flywheel integration
6. `docs/08_vscode_extension.md` — postMessage API contract, DOM rendering
   optimisations, and focus-redirection rules documented
7. Updated `AGENTS.md` to reflect fully completed project
8. Created `tests/` directory with:
   - `tests/test_cognitive_parser.py` — all 5 state machine cases
   - `tests/test_cognitive_parser_fuzz.py` — fuzz tests for malformed/partial tags
   - `tests/test_trace_logger.py` — schema fields, rotation trigger
   - `tests/test_training_curator.py` — save, export, DPO pairing
   - `tests/test_session_tree.py` — node/tree ops, branching, serialization, duck-typing
   - `tests/test_eval_harness.py` — harness run loop, case processing, report structure
   - `tests/test_swarm.py` — orchestrator plan emission and signal flow
9. Fixed `engine_test.py`: uses `ModelLoader.get_instance()` and `ModelLoader.model_name()`
   instead of a hardcoded `Llama()` constructor with a hardcoded path


---

## Data Flows

### Single Generation
```
User input (Workbench)
  → retrieve RAG chunks (if enabled, using AppState.rag_threshold)
  → LLMThread(system_prompt, chat_history, hyperparams, chunks)
      → ModelLoader.get_instance()
      → importlib.reload(core.interaction_loop)
      → build_prompt() → llm() streaming
      → emit new_thought_token / new_chat_token per token
      → TraceLogger.log_generation(model_name=ModelLoader.model_name(), ...)
      → emit generation_finished
  → WorkbenchWorkspace._on_done()
      → append to chat_history (response only, no <think>)
      → enable feedback buttons
      → if thumbs_up: TrainingCurator.save_example()
```

### Agentic Loop
```
Same as above except AgenticThread runs:
  iteration 0: generate → check should_continue() → inject build_next_prompt()
  iteration 1: generate → check should_continue() → ...
  ...
  iteration N: should_continue() returns False OR max iterations reached
  → loop_finished(N) emitted
```

### Training Export Path (Unsloth)
```
Workbench interaction
  → thumbs_up / corrected → TrainingCurator.save_example() → data/training/curated.jsonl
  [future] thumbs_down → save_example(source="thumbs_down")

Training Studio → Export tab
  → SFT: TrainingCurator.export_unsloth(path) → Unsloth-ready JSONL
  → DPO: pair thumbs_up (chosen) with thumbs_down (rejected) → DPO JSONL
```

### Eval Flow
```
Eval Suite → pick dataset.jsonl → run
  → EvalThread → EvalHarness.run(path, progress_cb)
      → for each case: build context → LLMThread (headless) → grade
      → EvalReport(summary, cases)
  → results tree populated
```

---

## Key Gotchas

1. **`llama-cpp-python` must be compiled from source** on the user's CPU.
   Pre-built wheels may fail with `Illegal Instruction`.
   ```bash
   CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python --no-binary llama-cpp-python
   ```

2. **`HF_HUB_OFFLINE=1` must be set before any sentence-transformers import.** `main.py`
   sets this at the top of the file before any imports. If you write a new entry point or
   test runner, set it first.

3. **The streaming parser is duplicated in both threads.** Any fix to tag-parsing logic
   must be applied to both `llm_thread.py` and `agentic_thread.py`.

4. **The model singleton holds KV cache between agentic iterations** — intentionally.
   This makes the loop faster. If you need a clean slate per iteration, call
   `llm.reset()` before each generation (this will slow things down significantly).

5. **`data/model_registry.json` is source-controlled.** Edit it to add model tiers.
   `data/active_model.json` is written at runtime and is gitignored.

6. **GPUtil is optional.** If no discrete GPU is detected, `vram_gb` returns `0.0`.

7. **No `upgrade_manager.py` exists anymore.** It was removed. Do not reference or
   re-create it. Self-upgrade functionality has been permanently cut.

8. **`Karl-main/` was removed.** It was a stale snapshot of the original codebase and
   is no longer tracked. All active work is in the root. Do not re-create it.

9. **`AppState` is the only cross-workspace communication channel.** Workspaces must
   not import each other or reference `MainWindow`. If a new workspace needs to trigger
   something in another, add a field or signal to `AppState`.

10. **`QTextBrowser.append()` in `ChatView`** creates a new paragraph block, which is
    how user message HTML blocks are separated. After calling `insertHtml(_KARL_HDR)`,
    subsequent `cursor.insertText(token)` calls append to the same paragraph — this is
    the streaming mechanism. Do not call `append()` during an active stream.

---

## How to Run (Linux / Arch)

```bash
# Prerequisites
sudo pacman -S python python-pip cmake base-devel

# Clone and set up
git clone https://github.com/ethan-da-tech-wizard/karl ~/karl
cd ~/karl
python -m venv venv
source venv/bin/activate

# Build llama-cpp-python for your CPU
CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python --no-binary llama-cpp-python
pip install -r requirements.txt

# Download the default model (~1 GB)
python download_test_model.py

# Run Karl
python main.py

# Headless engine test (no UI, verifies model loads and generates)
python engine_test.py

# Run eval harness against a dataset
python eval/run_eval.py --dataset eval/datasets/grounded_answer.jsonl
```

---

## Repo Structure (Current)

```
Karl/
├── AGENTS.md                  ← YOU ARE HERE
├── README.md                  ← [outdated — needs rewrite for Linux, Phase 5]
├── main.py                    ← entry point; sets env vars, loads stylesheet, launches MainWindow
├── engine_test.py             ← headless inference test [hardcoded path — fix in Phase 5]
├── smoke_test.py              ← template/workflow smoke tests [hardcoded path — fix in Phase 5]
├── raw_test.py                ← raw token streaming test
├── download_test_model.py     ← downloads deepseek-r1-1.5b.gguf Q4_K_M
├── requirements.txt           ← pip deps; peft/trl/transformers/datasets are optional (Training Studio)
│
├── core/                      ← HACKABLE LAYER — hot-reloaded on every generation
│   ├── interaction_loop.py    ← build_prompt(system, history) -> str
│   ├── prompt_templates.py    ← named templates; get_template(name, **kwargs) -> str
│   ├── workflows.py           ← 4 workflow modes (general_chat, document_extractor, grounded_answer, code_review)
│   ├── cognitive_parser.py    ← parse_thought_stream(raw) -> (thought, response); state machine
│   ├── agentic_loop.py        ← should_continue() + build_next_prompt(); MAX_ITERATIONS=20
│   └── hardware_scout.py      ← get_hardware_profile() -> {ram_gb, vram_gb, storage_gb}
│
├── app/
│   ├── state.py               ← AppState: shared state passed to all workspaces
│   ├── engine/
│   │   ├── model_loader.py    ← thread-safe singleton; registry n_ctx; GPU fallback; circuit breaker
│   │   ├── llm_thread.py      ← LLMThread(QThread); streaming parser, watchdog, trace logging
│   │   ├── agentic_thread.py  ← AgenticThread(QThread); autonomous loop, streaming parser
│   │   ├── websocket_server.py ← secure JSON-RPC 2.0 WSS bridge; token scopes; /metrics
│   │   ├── config_store.py    ← atomic data/*.json config I/O and registry cache
│   │   └── event_broker.py    ← thread-safe in-process pub/sub telemetry bus
│   ├── ui/
│   │   ├── main_window.py     ← shell only: sidebar + stack + status bar
│   │   ├── sidebar.py         ← 10-button accessible nav; workspace_changed(int) signal
│   │   ├── themes.py          ← THEMES palettes; get_theme_stylesheet(state); MONO font stack
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   └── status_bar.py  ← model name, state text, RAM; set_model/set_state/set_adapter
│   │   └── workspaces/
│   │       ├── __init__.py
│   │       ├── workbench/        ← Workbench package; params, sessions, branching, feedback
│   │       ├── prompt_lab.py     ← Prompt Lab; A/B streams, saved pairs, diff, tokenizer
│   │       ├── knowledge_base.py ← chunk size/overlap controls; threshold wired to AppState (Phase 3.1 / 2.1)
│   │       ├── training_studio.py ← training requires HF weights; DPO export wired (Phase 3.3 / 4.2)
│   │       ├── eval_suite.py     ← progress_cb wired to harness (Phase 3.1)
│   │       └── system_config/    ← System Config package; model registry, runtime, hardware
│   └── utils/
│       ├── rag_pipeline.py    ← persistent FAISS; distance threshold wired via AppState.rag_threshold (Phase 2.1)
│       ├── memory_manager.py  ← <think> blocks stripped before session save (Phase 1)
│       ├── trace_logger.py    ← new schema (id, session_id, feedback, model, adapter, rotation)
│       └── training_curator.py ← curated.jsonl; export_unsloth() returns path string (Phase 2.5)
│
├── eval/
│   ├── harness.py             ← EvalHarness.run(); model guard + progress_cb wired (Phase 1 / 3.1)
│   ├── graders.py             ← 5 graders: exact_match, json_valid, keyword_hit, groundedness, not_in_context
│   ├── run_eval.py            ← CLI: --dataset, --dry-run, --output
│   ├── benchmark_rag.py       ← RAG retrieval benchmarking
│   └── datasets/              ← eval JSONL files (source-controlled)
│
├── training/
│   ├── validate_dataset.py    ← validates curated.jsonl format
│   ├── qlora_config_template.yaml
│   └── WHEN_TO_TUNE.md
│
└── data/
    ├── model_registry.json    ← source-controlled; 4 tiers; n_ctx: 4096/8192/16384/32768
    ├── active_model.json      ← written at runtime (gitignored)
    ├── models/                ← gitignored (.gguf files)
    ├── hf_models/             ← gitignored (HuggingFace weights for LoRA training)
    ├── adapters/              ← gitignored (trained LoRA adapters)
    ├── logs/
    │   ├── traces/            ← gitignored (JSONL trace logs, one per day, configurable rotation)
    │   ├── archive/           ← gitignored (gzip+Fernet-encrypted .jsonl.enc archives)
    │   └── raw/               ← gitignored (.tokens raw archive per generation)
    │  
    ├── sessions/              ← gitignored (saved conversation JSON)
    ├── training/              ← gitignored (curated.jsonl, export files)
    └── vector_db/             ← gitignored (index.faiss, meta.db)
│
└── vscode-extension/          ← VS Code/Code OSS editor extension
    ├── package.json           ← Extension configuration and commands registry
    ├── extension.js           ← Extension host entry point (commands, workspaces, diffs)
    ├── src/
    │   └── sidebarProvider.js ← Webview container (HTML generation, socket lifecycle, postMessage proxy)
    └── media/
        ├── karl.js            ← Client event handlers and controller logic
        ├── karl_render.js     ← Stream renderer (Token DOM re-use, throttled requestAnimationFrame scrolling)
        ├── karl_socket.js     ← WebSocket manager (Heartbeat timers, direct/host-relay handshakes)
        ├── karl_state.js      ← State persistence & focus redirection
        ├── themes.js          ← Custom styling parameters
        └── karl.css           ← Obsidian-core styling rules
```
