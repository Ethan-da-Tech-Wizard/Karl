# Karl — Scope and Milestone Tracker

## Scope Statement (v2 — Prompt Engineering Workbench)

Karl is a privacy-first, offline Prompt Engineering Workbench. It provides a PyQt6 GUI for iterating on LLM behaviour with full introspection, reproducible evaluation, and a structured path to fine-tuning. The inference engine runs in-process via llama-cpp-python. No network calls. No external servers.

---

## Milestone Tracker

### Phase 0 — Foundation

#### M1: Headless Introspection Engine ✅
**Goal:** Prove the engine works and build the logging infrastructure before any UI.
- `engine_test.py` — headless generation test
- `TraceLogger` — JSONL logging of prompt, hyperparams, raw output, thought, response
- `cognitive_parser.py` — `<think>` block extraction
- **Success:** Script generates text, splits reasoning from answer, writes structured log

#### M2: Dual-Pane Thought Stream UI ✅
**Goal:** PyQt6 framework with live thought/response routing.
- `main_window.py` with dark neutral theme and three-column layout
- `LLMThread` streaming to two panels simultaneously
- **Success:** User sees thought stream populate separately from the final answer in real time

#### M3: Memory and Context Management ✅
**Goal:** Session persistence and context window safety.
- JSON serialisation of chat history
- System Prompt text field
- `Force Thought` button — inject fake `<think>` blocks
- Sliding window context trimming
- **Success:** Sessions survive restart; context window never overflows

#### M4: Universal RAG Pipeline ✅
**Goal:** Local document ingestion and retrieval.
- `sentence-transformers` + `faiss-cpu` pipeline
- Ingest PDF, DOCX, TXT, PY, MD, CSV
- Retrieved chunks logged in every trace entry
- **Success:** Ingested document content appears in retrieved context during generation

#### M5: Hackable Core Decoupling ✅
**Goal:** Hot-reloadable interaction logic.
- `core/interaction_loop.py` as the primary edit surface
- `importlib.reload()` on every generation
- Graceful exception handling from user modifications
- **Success:** User edits `interaction_loop.py`, saves, clicks Generate — change applies immediately

#### M6: Agentic Loop ✅
**Goal:** Autonomous self-iterating generation.
- `core/agentic_loop.py` — hackable stop condition and next-prompt injection
- `AgenticThread` — loops generation, hot-reloads agentic core per iteration
- UI: Run / Stop controls with iteration counter
- **Success:** Karl iterates autonomously until stop condition is met

---

### Phase 1 — Workbench Infrastructure

#### M7: Raw Token Archive ✅
- Toggle panel showing raw token stream with microsecond timestamps
- Written to `data/logs/raw/` simultaneously with trace log

#### M8: Hardware-Aware Upgrade Manager ✅
- `hardware_scout.py` reads RAM and VRAM
- `data/model_registry.json` maps hardware tiers to model recommendations
- `UpgradeCheckThread` runs at startup; notification + one-click download if upgrade available

#### M9: Auto-Loop and Agentic Controls ✅
- `Auto-Loop` checkbox for continuous self-feeding generation
- Stop button halts at next iteration boundary
- Send button label reflects loop state

#### M10: Self-Upgrade via Model Registry ✅
- `UpgradeDownloadThread` streams download progress
- Model auto-registered on completion; restart prompt shown

#### M11: Training Data Curator ✅
- 👍 / 👎 rating buttons after each generation
- 👎 opens correction editor; corrected response saved as SFT example
- `data/training/curated.jsonl` — append-only JSONL
- Export to Unsloth/HuggingFace ShareGPT format
- Curator stats displayed in config panel

#### M12: Prompt Template Registry ✅
- `core/prompt_templates.py` — named templates with `{placeholder}` filling
- Built-in: `reasoning_minimal`, `gpt_structured`, `json_extractor`, `grounded_answer`, `code_review`
- Hot-reloaded; `get_template(name, **kwargs)` API
- Template selector in UI

#### M13: Workflow Engine ✅
- `core/workflows.py` — named modes linking template + RAG config + eval grader
- Built-in: `general_chat`, `document_extractor`, `grounded_answer`, `code_review`
- Workflow selector syncs template and RAG top-k automatically
- Workflow + template logged in every trace entry

#### M14: Eval Harness and Graders ✅
- `eval/graders.py` — pure scoring functions: `exact_match`, `json_valid`, `keyword_hit`, `groundedness`, `not_in_context`
- `eval/harness.py` — `EvalHarness.run()` against any JSONL dataset
- `eval/run_eval.py` — CLI with `--dry-run` support
- Seed datasets: `document_extractor`, `grounded_answer`, `code_review`
- `eval/benchmark_rag.py` — retrieval quality benchmark (Hit@k, MRR)

#### M15: Hardened RAG Pipeline ✅
- FAISS index persisted to `data/vector_db/` — survives restarts
- Per-chunk metadata: `source_file`, `chunk_id`, `ingested_at`
- Contextual chunk headers toggle: `[Source: file | Chunk N]`
- `eval_retrieval()` for Hit@k and MRR measurement
- Source filter on `retrieve()`

---

### Phase 2 — Measurement and Control

#### M16: Session Branching ✅
- `fork_session()` — clone to new branch file, switch immediately
- `save_version()` — named snapshot (e.g. `_v_v2-with-rag.json`)
- Session list sorted newest-first by mtime
- Fork/Version buttons in UI

#### M17: Prompt Diff Viewer ✅
- `DiffViewerDialog` — loads all `data/logs/traces/` JSONL entries
- Two-panel side-by-side: workflow, template, hyperparams, RAG chunks, thought, response
- Line-level diff highlighting: differing response lines coloured red in both panels

#### M18: Eval Results Dashboard ✅
- `EvalDashboardDialog` history panel: `QTableWidget` of all past reports
- Pass-rate colour coding: green ≥ 80%, amber ≥ 50%, red below
- Per-case breakdown on row click

#### M19: Live Eval Runner ✅
- `EvalRunThread` runs `EvalHarness` off the UI thread
- Dataset + workflow dropdowns, progress bar, live case-by-case status log
- Report auto-saved; history panel auto-refreshes on completion
- `📊 Eval` button in chat panel opens dashboard

#### M20: Logit Bias Editor ✅
- `QTextEdit` in config panel: `word: ±float` one per line
- `_parse_logit_bias()` tokenises via loaded model → `{token_id: float}`
- Passed as `logit_bias` kwarg to llama on every generation including continuations

#### M21: Token Confidence Heatmap ✅
- `logprobs=5` on every generation; `token_logprobs_ready` signal
- Confidence bar: average logprob with green/amber/red colour coding
- Heatmap panel: per-token HTML colour render (green→red, 0 to −5)
- Heatmap renders from cache when toggled on mid-session
