# Product Requirements Document (PRD) — Karl v2

## 1. Product Vision

**Karl** is a surgical instrument for Prompt Engineers. The philosophy:

> **UI for convenience. Code for control. Measurement for trust.**

Karl provides a polished PyQt6 GUI for interacting with a local model, but its defining characteristic is that every layer of the generation process is visible, modifiable, and measurable. It is not a chat app. It is a lab.

---

## 2. Target Persona

- **Role:** Prompt Engineer / AI Solutions Architect
- **Skills:** Python-proficient; understands tokenisation, embeddings, hyperparameters, fine-tuning
- **Needs:** Reproducible experiments, privacy, measurable output quality, direct inference control
- **Non-goals:** General public users; people who want a polished consumer chat experience

---

## 3. Strict Constraints

### 3.1 Network & Privacy Isolation
- **AC1:** The application MUST NOT initiate any outbound network requests
- **AC2:** All telemetry MUST be suppressed at process startup before any library imports (`HF_HUB_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY`, `HF_DATASETS_OFFLINE`, `TOKENIZERS_PARALLELISM`)
- **AC3:** Inference MUST run in-process via `llama-cpp-python` C-bindings — no localhost servers, no daemons

### 3.2 Introspection Engine
- **AC1:** The application MUST separate model reasoning (`<think>` blocks) from final output, streaming both to distinct UI panels in real time
- **AC2:** Every generation MUST be logged to `data/logs/traces/` as an immutable JSONL entry: timestamp, compiled prompt, hyperparameters, raw output, parsed thought, parsed response, RAG chunks, workflow, template
- **AC3:** The user MUST have a live visual pathway for the thought stream, distinct from the chat panel

### 3.3 Hackable Core
- **AC1:** All files in `core/` MUST be hot-reloaded via `importlib` on every generation — no restart required
- **AC2:** The application MUST catch all exceptions from `core/` and display them in the UI without crashing

### 3.4 Measurability
- **AC1:** An eval harness MUST score outputs against defined graders and return a structured report
- **AC2:** The harness MUST be runnable both headlessly (CLI) and from the UI
- **AC3:** Eval reports MUST persist to `eval/results/` and be browsable with pass-rate history

---

## 4. Feature Specifications

### 4.1 Workflow Engine
A **Workflow** combines a prompt template, RAG config, output schema, and eval grader into a named mode. Selecting a workflow syncs the system prompt, RAG top-k, and template selector automatically. Defined in `core/workflows.py`, hot-reloaded.

Built-in: `general_chat`, `document_extractor`, `grounded_answer`, `code_review`.

### 4.2 Prompt Template Registry
Named system prompts in `core/prompt_templates.py` with `{rag_context}`, `{schema}`, `{code}` placeholders filled at generation time. Hot-reloaded — edit and generate, no restart.

### 4.3 Eval Harness
- Dataset: JSONL, one case per line
- Graders: `exact_match`, `json_valid`, `keyword_hit`, `groundedness`, `not_in_context`
- Each grader returns `{passed: bool, score: float, detail: str}`
- CLI: `python eval/run_eval.py --dataset ... --workflow ...`
- UI: `EvalDashboardDialog` with live progress and history table
- Reports saved to `eval/results/` as timestamped JSONL

### 4.4 Session & Memory Management
- Save, load, list sessions as JSON in `data/sessions/`
- **Fork:** Clone to a new branch file — diverge without losing the original
- **Save Version:** Snapshot with a human-readable tag
- List sorted newest-first by mtime, alphabetical tiebreaker

### 4.5 RAG Pipeline
- Ingest: PDF, DOCX, TXT, PY, MD, CSV
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (local)
- Storage: FAISS `IndexFlatL2`, persisted to `data/vector_db/`
- Per-chunk metadata: `source_file`, `chunk_id`, `ingested_at`
- Optional contextual headers: `[Source: file | Chunk N]`
- Retrieval metrics: `eval_retrieval()` for Hit@k and MRR

### 4.6 Training Data Pipeline
- 👍 Thumbs-up → SFT example
- 👎 Correction → SFT example + DPO pair (original stored as rejected)
- Validation: `training/validate_dataset.py`
- Export SFT: Unsloth / HuggingFace ShareGPT format
- Export DPO: TRL DPOTrainer chosen/rejected format
- Config: `training/qlora_config_template.yaml`
- Decision guide: `training/WHEN_TO_TUNE.md`

### 4.7 Prompt Diff Viewer
- Loads all JSONL traces from `data/logs/traces/`
- Side-by-side two-panel comparison
- Line-level diff highlights differing response lines in red in both panels

### 4.8 Logit Bias Editor
- UI text area: `token_string: ±float` one per line
- Karl tokenises each word via the loaded model at generation time
- Applied on every generation including auto-continued responses

### 4.9 Token Confidence Heatmap
- `logprobs=5` passed to llama-cpp-python on every generation
- `token_logprobs_ready` signal: `[(token_str, logprob), ...]`
- Confidence bar: average logprob, green/amber/red
- Heatmap panel: per-token colour, green→red (0 to −5)

### 4.10 Agentic Loop
- Auto-Loop, Run, Stop controls
- `core/agentic_loop.py` defines stop condition and next-prompt logic
- Hot-reloaded per iteration

### 4.11 Hardware-Aware Upgrade
- Detects RAM/VRAM at startup
- Offers one-click download and model switch if a better tier is available

---

## 5. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Startup time | < 5s excluding model load |
| UI thread blocking | Never — all inference on QThread |
| Context management | Sliding window with per-message character cap |
| Crash recovery | All `core/` exceptions caught and displayed; app continues |
| Telemetry | Zero — enforced via environment variables before any import |
