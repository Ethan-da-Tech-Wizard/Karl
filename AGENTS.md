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
│   ├── [0] WorkbenchWorkspace     app/ui/workspaces/workbench.py
│   ├── [1] PromptLabWorkspace     app/ui/workspaces/prompt_lab.py
│   ├── [2] KnowledgeBaseWorkspace app/ui/workspaces/knowledge_base.py
│   ├── [3] TrainingStudioWorkspace app/ui/workspaces/training_studio.py
│   ├── [4] EvalSuiteWorkspace     app/ui/workspaces/eval_suite.py
│   └── [5] SystemConfigWorkspace  app/ui/workspaces/system_config.py
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
- One dark theme (no theme switcher — Karl is a precision tool, not a toy)
- `PALETTE` dict: 20 named color tokens
- `MONO` string: JetBrains Mono → Fira Code → Cascadia Code → Consolas → Courier New
- `stylesheet(accent="#00C2FF") -> str` — call once, pass to `QApplication.setStyleSheet()`
- Object names (`#sidebar`, `#panel`, `#btn-primary`, etc.) are the hook points in QSS

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

### Threading Model

- `LLMThread(QThread)` — single-shot generation. `app/engine/llm_thread.py`
- `AgenticThread(QThread)` — autonomous multi-iteration loop. `app/engine/agentic_thread.py`
- Both emit: `new_thought_token(str)`, `new_chat_token(str)`, `new_raw_token(str)`
- `LLMThread` additionally emits: `generation_finished(thought, response, truncated, ended_in_thought)`
- `AgenticThread` additionally emits: `iteration_finished(index, thought, response)`, `loop_finished(total)`
- Both emit: `error_occurred(str)`
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
ModelLoader.get_instance(model_path=None) -> Llama
ModelLoader.reset_instance()              # forces reload on next call
ModelLoader.model_name() -> str           # basename of loaded GGUF
ModelLoader.is_loaded()  -> bool
```

- Protected by `threading.Lock()` — safe to call from any thread
- Reads `data/active_model.json` at first call to determine which GGUF to load
- Falls back to `deepseek-r1-1.5b.gguf` if the specified file is missing
- Currently hardcodes `n_ctx=4096` — **this is a known gap** (see below)

### The Trace Logger

`app/utils/trace_logger.py` writes JSONL to `data/logs/traces/trace_YYYY-MM-DD.jsonl`.
Rotates at 50 MB. Each entry has this schema:

```json
{
  "id": "uuid4",
  "session_id": "uuid4",
  "timestamp": "ISO8601",
  "timing": { "total_seconds": 0.0 },
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
  "corrected_response": null
}
```

This schema is the Unsloth SFT/DPO source. `feedback` + `corrected_response` drive the
training curator export.

### The RAG Pipeline

`app/utils/rag_pipeline.py` — persistent FAISS index.

- Embedding model: `all-MiniLM-L6-v2` (sentence-transformers)
- Index persists to `data/vector_db/index.faiss` + `data/vector_db/metadata.json`
- `ingest_file(path)` — extract text (PDF/DOCX/TXT/MD/PY/CSV) → chunk → embed → add
- `retrieve(query, top_k=3, source_filter=None) -> list[str]`
- `retrieve_with_metadata(query, top_k, ...) -> list[dict]` — includes distance scores
- `eval_retrieval(query, expected_ids, top_k) -> dict` — hit@1, hit@3, hit@k, MRR
- **Gap:** no distance threshold filtering in `retrieve()` — all top-k are returned
  regardless of relevance score

### The Training Curator

`app/utils/training_curator.py` — captures training examples.

- Saves to `data/training/curated.jsonl`
- `save_example(prompt, response, source)` — source = `"thumbs_up"` or `"corrected"`
- `export_unsloth(output_path) -> (str, int)` — returns (path, count)
- Unsloth format: `{ "instruction": ..., "input": "", "output": ..., "source": ..., "timestamp": ... }`

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
| WorkbenchWorkspace — chat, streaming, RAG toggle, loop toggle, Ctrl+Enter, feedback | `app/ui/workspaces/workbench.py` |
| KnowledgeBaseWorkspace — ingest, source list, chunk inspector, search tester | `app/ui/workspaces/knowledge_base.py` |
| PromptLabWorkspace — A/B side-by-side streaming | `app/ui/workspaces/prompt_lab.py` |
| TrainingStudioWorkspace — dataset browser, SFT/DPO export UI, LoRA config UI | `app/ui/workspaces/training_studio.py` |
| EvalSuiteWorkspace — dataset picker, results tree | `app/ui/workspaces/eval_suite.py` |
| SystemConfigWorkspace — model loader, defaults, identity, hardware | `app/ui/workspaces/system_config.py` |
| ModelLoader thread-safety | `app/engine/model_loader.py` |
| cognitive_parser state machine | `core/cognitive_parser.py` |
| Trace logger (new schema + rotation) | `app/utils/trace_logger.py` |
| LLMThread streaming + auto-continuation | `app/engine/llm_thread.py` |
| AgenticThread loop + hot-reload | `app/engine/agentic_thread.py` |
| RAG pipeline (persistent FAISS) | `app/utils/rag_pipeline.py` |
| Training curator (Unsloth SFT export) | `app/utils/training_curator.py` |
| Eval harness + 5 graders | `eval/harness.py`, `eval/graders.py` |
| Hardware scout | `core/hardware_scout.py` |

### ⚠️ Implemented but Broken / Incomplete

| Issue | File | What's Wrong |
|-------|------|--------------|
| Trace logger calls missing fields | `app/engine/llm_thread.py` line 176 | `model_name`, `adapter_name`, `workflow`, `template`, `feedback` not passed — all logs say `"model": "unknown"` |
| Same issue in agentic loop | `app/engine/agentic_thread.py` line 204 | Same missing fields; also passes synthetic `rag_context=[f"agentic_iteration_{n}"]` |
| Context budget ignores model registry | `app/engine/llm_thread.py` line 11, `app/engine/agentic_thread.py` line 15, `app/engine/model_loader.py` line 39 | `_CONTEXT_BUDGET = 4096` and `n_ctx=4096` are hardcoded; `data/model_registry.json` defines 4 tiers with contexts 4096→32768 but is never read |
| `<think>` blocks saved in sessions | `app/utils/memory_manager.py` | `save_session()` dumps raw `chat_history` including think tokens; on reload, model re-reasons already-completed thoughts |
| RAG threshold not wired to Workbench | `app/ui/workspaces/knowledge_base.py` threshold control, `app/ui/workspaces/workbench.py` | The threshold spinbox in KB workspace sets nothing on `AppState`; `retrieve()` in Workbench always uses no threshold |
| Workbench has no params drawer | `app/ui/workspaces/workbench.py` | temperature / top-p / max-tokens only accessible via System Config; no per-session override in Workbench UI |
| Session save/load not connected | `app/ui/workspaces/workbench.py` | `MemoryManager` exists in `AppState` but Workbench never calls `save_session()` or `load_session()` |
| Eval harness no model guard | `eval/harness.py` | `run()` proceeds unconditionally; `FileNotFoundError` surfaces inside the case loop instead of at entry |
| Eval progress callback not implemented | `eval/harness.py` | `progress_cb` parameter exists in signature but `harness.run()` doesn't call it |
| LoRA training stubbed | `app/ui/workspaces/training_studio.py` | Train button logs a message explaining HF model path requirements; no training executes |
| Prompt Lab no diff view | `app/ui/workspaces/prompt_lab.py` | A/B streaming works; diff render after both complete is not implemented |
| System Config no model registry browser | `app/ui/workspaces/system_config.py` | Shows files in `data/models/` but doesn't read `data/model_registry.json` for tier info or download |
| KB workspace chunk controls absent | `app/ui/workspaces/knowledge_base.py` | `ingest_file()` always uses default chunk_size=200, overlap=50 |
| DPO export needs thumbs-down | `app/ui/workspaces/workbench.py` | No thumbs-down button; DPO export in Training Studio attempts pairing but has no rejected examples to pair |
| `training_curator.export_unsloth()` return | `app/utils/training_curator.py` | Returns `(path, count)` tuple; Training Studio only assigns to `out_path`, discards count silently |

### ❌ Not Yet Built

| Feature | Target Location | Phase |
|---------|----------------|-------|
| Model-aware context budgeting | `model_loader.py`, both threads | Phase 1 |
| `<think>` stripping in session save | `memory_manager.py` | Phase 1 |
| Workbench params drawer | `workbench.py` | Phase 1 |
| Session save/load UI | `workbench.py` | Phase 2 |
| Thumbs-down + DPO pairing | `workbench.py`, `training_curator.py` | Phase 2 |
| RAG threshold wired to AppState | `knowledge_base.py`, `workbench.py`, `state.py` | Phase 2 |
| Eval harness model guard + progress | `eval/harness.py` | Phase 2 |
| KB chunk size/overlap controls | `knowledge_base.py` | Phase 3 |
| Prompt diff view | `prompt_lab.py` | Phase 3 |
| Prompt pair save/load | `prompt_lab.py` | Phase 3 |
| LoRA/QLoRA actual training | `training_studio.py` | Phase 3 |
| Model registry browser + download | `system_config.py` | Phase 3 |
| Session branching | `workbench.py` | Phase 4 |
| Tokenizer visualization | `prompt_lab.py` or `workbench.py` | Phase 4 |
| DPO export complete | `training_studio.py`, `training_curator.py` | Phase 4 |
| README rewrite for Linux/Arch | `README.md` | Phase 5 |
| All 7 docs rewritten to match current arch | `docs/` | Phase 5 |
| Unit tests for parser, logger, curator | `tests/` (new) | Phase 5 |
| `smoke_test.py`, `engine_test.py` hardcoded paths fixed | root | Phase 5 |

---

## Completion Plan

Work proceeds in strict phase order.
**Do not start Phase N+1 until Phase N is fully committed and pushed.**

The plan is intentionally broken into sub-phases where the work is complex,
architecturally significant, or high-risk. Simple phases (1, 2, 5) are done in
one commit. Complex phases (3, 4) are split into isolated sub-commits so that a
failure in one sub-phase cannot corrupt the others.

---

> **Progress Legend:** ✅ = completed · 🔨 = in progress (← YOU ARE HERE) · ⬚ = not started

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

### 🔨 Phase 2.5a — UX Polish: Workbench  ← YOU ARE HERE
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

### ⬚ Phase 2.5b — UX Polish: Knowledge Base + Prompt Lab
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

### ⬚ Phase 2.5c — UX Polish: Training Studio + Eval Suite
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

### ⬚ Phase 2.5d — System Config + Global Consistency Pass
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

### ⬚ Phase 3.1 — Small Workspace Fixes
**One commit. Two mechanical additions. Low risk.**

1. KB workspace: add chunk_size and overlap spinboxes before ingest button;
   pass values to `ingest_file(filepath, chunk_size, overlap)`
2. Eval Suite: connect EvalSuiteWorkspace progress bar to `progress_cb` now
   implemented in `harness.run()`

---

### ⬚ Phase 3.2 — Prompt Lab Completion
**One commit. Self-contained UI feature. Medium risk.**

1. After both A/B runs complete, render character-level diff of the two outputs
   (use `difflib.ndiff` or similar; color-code additions/deletions inline)
2. Save/load named prompt pairs to `data/prompt_pairs/<name>.json`;
   add a pairs list in the Prompt Lab left panel

---

### ⬚ Phase 3.3 — LoRA / QLoRA Training Thread
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

### ⬚ Phase 3.4 — System Config Model Registry Browser
**One commit. Self-contained workspace enhancement. Low risk.**

1. Read `data/model_registry.json`; render tier table (name, RAM req, n_ctx, file size)
2. Download button per tier: `requests` stream to `data/models/` with progress bar
3. On download complete, set as active model via `ModelLoader.reset_instance()` +
   write `data/active_model.json`

---

### ⬚ Phase 4.1 — Tokenizer Visualization
**One commit. Self-contained display feature. Low risk.**

1. Add tokenizer panel to Prompt Lab (or collapsible drawer in Workbench)
2. Call `ModelLoader.get_instance().tokenize(text.encode())` on input text
3. Render tokens as colored inline spans with token IDs on hover
4. Color tokens by rough type: punctuation, word-start, subword continuation, special

---

### ⬚ Phase 4.2 — DPO Export Completion
**One commit. Depends on Phase 2.2 (thumbs-down) being complete.**

1. `training_curator.export_dpo(path)`: pair thumbs_up (chosen) with thumbs_down
   (rejected) on same prompt; write `{prompt, chosen, rejected}` JSONL
2. Training Studio Export tab: wire DPO button to new method
3. Output must be loadable by Unsloth without modification — verify against schema

---

### ⬚ Phase 4.3 — Session Branching
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

### ⬚ Phase 5 — Documentation, Tests, Accuracy
**One commit. No code risk. Do last.**

1. Rewrite `README.md` for Linux/Arch — no PowerShell, no Windows paths
2. Rewrite `docs/01–03` and `docs/06` to match current architecture
3. `docs/04_architecture.md`, `docs/05_scope_and_milestones.md`,
   `docs/07_risk_register.md` — already updated; verify they still match after Phase 4
4. Update this file (`AGENTS.md`) to reflect completed state
5. Create `tests/` directory; write:
   - `tests/test_cognitive_parser.py` — all 5 state machine cases
   - `tests/test_trace_logger.py` — schema fields, rotation trigger
   - `tests/test_training_curator.py` — save, export, DPO pairing
6. Fix `smoke_test.py` and `engine_test.py`: replace hardcoded model paths with
   `ModelLoader.get_instance()` / discovery from `data/models/`

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

8. **`Karl-main/` is a stale archive copy.** Do not modify it. It exists only as a
   reference snapshot of the original codebase. All active work is in the root.

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
│   │   ├── model_loader.py    ← thread-safe singleton; _lock; model_name(); is_loaded()
│   │   ├── llm_thread.py      ← LLMThread(QThread); ⚠️ trace_logger call missing fields
│   │   └── agentic_thread.py  ← AgenticThread(QThread); ⚠️ same
│   ├── ui/
│   │   ├── main_window.py     ← shell only: sidebar + stack + status bar
│   │   ├── sidebar.py         ← 6-button nav; workspace_changed(int) signal
│   │   ├── themes.py          ← stylesheet(accent) -> str; PALETTE dict; MONO font stack
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   └── status_bar.py  ← model name, state text, RAM; set_model/set_state/set_adapter
│   │   └── workspaces/
│   │       ├── __init__.py
│   │       ├── workbench.py      ← ⚠️ no params drawer; no session save/load; no thumbs-down
│   │       ├── prompt_lab.py     ← ⚠️ no diff view; no pair save/load
│   │       ├── knowledge_base.py ← ⚠️ no chunk controls; threshold not wired to AppState
│   │       ├── training_studio.py ← ⚠️ training stubbed; DPO has no rejected examples
│   │       ├── eval_suite.py     ← ⚠️ progress_cb not implemented in harness
│   │       └── system_config.py  ← ⚠️ no model registry browser
│   └── utils/
│       ├── rag_pipeline.py    ← persistent FAISS; ⚠️ no distance threshold in retrieve()
│       ├── memory_manager.py  ← ⚠️ saves <think> blocks in sessions
│       ├── trace_logger.py    ← new schema (id, session_id, feedback, model, adapter, rotation)
│       └── training_curator.py ← curated.jsonl; export_unsloth() returns (path, count) tuple
│
├── eval/
│   ├── harness.py             ← EvalHarness.run(); ⚠️ no model guard; ⚠️ progress_cb not called
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
    │   ├── traces/            ← gitignored (JSONL trace logs, one per day, rotates at 50 MB)
    │   └── raw/               ← gitignored (.tokens raw archive per generation)
    ├── sessions/              ← gitignored (saved conversation JSON)
    ├── training/              ← gitignored (curated.jsonl, export files)
    └── vector_db/             ← gitignored (index.faiss, metadata.json)
```
