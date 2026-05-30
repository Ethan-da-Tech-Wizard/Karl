# AGENTS.md — Handoff Document for AI Agents

> **Written for AI coding agents. Read this before touching any code.**
> This file describes the exact current state of the repo — what is done,
> what is incomplete, what is broken, and what must be built next.
> Every claim here is accurate as of the last commit on `claude/hopeful-brahmagupta-dIo49`.

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

Work proceeds in strict phase order. Do not start Phase N+1 until Phase N is fully committed.

### Phase 1 — Wire It Together (make existing code correct)
1. Fix `llm_thread.py` trace_logger call: pass `model_name`, `adapter_name`, `workflow`, `template`
2. Fix `agentic_thread.py` same; also fix synthetic `rag_context`
3. Fix context budgeting: `ModelLoader` reads `n_ctx` from `model_registry.json` at load time; both threads read `n_ctx` from `ModelLoader` instead of hardcoding 4096
4. Fix `memory_manager.save_session()`: strip `<think>...</think>` blocks before saving
5. Fix eval harness: add `ModelLoader.is_loaded()` guard at top of `run()` and implement `progress_cb` call inside the case loop
6. Add params drawer to WorkbenchWorkspace: collapsible widget above input bar exposing temperature, top-p, max-tokens

### Phase 2 — Complete the Data Pipeline
1. Add `rag_threshold` and `rag_top_k` to `AppState`; KB workspace writes them, Workbench reads them
2. Add thumbs-down button to Workbench feedback row; wire to `curator.save_example(source="thumbs_down")`
3. Connect `MemoryManager` to Workbench: sessions list panel, save on new session, load on click
4. Update `feedback` field in trace log retroactively when user rates a generation
5. `training_curator.export_unsloth()`: normalise return to path-only string

### Phase 3 — Finish the Workspaces
1. KB workspace: add chunk_size and overlap spinboxes before ingest; pass to `ingest_file()`
2. Prompt Lab: after both A/B runs complete, render a character-level diff; add save/load named pairs
3. Training Studio: detect `data/hf_models/` for HF weights; if present, run `SFTTrainer` via peft+trl in a `QThread`, stream loss to log view
4. Eval Suite: implement `progress_cb` in `harness.run()`, connect to progress bar
5. System Config: read `model_registry.json`, show tier table (name, RAM req, context), download button per tier

### Phase 4 — The Four Planned Milestones
1. **Prompt diff tool**: character-level diff rendered inline in Prompt Lab after both outputs complete
2. **Session branching**: "branch from here" on any Workbench message; fork `chat_history` at that index into a new named session
3. **DPO export completion**: `training_curator` produces proper chosen/rejected pairs; Unsloth-compatible DPO JSONL
4. **Tokenizer visualization**: call `llm.tokenize()` on any text; render tokens as colored spans

### Phase 5 — Docs, Tests, Accuracy
1. Rewrite `README.md` for Arch Linux (remove all PowerShell references)
2. Rewrite all 7 `docs/` files to match current architecture
3. Update this file (`AGENTS.md`) after each phase
4. Write unit tests: `tests/test_cognitive_parser.py`, `tests/test_trace_logger.py`, `tests/test_training_curator.py`
5. Fix `smoke_test.py` and `engine_test.py` hardcoded model paths

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
