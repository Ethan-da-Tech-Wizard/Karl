# Product Requirements Document (PRD) — Karl v2

## 1. Product Vision & Philosophy

**Karl** is a surgical instrument for Prompt Engineers. It is not designed for the general
public — it is designed for professionals who need absolute control over the LLM generation
lifecycle.

> "UI for convenience, Code for control, Introspection for insight."

Karl provides a polished PyQt6 GUI for interacting with the model, but critically, it
completely exposes the model's internal monologue and gives the user direct access to the
prompt construction, parsing, and agentic loop logic via hot-reloadable Python scripts.

---

## 2. Target Persona

- **Role:** Prompt Engineer / AI Solutions Architect / AI Researcher
- **Skills:** Proficient in Python, understands tokenisation, embeddings, vector mathematics, and LLM hyperparameters
- **Needs:** Rapid iteration, absolute privacy, deterministic traceability, explicit pathways to manipulate model reasoning, and a direct path from experimentation to fine-tuning

---

## 3. Strict Constraints & Acceptance Criteria

### 3.1 Network & Privacy Isolation
- **AC1:** The inference engine runs in-process via `llama-cpp-python` C-bindings — zero localhost servers.
- **AC2:** No outbound network requests are made during inference. The only network calls allowed are: model download (manual, user-triggered) and the optional GitHub push on model upgrade.
- **AC3:** `HF_HUB_OFFLINE=1` can be set to silence the `sentence-transformers` HuggingFace token warning without affecting functionality.

### 3.2 The Introspection Engine
- **AC1:** The streaming parser intercepts `<think>` … `</think>` tokens in real time and routes them to the **Diagnostic Lane** panel, separate from the Final Response panel.
- **AC2:** Every generation writes an immutable JSONL trace to `data/logs/traces/trace_YYYY-MM-DD.jsonl` containing: timestamp, workflow, template, hyperparameters, compiled prompt, raw output, parsed thought, parsed response, latency, and RAG context used.
- **AC3:** Every generation also writes a timestamped `.tokens` raw archive file to `data/logs/raw/`.

### 3.3 The Hackable Core
- **AC1:** `core/interaction_loop.py` — prompt string builder. Hot-reloaded via `importlib.reload()` before every generation.
- **AC2:** `core/agentic_loop.py` — stop condition and next-prompt injection. Hot-reloaded between every agentic iteration.
- **AC3:** `core/prompt_templates.py` — named system prompt templates. Hot-reloaded on every generation.
- **AC4:** `core/workflows.py` — workflow mode definitions. Read at UI startup and on combo-box change.
- **AC5:** Python exceptions from user modifications are caught and displayed in the Final Response panel with a red error label — Karl never crashes on bad user code.

### 3.4 Generation Quality
- **AC1:** Stop tokens include `<|im_end|>`, `<|endoftext|>`, and `<|end_of_text|>` to prevent early truncation on Qwen-derived models.
- **AC2:** `echo=False` is set on all generation calls to prevent the prompt being echoed back into the output stream.
- **AC3:** Context overflow is handled by `_trim_history()` in both `LLMThread` and `AgenticThread` — the seed message is always preserved.
- **AC4:** If a generation hits `max_tokens` with `finish_reason == "length"`, Karl automatically chains a `Continue.` turn to complete the response.

---

## 4. Feature Specifications (All Implemented)

### 4.1 Session & Memory Management
- Conversations are saved as JSON to `data/sessions/` via `MemoryManager`.
- Sessions store full chat history + system prompt.
- Double-clicking a session in the left panel reloads it completely, replaying thoughts into the Diagnostic Lane and responses into the Final Response panel.
- **Force Thought** — injects a fake `<think>` block into the context window to seed or steer the model's reasoning chain.

### 4.2 Agentic Loop ("Ralph Wiggum" Loop)
- `AgenticThread` runs autonomously: generate → parse → check `should_continue()` → inject `build_next_prompt()` → repeat.
- Both functions are in `core/agentic_loop.py` and are hot-reloaded between iterations.
- Hard cap: `MAX_ITERATIONS = 5` by default (user editable).
- Stop signals: `[DONE]`, `[END]`, `[STOP]`, `FINAL ANSWER:` in the last response.
- **Auto-Loop Mode** — checkbox that feeds each single generation directly into the agentic loop automatically.

### 4.3 Universal RAG Pipeline
- Supported formats: PDF (PyMuPDF), DOCX (python-docx), TXT, PY, MD, CSV (plain-text fallback).
- Chunking: 200-word chunks with 50-word overlap (configurable).
- Embedding: `all-MiniLM-L6-v2` via `sentence-transformers`.
- Index: FAISS flat L2 index, persisted to `data/vector_db/`.
- Retrieval: top-k configurable (0–10), with optional source-filter and contextual chunk headers.
- Retrieval eval metrics: `hit@1`, `hit@3`, `hit@k`, reciprocal rank via `eval_retrieval()`.

### 4.4 Workflow Modes
Four named workflow modes, each bundling a template + RAG config + output schema + eval grader:
| Workflow | Template | RAG | Output |
|---|---|---|---|
| General Chat | `reasoning_minimal` | Optional | Free text |
| Document Extractor | `json_extractor` | Required (top-5) | Valid JSON |
| Grounded Answer | `grounded_answer` | Required (top-5) | Cited text or NOT IN CONTEXT |
| Code Review | `code_review` | Off | JSON array of findings |

### 4.5 Hardware Scout & Model Upgrade
- `core/hardware_scout.py` → `get_hardware_profile()` returns `{ram_gb, vram_gb, storage_gb}`.
- `app/engine/upgrade_manager.py` → `check_for_upgrade()` compares profile to `data/model_registry.json` tiers.
- On user approval: downloads GGUF, resets `ModelLoader` singleton, updates `data/active_model.json`, runs `git commit + git push`.

### 4.6 Training Data Curator
- 👍 / ✏️ rating buttons appear after every completed generation.
- 👍 saves the exchange as a positive example.
- ✏️ opens a correction dialog — user rewrites the ideal response.
- All data stored in `data/training/curated.jsonl`.
- Export via **Export for Unsloth** button → writes Unsloth-formatted JSONL for QLoRA fine-tuning.
- See `training/qlora_config_template.yaml` and `training/WHEN_TO_TUNE.md` for the full training pipeline.

### 4.7 Eval Harness
- `eval/harness.py` — dataset runner across all workflow modes.
- `eval/graders.py` — 5 graders: `keyword_hit`, `json_valid`, `groundedness`, `json_schema`, `regex_match`.
- `eval/run_eval.py` — CLI entry point.
- `eval/benchmark_rag.py` — retrieval-only benchmark with hit@k and MRR metrics.
- Datasets in `eval/datasets/*.jsonl` (one per workflow mode).

### 4.8 UI Design
- Three-column layout: Sessions/RAG | Diagnostic+Chat | Config
- **Diagnostic Lane** — `<think>` tokens streamed live in monospace
- **Final Response** — cleaned answer in readable prose font
- **Raw Token Archive** — toggled panel showing pre-parser token stream + `.tokens` file
- **Workflow Report** — one-line post-generation diagnostic (workflow, template, chunks, latency)
- **Status bar** — live generation state + last latency
- **Rich tooltips** — every interactive element has a detailed hover description
- Fully resizable via QSplitter handles

---

## 5. Out of Scope (Planned Next Milestones)

- **Tokenizer Visualization** — token IDs and per-token log-probabilities alongside raw stream
- **Session Branching** — fork a conversation at any point and explore alternate paths
- **Prompt Diff Tool** — side-by-side comparison of two trace logs
- **DPO Export** — direct preference optimisation dataset format (requires rejected-text storage at rating time)
