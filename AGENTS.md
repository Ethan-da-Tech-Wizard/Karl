# AGENTS.md — Handoff Document for AI Agents

> **Written for AI coding agents. Read this before touching any code.**
> This file describes the current state of the repo — what is done,
> what is incomplete, what is broken, and what must be built next.
> The "Completion Plan" below records the original Phase 1–5 build (all
> complete). Everything the project grew *after* that — the vision
> pipeline, the multi-agent swarm engine, the WebSocket editor/remote
> bridge, the VS Code and Neovim clients, k8s/Helm/Docker deployment, and
> a full security-hardening pass — is real, shipped, and summarized in the
> sections below, but is documented in depth in `docs/*.md` and
> `docs/audits/` rather than re-derived here. **If you find a claim in this
> file that doesn't match the code, trust the code and fix this file.**

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

The sidebar/stack above is the whole visible app, but it is not the whole
codebase. Several subsystems live outside the stack and are driven by
their own workspace, by the WebSocket bridge, or by CLI scripts:

- **Vision pipeline** (`app/vision/`) — OCR, image preprocessing, and a
  vision-model loader consumed by `VisionWorkbench` (stack index 3).
- **Swarm engine** (`app/engine/swarm_agents.py`, `swarm_orchestrator.py`,
  `swarm_judge.py`, `swarm_specialists.py`, `swarm_memory.py`,
  `task_supervisor.py`) — the Architect/Coder/Tester multi-agent pipeline
  behind SwarmStudioWorkspace. See `docs/05_multi_agent_swarm.md`.
- **Editor/remote bridge** (`app/engine/websocket_server.py`, ~2.5k lines)
  — a token-scoped, RBAC-gated WSS JSON-RPC server that the VS Code
  extension and Neovim client connect to as remote UIs onto the same
  running app. See "Editor Extension Integration" below and
  `docs/08_vscode_extension.md`.
- **AI Lab** (`app/ui/workspaces/ai_lab.py`, ~800 lines, has its own test
  file) is fully built but **deliberately not wired into the sidebar** —
  a past audit found the "AI Lab" button actually opened Training Studio
  and relabeled the button rather than silently swap workspaces; adding
  AI Lab as an 11th sidebar slot is a product decision, not a bug fix.
  See `docs/audits/repo_audit_findings_2026-07.md` item 5.
- **Flywheel automation** (`flywheel_runner.py`, `data/flywheel/*.py`) —
  a sandboxed background loop distinct from `FlywheelStudioWorkspace`
  (which is the UI for viewing its telemetry).

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

Karl is equipped with a native VS Code/Code OSS editor extension (`oss/vss_extension/`) that acts as a client to the running Karl PyQt6 desktop application over the WebSocket bridge (`app/engine/websocket_server.py`). A Neovim client (`neovim/karl.lua`) speaks the same bridge protocol for terminal-editor users. Full protocol reference: `docs/08_vscode_extension.md`.

* **Architecture**: The extension is a Webview panel that executes HTML5/JavaScript UI logic, proxying RPC calls to Karl's WebSocket server over local secure ports (WSS, token-authenticated — see `data/bridge_token.json`, gitignored, generated at runtime).
* **Message Protocol (`postMessage`)**: The Webview and VS Code host communicate via JSON messages. The host forwards connections and editor status telemetry (`cockpit_state_update`) to the Webview and processes workspace file writes (`queue_file_edit`) proposed by agents — routed through `oss/vss_extension/src/fileOps.js` (file I/O) and `gitOps.js` (diff/git actions) into real VS Code APIs (`vscode.workspace.applyEdit` / diff views), not just displayed as chat text.
* **Performance Rendering**: To prevent DOM fragmentation, tokens are appended directly to existing `.token-appear` nodes. Scroll recalculations are throttled using `requestAnimationFrame` to avoid layout reflow thrashing.
* **Focus Management**: Switching workspaces within the extension automatically focuses the primary inputs (`chatInput`, `objective`, or `kbQuery`) to keep the user's hands on the keyboard.
* **Security**: symlink-safe path checks, an allowlisted model/adapter-path validator, and a random (not timestamp-derived) CSP nonce were added in the security pass — see `docs/audits/architecture_walkthrough_2026-07.md`.

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
| Vision pipeline — OCR, preprocessing, vision model loader | `app/vision/` |
| Swarm engine — Architect/Coder/Tester orchestration, judge, specialists, cross-run memory | `app/engine/swarm_agents.py`, `swarm_orchestrator.py`, `swarm_judge.py`, `swarm_specialists.py`, `swarm_memory.py` |
| WebSocket editor/remote bridge — WSS, token auth, per-method RBAC scopes | `app/engine/websocket_server.py` |
| VS Code extension — chat panel, KB/eval/ai-lab views, real file writes via `fileOps.js`/`gitOps.js` | `oss/vss_extension/` |
| Neovim client (same bridge protocol) | `neovim/karl.lua` |
| Codex reference library (scraped per-topic docs) backing DocsWorkspace | `data/codex_library/`, `app/ui/workspaces/docs_data.py` |
| Agent profile / persona editor workspace | `app/ui/workspaces/agent_profile_studio.py` |

### 🔧 Built But Not Wired Into the Sidebar (by design)

| Component | File(s) | Why it's not in the stack |
|-----------|---------|----------------------------|
| AI Lab workspace | `app/ui/workspaces/ai_lab.py` | Fully built, has its own test file, but adding an 11th sidebar slot is a product decision that hasn't been made — see `docs/audits/repo_audit_findings_2026-07.md` item 5. |

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
> **All phases below are complete.** The work that followed Phase 5 — the vision
> pipeline, swarm engine expansion, WebSocket bridge, VS Code/Neovim clients,
> deployment manifests, and a full audit-driven hardening pass — isn't tracked as
> numbered phases; see `docs/audits/repo_audit_findings_2026-07.md` and
> `docs/audits/architecture_walkthrough_2026-07.md` for that history.


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

8. **`Karl-main/` was removed** (an untracked, empty leftover directory tree with the
   same name resurfaced at one point and was deleted again during the 2026-09 demo
   cleanup pass — see `docs/audits/`). It was a stale snapshot of the original codebase.
   All active work is in the root. Do not re-create it.

11. **The WebSocket bridge (`app/engine/websocket_server.py`) is a real remote-control
    surface**, not just a chat relay — it's what the VS Code extension and Neovim client
    talk to. Any RPC method that reads/writes paths, sets the active model/adapter, or
    shells out (e.g. `start_auto_train`) must go through the existing path-safety and
    allowlist helpers (`_is_safe_path`, `_collect_kb_files`, the model/adapter basename
    checks) — do not add a new file/subprocess-touching RPC method without them. Full
    threat model and fixes: `docs/audits/architecture_walkthrough_2026-07.md`.

12. **`k8s/`, `helm/`, `Dockerfile`, `docker-compose.yml` deploy Karl's WebSocket bridge
    as a networked service**, which is a different trust model than the offline desktop
    app described above — `_start_server` in `websocket_server.py` requires a real TLS
    cert and fails closed (refuses to bind) for any non-loopback `KARL_WS_HOST`, it does
    not fall back to plaintext. Something has to actually provision `data/ssl/localhost.{crt,key}`
    for that non-loopback case, or the container crash-loops on boot (`main.py`'s headless
    entrypoint correctly exits 1 when the bind fails). k8s/Helm do this via a cert-manager
    `Certificate` (`k8s/certificate.yaml` / `helm/karl/templates/certificate.yaml`, reusing
    the `internal-ca` issuer the ingress already references); plain Docker/docker-compose
    do it via `docker-entrypoint.sh` generating a self-signed cert on first boot. If you
    touch these manifests, keep the cert-provisioning path intact — don't just set
    `KARL_WS_HOST=0.0.0.0` without one of the two provisioning mechanisms above.

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

This is a curated map of what matters, not an exhaustive listing — the repo has
~550 tracked files. Run `git ls-files` for the literal current list; trust that
over this tree if they disagree.

```
Karl/
├── AGENTS.md                  ← YOU ARE HERE
├── README.md                  ← documentation reference
├── main.py                    ← entry point; sets env vars, loads stylesheet, launches MainWindow
├── engine_test.py             ← headless inference test
├── smoke_test.py              ← template/workflow smoke tests
├── raw_test.py                ← raw token streaming test
├── flywheel_runner.py         ← background sandboxed self-improvement loop (distinct from FlywheelStudioWorkspace UI)
├── auto_train.py              ← CLI entry for the LoRA/QLoRA training thread, also invoked by the WS bridge
├── download_test_model.py     ← downloads deepseek-r1-1.5b.gguf Q4_K_M
├── download_all_models.py     ← downloads every tier in data/model_registry.json
├── setup_karl.py, karl.sh, setup_gpu.sh ← bootstrap scripts (venv, CMAKE flags, GPU/CUDA setup)
├── requirements.txt           ← pip deps; peft/trl/transformers/datasets are optional (Training Studio)
│
├── core/                      ← HACKABLE LAYER — hot-reloaded on every generation
│   ├── interaction_loop.py    ← build_prompt(system, history) -> str
│   ├── prompt_templates.py    ← named templates; get_template(name, **kwargs) -> str
│   ├── prompt_optimizer.py    ← prompt-compression / "machine-speak" trace helpers
│   ├── workflows.py           ← 4 workflow modes (general_chat, document_extractor, grounded_answer, code_review)
│   ├── cognitive_parser.py    ← parse_thought_stream(raw) -> (thought, response); state machine
│   ├── agentic_loop.py        ← should_continue() + build_next_prompt(); MAX_ITERATIONS=20
│   ├── hardware_scout.py      ← get_hardware_profile() -> {ram_gb, vram_gb, storage_gb}
│   ├── security.py            ← shared path/input validation helpers (also used by the WS bridge)
│   └── default_prompts.py     ← built-in system prompt presets
│
├── app/
│   ├── state.py               ← AppState: shared state passed to all workspaces
│   ├── engine/                ← ~30 files: model lifecycle, threads, swarm engine, bridge
│   │   ├── model_loader.py    ← thread-safe singleton; registry n_ctx; GPU fallback; circuit breaker
│   │   ├── llm_thread.py / agentic_thread.py ← QThread generation workers, streaming parser
│   │   ├── swarm_agents.py, swarm_orchestrator.py, swarm_judge.py, swarm_specialists.py,
│   │   │   swarm_memory.py, task_supervisor.py ← Architect/Coder/Tester multi-agent pipeline
│   │   ├── websocket_server.py ← secure JSON-RPC 2.0 WSS bridge; token scopes; /metrics; ~2.5k lines
│   │   ├── tool_executor.py, mcp_client.py, remote_rpc_client.py ← tool-call execution + MCP integration
│   │   ├── agent_memory.py    ← per-workspace codebase memory index for swarm agents
│   │   ├── config_store.py    ← atomic data/*.json config I/O and registry cache
│   │   └── event_broker.py    ← thread-safe in-process pub/sub telemetry bus
│   ├── repository/
│   │   └── session_repository.py ← file/DB-backed session persistence (distinct from MemoryManager)
│   ├── vision/                 ← OCR, image preprocessing, vision model loader/analyzer for VisionWorkbench
│   ├── ui/
│   │   ├── main_window.py     ← sidebar + stack + status bar wiring
│   │   ├── sidebar.py         ← 10-button accessible nav; workspace_changed(int) signal
│   │   ├── themes.py          ← THEMES palettes; get_theme_stylesheet(state); MONO font stack
│   │   ├── widgets/            ← status_bar, command_palette, glow_panel, toast, shortcuts_overlay, tracing_panel, etc.
│   │   └── workspaces/
│   │       ├── workbench/        ← Workbench package; params, sessions, branching, feedback
│   │       ├── prompt_lab.py     ← Prompt Lab; A/B streams, saved pairs, diff, tokenizer
│   │       ├── knowledge_base.py ← chunk size/overlap controls; threshold wired to AppState
│   │       ├── vision_workbench.py
│   │       ├── training_studio/  ← Training Studio package; training requires HF weights
│   │       ├── eval_suite.py
│   │       ├── swarm_studio.py   ← task graph, file proposals, verification traces
│   │       ├── system_config/    ← model registry, quantization, MCP, theme, observability, hardware
│   │       ├── docs.py, docs_data.py ← Codex reference-library browser + its scraped content index
│   │       ├── flywheel_studio.py ← telemetry UI for flywheel_runner.py
│   │       ├── agent_profile_studio.py ← persona/agent-profile editor
│   │       └── ai_lab.py          ← built, tested, NOT wired into the sidebar (see above)
│   └── utils/                  ← ~30 files: rag_pipeline, memory_manager, trace_logger, training_curator,
│                                  session_tree, dataset_merger, db_pool, keychain_manager, correlation_logger,
│                                  swarm_replay, swarm_agent_profiles, topic_graph, codebase_search,
│                                  convert_lora_to_gguf.py (+ conversion/ — vendored per-architecture
│                                  GGUF converters it imports), and more
│
├── eval/
│   ├── harness.py, graders.py, run_eval.py, benchmark_rag.py, perplexity_bench.py
│   └── datasets/               ← eval JSONL files (source-controlled)
│
├── training/                   ← validate_dataset.py, qlora_config_template.yaml, WHEN_TO_TUNE.md
├── tools/                      ← operator/dataset CLI scripts: curate_code_datasets.py, decrypt_logs.py,
│                                  generate_*_sft_dataset.py, scrape_library_docs.py, evaluate_adapters.py,
│                                  setup_speculative_decoding.py, auto_train_lora.py
│
├── tests/                      ← ~80 pytest files covering nearly every module above; run `pytest` from repo root
│
├── oss/vss_extension/          ← VS Code/Code OSS editor extension
│   ├── package.json           ← Extension configuration and commands registry
│   ├── extension.js           ← Extension host entry point (commands, workspaces, diffs)
│   ├── src/
│   │   ├── sidebarProvider.js ← Webview container (HTML generation, socket lifecycle, postMessage proxy)
│   │   ├── commands.js        ← registered VS Code command palette entries
│   │   ├── fileOps.js         ← real file reads/writes into the VS Code workspace
│   │   └── gitOps.js          ← diff views / git actions for agent-proposed edits
│   └── media/                 ← karl.js, karl_render.js, karl_socket.js, karl_state.js, themes.js, karl.css
├── neovim/karl.lua             ← Neovim client speaking the same WebSocket bridge protocol
│
├── k8s/, helm/karl/, Dockerfile, docker-compose.yml
│                                ← deploy the WebSocket bridge as a networked service; see gotcha #12 above
│                                  before touching — different trust model than the offline desktop app
│
├── docs/                       ← 01–10 numbered reference docs + audits/ (dated hardening/audit history)
│
└── data/
    ├── model_registry.json, vision_model_registry.json ← source-controlled model tiers
    ├── agent_profiles.json, feature_flags.json          ← source-controlled defaults
    ├── codex_library/                                    ← source-controlled scraped reference docs (DocsWorkspace)
    ├── flywheel/*.py                                     ← flywheel_runner.py sandbox/generator/curator modules
    ├── active_model.json, ui_config.json, mcp_config.json, agent_memory*.json ← runtime state (gitignored)
    ├── bridge_token.json, ssl/                            ← runtime secrets, regenerated on launch (gitignored)
    ├── prompt_pairs/, eval_last.json, quantization_comparison.json,
    │   rag_benchmark_results.json                         ← personal run output (gitignored, not source)
    ├── models/, hf_models/, adapters/                     ← gitignored (large binaries / weights / trained adapters)
    ├── logs/, sessions/, training/, vector_db/, swarm_memory/ ← gitignored (user/runtime data)
```
