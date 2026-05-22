# Karl — Scope Lock & Milestones

## Scope Lock Statement (v2 — All Milestones Complete)

Karl is a self-contained, offline LLM **Introspection Environment** focused on:
- Exposing the model's full internal reasoning trace in real time
- Giving the user direct, hot-reloadable control over the prompt pipeline
- Providing a direct path from experimentation to fine-tuning
- Zero network calls during inference

---

## Completed Milestones

### ✅ Milestone 1 — Headless Introspection Engine
**Files:** `engine_test.py`, `core/cognitive_parser.py`, `app/utils/trace_logger.py`

Proved the engine works and established the raw logging infrastructure.
- `engine_test.py` loads the model headlessly and runs a test generation
- `TraceLogger` writes structured JSONL traces to `data/logs/traces/`
- `cognitive_parser.py` batch-parses `<think>` blocks from raw output (used by eval harness)

---

### ✅ Milestone 2 — Dual-Pane Thought Stream UI
**Files:** `app/ui/main_window.py`, `app/engine/llm_thread.py`

Built the PyQt6 framework with live streaming to two separate panels.
- **Diagnostic Lane** — `<think>` tokens streamed in real time
- **Final Response** — cleaned answer rendered as it arrives
- Inline state machine in `LLMThread.run()` routes tokens to the correct panel
- Suffix guard prevents tag-split flushing errors

---

### ✅ Milestone 3 — Memory & Context Management
**Files:** `app/utils/memory_manager.py`, `MainWindow.force_thought()`

Session persistence and context window management.
- `MemoryManager` serialises/deserialises chat history as JSON
- **Force Thought** button injects a fake `<think>` block into the context
- `_trim_history()` prevents context overflow in both `LLMThread` and `AgenticThread`
- Always preserves the seed message (index 0)

---

### ✅ Milestone 4 — Universal RAG Pipeline
**Files:** `app/utils/rag_pipeline.py`

Local document ingestion and retrieval.
- Supported formats: PDF, DOCX, TXT, PY, MD, CSV
- 200-word chunks / 50-word overlap
- FAISS flat L2 index with `all-MiniLM-L6-v2` embeddings
- Persistent index saved to `data/vector_db/`
- Retrieved chunks logged explicitly in every trace

---

### ✅ Milestone 5 — Hackable Decoupling
**Files:** `core/interaction_loop.py`, `importlib.reload()` in both threads

The "edit without restarting" capability.
- All prompt construction logic lives in `core/interaction_loop.py`
- Both `LLMThread` and `AgenticThread` call `importlib.reload()` before every generation
- User edits the file → clicks Generate → new logic runs immediately

---

### ✅ Milestone 6 — Agentic Loop
**Files:** `core/agentic_loop.py`, `app/engine/agentic_thread.py`, UI controls

Autonomous multi-turn self-reflection.
- `AgenticThread` loops: generate → parse → check stop → inject → repeat
- `should_continue()` and `build_next_prompt()` in `core/agentic_loop.py` are hot-reloaded per iteration
- Hard cap: `MAX_ITERATIONS = 5` (user editable)
- **Run Agentic Loop** and **Stop** buttons in UI
- Stop signals: `[DONE]`, `[END]`, `[STOP]`, `FINAL ANSWER:`

---

### ✅ Milestone 7 — Raw Token Archive
**Files:** `new_raw_token` signal, `data/logs/raw/*.tokens`, Raw Token Archive panel

Pre-parser token visibility.
- Every token emitted via `new_raw_token` before the streaming parser sees it
- Each generation writes a micro-timestamped `.tokens` file
- Toggleable **Raw Token Archive** panel in the UI (hidden by default)
- Data persists even if generation is killed mid-stream

---

### ✅ Milestone 8 — Hardware Scout & Model Registry
**Files:** `core/hardware_scout.py`, `data/model_registry.json`, `app/engine/upgrade_manager.py`

Automatic hardware-tier detection and model upgrade suggestions.
- `get_hardware_profile()` reads RAM, VRAM, and available storage
- `check_for_upgrade()` compares profile to tier thresholds in `model_registry.json`
- Upgrade notification shown in right panel if a better tier is eligible

---

### ✅ Milestone 9 — Auto-Loop Mode
**Files:** `MainWindow.auto_loop_toggle`, `handle_generation_finished()`

Continuous agentic operation from a single prompt.
- **Auto-Loop** checkbox — when ON, `handle_generation_finished()` calls `start_agentic_loop()` automatically
- Send button label changes to **Send + Loop** as a visual reminder
- Stop via the **Stop** button or the stop condition in `core/agentic_loop.py`

---

### ✅ Milestone 10 — Self-Upgrade Git Push
**Files:** `app/engine/upgrade_manager.py`

Model upgrade with automatic git commit + push.
- `perform_upgrade()` downloads the new GGUF, calls `ModelLoader.reset_instance()`
- Updates `data/active_model.json`
- Commits the updated JSON and pushes to `origin/main`

---

### ✅ Milestone 11 — Training Data Curator
**Files:** `app/utils/training_curator.py`, rating buttons in UI

Rate-to-dataset pipeline.
- 👍 **Good** — saves positive (prompt, response) pair
- ✏️ **Fix** — opens correction dialog, saves corrected pair
- All data in `data/training/curated.jsonl`
- **Export for Unsloth** — writes Unsloth-formatted JSONL for QLoRA fine-tuning
- Stats displayed live in right panel

---

### ✅ Milestone 12 — Eval Harness
**Files:** `eval/harness.py`, `eval/graders.py`, `eval/run_eval.py`, `eval/benchmark_rag.py`

Dataset-driven automated evaluation.
- 5 graders: `keyword_hit`, `json_valid`, `groundedness`, `json_schema`, `regex_match`
- CLI: `python eval/run_eval.py --workflow grounded_answer --top_k 5`
- Retrieval benchmark: `python eval/benchmark_rag.py`

---

### ✅ Milestone 13 — Three Workflow Modes + Prompt Templates
**Files:** `core/prompt_templates.py`, `core/workflows.py`

Named, selectable operating modes.
- 4 workflows: General Chat, Document Extractor, Grounded Answer, Code Review
- 5 templates: `reasoning_minimal`, `gpt_structured`, `json_extractor`, `grounded_answer`, `code_review`
- Changing workflow auto-selects its default template and RAG top-k

---

### ✅ Milestone 14 — RAG Hardening
**Files:** `app/utils/rag_pipeline.py`

Production-grade RAG improvements.
- Persistent FAISS index across restarts
- File-level metadata attached to every chunk `{source_file, chunk_id, ingested_at}`
- Optional contextual chunk headers `[Source: file | Chunk N]`
- `source_filter` parameter on `retrieve()` to restrict by file
- Retrieval eval: `hit@1`, `hit@3`, `hit@k`, reciprocal rank

---

### ✅ Milestone 15 — Training Path Formalisation
**Files:** `training/validate_dataset.py`, `training/qlora_config_template.yaml`, `training/WHEN_TO_TUNE.md`

End-to-end fine-tuning guidance.
- `validate_dataset.py` — validates curated JSONL before training runs
- `qlora_config_template.yaml` — ready-to-use QLoRA config for Unsloth
- `WHEN_TO_TUNE.md` — decision guide for when fine-tuning is worthwhile vs. prompt engineering

---

## Planned Next Milestones

| # | Name | Description |
|---|---|---|
| 16 | Tokenizer Visualization | Display actual token IDs and per-token log-probabilities alongside the raw stream. Requires `logprobs=5` in the generation call. |
| 17 | Session Branching | Fork a session at any turn and explore alternate prompt paths in parallel. |
| 18 | Prompt Diff Tool | Side-by-side comparison of two trace logs. The `workflow` + `template` fields in every trace make this tractable. |
| 19 | DPO Export | Direct preference optimisation dataset format. Requires storing the original (rejected) response alongside the correction in `_rate_thumbs_down()`. |
