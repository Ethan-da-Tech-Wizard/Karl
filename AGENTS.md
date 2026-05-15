# AGENTS.md — Full Handoff Document for AI Agents

> **Read this entire file before touching any code.**
> This is your primary context. The README is for humans. This file is for you.

---

## What Is Karl?

Karl is a **privacy-first, offline Prompt Engineering Workbench** — a PyQt6 desktop application
that runs local LLMs via `llama-cpp-python` (in-process, no server, no ports, no network calls).

**Philosophy:** UI for convenience. Code for control. Measurement for trust.

It started as an LLM introspection toy (see the problem statement) and has been transformed into
a professional-grade system for prompt engineers. The key distinction from tools like LM Studio
or Ollama: every layer is measurable, reproducible, and hackable.

**Current branch:** `claude/karl-prompt-workbench-F5lWl`
**Remote:** `https://github.com/Ethan-da-Tech-Wizard/Karl.git`
**Entry point:** `python main.py`

---

## What Has Been Built — All 21 Milestones + Fine-Tuning System

### Phase 0 — Foundation (M1–M6) ✅
All complete. Standard introspection loop: model loads via singleton, LLMThread streams tokens,
`<think>` blocks route to Diagnostic Lane, everything else routes to Chat. Sessions persist as JSON.
FAISS RAG pipeline ingests documents. `core/` is hot-reloaded on every generation.

### Phase 1 — Workbench Infrastructure (M7–M15) ✅

| M | What it is | Key files |
|---|---|---|
| M7 | Raw Token Archive — toggleable panel, `.tokens` files in `data/logs/raw/` | `llm_thread.py` `new_raw_token` signal |
| M8 | Hardware Scout — RAM/VRAM detection, model tier recommendation | `core/hardware_scout.py`, `data/model_registry.json`, `app/engine/upgrade_manager.py` |
| M9 | Auto-Loop — checkbox routes `generation_finished` → `start_agentic_loop()` | `main_window.py` |
| M10 | Self-Upgrade — downloads GGUF, resets singleton, commits to git | `upgrade_manager.perform_upgrade()` |
| M11 | Training Data Curator — 👍/👎 rating, correction editor, Unsloth JSONL export | `app/utils/training_curator.py` |
| M12 | Prompt Template Registry — named templates with `{placeholder}` filling, hot-reloaded | `core/prompt_templates.py` |
| M13 | Workflow Engine — named modes linking template + RAG config + eval grader | `core/workflows.py` |
| M14 | Eval Harness — 5 graders, headless CLI runner, 3 seed datasets | `eval/graders.py`, `eval/harness.py`, `eval/run_eval.py` |
| M15 | Hardened RAG — persistent FAISS, per-chunk metadata, contextual headers, retrieval metrics | `app/utils/rag_pipeline.py` |

### Phase 2 — Measurement and Control (M16–M21) ✅

| M | What it is | Key files |
|---|---|---|
| M16 | Session Branching — fork_session(), save_version(), newest-first sort | `app/utils/memory_manager.py`, Fork/📌 buttons in UI |
| M17 | Prompt Diff Viewer — side-by-side trace comparison, line-level diff highlighting | `app/ui/diff_viewer.py` |
| M18 | Eval Dashboard — history table with colour-coded pass rates | `app/ui/eval_dashboard.py` (_HistoryPanel) |
| M19 | Live Eval Runner — EvalRunThread, progress bar, auto-saves report | `app/ui/eval_dashboard.py` (_RunnerPanel) |
| M20 | Logit Bias Editor — `word: ±float` per line, tokenised at gen time, applied incl. continuations | `main_window.py` `_parse_logit_bias()` |
| M21 | Token Confidence Heatmap — per-token HTML colour (green→red by logprob), avg confidence bar | `main_window.py` `_render_heatmap()` |

### Lite Fine-Tuning System (karl_finetune/) ✅

A complete local fine-tuning pipeline as a self-contained Python package.
Same repo, separate process. Training deps are in `requirements-training.txt` — NOT `requirements.txt`.

**CLI flow (in order):**
```
python -m karl_finetune.validate_dataset data/train.jsonl
python -m karl_finetune.format_dataset data/train.jsonl --template alpaca
python -m karl_finetune.train_lora configs/finetune_config.json --dry-run
python -m karl_finetune.train_lora configs/finetune_config.json
python -m karl_finetune.run_eval configs/eval_config.json --mode base
python -m karl_finetune.run_eval configs/eval_config.json --mode tuned
python -m karl_finetune.compare_outputs
```

| File | What it does |
|---|---|
| `karl_finetune/privacy_guard.py` | Scans text for emails, phones, SSNs, API keys, PEM keys, AWS keys before training |
| `karl_finetune/validate_dataset.py` | Validates alpaca and ShareGPT format JSONL: schema, count, token length, dupes, privacy scan |
| `karl_finetune/format_dataset.py` | Converts raw JSONL to `alpaca` (### blocks), `chat` (messages list), or `chatml` (<\|im_start\|>) format |
| `karl_finetune/train_lora.py` | LoRA/QLoRA training via transformers + peft + trl. `--dry-run` validates without GPU. |
| `karl_finetune/run_eval.py` | Runs eval prompts against base or tuned model (`--mode base/tuned`), saves JSONL results |
| `karl_finetune/compare_outputs.py` | Scores base vs tuned on keyword hit, tone markers, length ratio. Generates markdown report. |
| `configs/finetune_config.json` | Default config: TinyLlama-1.1B, lora_r=16, 2 epochs, CPU-compatible |
| `configs/eval_config.json` | Eval config pointing at same model + adapter dir |
| `data/train.jsonl` | 20 seed examples: complaint rewriting, ticket classification, note-to-email |
| `data/eval.jsonl` | 8 held-out eval cases with expected_keywords |

**Key design decision:** Training deps (torch, transformers, peft, trl, datasets, accelerate, bitsandbytes)
are intentionally excluded from `requirements.txt`. They're 2–4 GB and only needed if the user
wants to run training. Karl itself stays light. Install from `requirements-training.txt` in a
separate venv if needed.

---

## Architecture — What You Must Understand

### The Hot-Reload Pattern (Critical)

`app/engine/llm_thread.py` imports core files via `importlib.reload()` on every generation.
This means the user can edit any file in `core/` and the change takes effect without restarting.

Files that are hot-reloaded:
- `core/interaction_loop.py` — prompt string construction
- `core/prompt_templates.py` — named template registry
- `core/workflows.py` — workflow mode definitions
- `core/agentic_loop.py` — agentic stop condition (per iteration)

**Do NOT put heavy imports or stateful objects in these files.** They reload on every call.

### Threading Model

```
Main UI Thread (MainWindow)
  ├── LLMThread (single generation)
  │     signals: new_thought_token, new_chat_token, new_raw_token,
  │              generation_finished, token_logprobs_ready, error_occurred
  ├── AgenticThread (autonomous loop)
  │     signals: iteration_finished, loop_finished, error_occurred
  ├── UpgradeCheckThread (startup hardware check)
  ├── UpgradeDownloadThread (model download)
  └── EvalRunThread (headless eval, in EvalDashboardDialog)
```

**Rule:** Never touch UI widgets from inside `run()`. Only emit signals.
All signals route back to the main thread automatically via Qt's signal/slot mechanism.

### LLMThread — How It Works

1. Reloads `core/interaction_loop` via importlib
2. Trims history: sliding window, per-message char cap, always keeps seed message
3. Calls `llm(prompt, stream=True, logprobs=5, logit_bias=..., ...)`
4. Parses streaming tokens with a suffix-guard state machine:
   - `<think>` detected → `in_thought = True` → route to `new_thought_token`
   - `</think>` detected → `in_thought = False` → route to `new_chat_token`
   - Guard: if buffer ends with a partial tag (`<`, `</`, `</t`...) don't flush yet
5. Collects `(token_str, top_logprob)` pairs → emits `token_logprobs_ready` on finish
6. If `finish_reason == "length"` → emits `generation_finished(truncated=True)`
   → MainWindow fires `_fire_generation()` to auto-continue
7. Writes full trace to `data/logs/traces/trace_YYYY-MM-DD.jsonl`

**Logit bias:** `_parse_logit_bias()` in MainWindow tokenises each `word: ±float` line
using the loaded model and passes `{token_id: float}` to llama. Stored as `_last_logit_bias`
and forwarded to continuations via `_fire_generation()`.

### Workflow System

A **Workflow** = template name + RAG top-k + require_rag flag + eval grader name.
Defined in `core/workflows.py`. Selecting a workflow in the UI:
1. Syncs the Template combo to the workflow's default template
2. Updates the RAG top-k spinner
3. Stores `_last_workflow` and `_last_template` for trace logging

The system prompt is built via `get_template(tpl_name, rag_context=..., schema=..., code=...)`
EXCEPT in `general_chat` workflow where the raw System Prompt text box is used directly.

### Training Curator — SFT + DPO Data Collection

Every thumbs-up/correction writes to `data/training/curated.jsonl`:
```json
{"timestamp": "...", "source": "thumbs_up|corrected", "messages": [...], "rejected": "...or null"}
```
- Thumbs-up → `source: thumbs_up`, no `rejected` field
- Thumbs-down + correction → `source: corrected`, `rejected` = original response
  This makes every correction automatically a DPO pair. No extra steps.

Export functions:
- `export_unsloth()` → SFT format (ShareGPT messages list)
- `export_dpo()` → TRL DPOTrainer format (`prompt`, `chosen`, `rejected`)

### RAG Pipeline

```
ingest_file(path) → extract text → chunk → encode → add to FAISS → save index+metadata
retrieve(query, top_k) → encode → FAISS search → fetch metadata → optional headers → return list[str]
```

Persistence: `data/vector_db/index.faiss` + `data/vector_db/metadata.json`.
Loaded on `RAGPipeline.__init__()`. Saved after every ingest.
`contextual_headers=True` prepends `[Source: filename | Chunk N]` to each chunk.

### Model Singleton

`ModelLoader.get_instance()` loads once, returns same object forever.
`ModelLoader.reset_instance()` forces reload on next call (used by upgrade manager).
Config: `n_ctx=4096`, `verbose=False`.
Model path: `data/models/deepseek-r1-1.5b.gguf` (default) or whatever `active_model.json` specifies.

### Privacy Isolation

`main.py` sets these environment variables as the VERY FIRST LINES before any import:
```python
os.environ["HF_HUB_OFFLINE"]            = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_DATASETS_OFFLINE"]       = "1"
os.environ["TOKENIZERS_PARALLELISM"]    = "false"
```
This blocks all huggingface_hub telemetry before sentence-transformers can phone home.

---

## File Map — Every File and What It Does

```
Karl/
├── main.py                     Entry point. Sets env vars first, then launches PyQt6 app.
├── requirements.txt            Runtime deps: llama-cpp-python, PyQt6, sentence-transformers, faiss-cpu, etc.
├── requirements-training.txt   Training-only deps: torch, transformers, peft, trl, datasets, bitsandbytes.
├── smoke_test.py               Fast syntax + bridge test. No model needed. Run after any core/ change.
├── engine_test.py              Headless inference test. Needs model loaded.
├── download_test_model.py      Downloads DeepSeek-R1-Distill-Qwen-1.5B Q4_K_M (~1GB).
│
├── core/                       HOT-RELOADED every generation. User edits these freely.
│   ├── interaction_loop.py     build_prompt(system, history) → str. Controls ChatML formatting.
│   ├── prompt_templates.py     TEMPLATES dict. get_template(name, **kwargs). Hot-reloaded.
│   ├── workflows.py            WORKFLOWS dict. get_workflow(name). Defines mode → template+RAG+grader.
│   ├── cognitive_parser.py     Batch <think> parser. Used by engine_test.py (not LLMThread).
│   ├── agentic_loop.py         stop_condition(response, iteration) → bool. Hot-reloaded per iter.
│   └── hardware_scout.py       get_hardware_profile() → {ram_gb, vram_gb, storage_gb}.
│
├── app/
│   ├── engine/
│   │   ├── model_loader.py     Singleton. get_instance() / reset_instance(). Loads GGUF.
│   │   ├── llm_thread.py       QThread. Streaming + logprobs + logit_bias + trace logging.
│   │   ├── agentic_thread.py   QThread. Autonomous loop with per-iteration hot-reload.
│   │   └── upgrade_manager.py  check_for_upgrade() / perform_upgrade(). Downloads + git commit.
│   ├── ui/
│   │   ├── main_window.py      Everything: all panels, all signals, all handlers. ~800 lines.
│   │   ├── diff_viewer.py      DiffViewerDialog. Loads trace JSONL, side-by-side, diff highlight.
│   │   ├── eval_dashboard.py   EvalDashboardDialog. History table + EvalRunThread live runner.
│   │   └── styles/neutral.qss  Dark neutral Qt stylesheet.
│   └── utils/
│       ├── memory_manager.py   save_session / load_session / fork_session / save_version / list_sessions.
│       ├── rag_pipeline.py     RAGPipeline. ingest_file / retrieve / save_index / eval_retrieval.
│       ├── trace_logger.py     TraceLogger. log_generation() → daily JSONL file.
│       └── training_curator.py save_example / export_unsloth / export_dpo / get_stats / get_dpo_stats.
│
├── eval/
│   ├── graders.py              exact_match, json_valid, keyword_hit, groundedness, not_in_context.
│   ├── harness.py              EvalHarness.run(dataset, workflow) → EvalReport. save_report().
│   ├── run_eval.py             CLI: python eval/run_eval.py --dataset ... --workflow ...
│   ├── benchmark_rag.py        eval_retrieval(): Hit@k and MRR for RAG quality testing.
│   └── datasets/               document_extractor.jsonl, grounded_answer.jsonl, code_review.jsonl
│
├── karl_finetune/              Lite Fine-Tuning System. No UI dep. CLI-only.
│   ├── __init__.py
│   ├── privacy_guard.py        scan_text / scan_dataset. Runs before validation.
│   ├── validate_dataset.py     validate(path, format). Supports alpaca + ShareGPT.
│   ├── format_dataset.py       format_dataset(path, template). alpaca / chat / chatml.
│   ├── train_lora.py           train(config_path, dry_run). SFTTrainer + peft. Saves adapter.
│   ├── run_eval.py             run_eval(config, mode). base or tuned. Saves JSONL results.
│   └── compare_outputs.py      compare(base, tuned). Scores + generates markdown report.
│
├── configs/
│   ├── finetune_config.json    Default: TinyLlama-1.1B, lora_r=16, 2 epochs.
│   └── eval_config.json        Default: same model, adapter_dir, reports_dir.
│
├── training/                   Decision layer. Not the training execution layer.
│   ├── validate_dataset.py     Earlier validator (curated.jsonl format). Still works.
│   ├── qlora_config_template.yaml  YAML reference config for Unsloth/HF TRL.
│   └── WHEN_TO_TUNE.md         Decision guide: prompt → RAG → SFT → DPO.
│
├── data/
│   ├── model_registry.json     Source-controlled. Maps hardware tiers to model recommendations.
│   ├── train.jsonl             20 seed training examples (complaint / classify / email).
│   ├── eval.jsonl              8 held-out eval cases with expected_keywords.
│   ├── models/                 gitignored. Place GGUF files here.
│   ├── vector_db/              gitignored. index.faiss + metadata.json.
│   ├── logs/traces/            gitignored. trace_YYYY-MM-DD.jsonl per day.
│   ├── logs/raw/               gitignored. TIMESTAMP.tokens raw streams.
│   ├── sessions/               gitignored. session_*.json files.
│   └── training/               gitignored. curated.jsonl, export files.
│
├── outputs/                    gitignored. Fine-tuning artifacts.
│   ├── adapters/               LoRA adapter checkpoints + training_summary.json.
│   └── reports/                eval_base.jsonl, eval_tuned.jsonl, comparison_*.md.
│
└── docs/
    ├── 01_problem_statement.md  v2: measurement gap framing, dual persona.
    ├── 02_prd.md               v2: full AC for all 21 milestones.
    ├── 03_frd.md               v2: every UI panel specced, threading model, data formats.
    ├── 04_architecture.md      v2: full Mermaid diagram, component detail sections.
    ├── 05_scope_and_milestones.md  All M1–M21 with goals, tasks, success criteria.
    ├── 06_repo_structure.md    Annotated file tree with purpose of every file.
    └── 07_risk_register.md     13 risks, R07 closed, R08 open (log rotation).
```

---

## How the UI Is Wired — MainWindow Key Methods

```python
# Generation start (send_message)
text → chat_display.append → chat_history.append → resolve workflow/template/RAG
→ _last_logit_bias = _parse_logit_bias()
→ LLMThread(sys_prompt, history, hyperparams, retrieved,
             logit_bias=_last_logit_bias, workflow=wf_name, template=tpl_name)
→ thread.token_logprobs_ready.connect(handle_token_logprobs)
→ thread.generation_finished.connect(handle_generation_finished)

# Generation finish (handle_generation_finished)
→ chat_history.append(response)
→ if truncated: _fire_generation(continuation_history, start_in_thought=True)
→ else: enable buttons, update report panel, enable rating buttons

# Continuation (_fire_generation)
→ LLMThread(..., logit_bias=_last_logit_bias, workflow=_last_workflow, template=_last_template)
# _last_* are set at generation start, NOT re-resolved on continuation

# Token logprobs (handle_token_logprobs)
→ _last_logprobs = logprobs
→ update confidence_bar colour (green/amber/red by avg logprob)
→ if heatmap visible: _render_heatmap(logprobs)

# Heatmap toggle (_toggle_heatmap_panel)
→ show/hide heatmap_display
→ if toggled on and _last_logprobs exists: _render_heatmap(_last_logprobs)

# Session fork (fork_session)
→ memory_manager.fork_session(current_session_file)
→ current_session_file = new_file
→ refresh_session_list()

# DPO: thumbs-down correction (_rate_thumbs_down)
→ dialog shows _last_response pre-filled
→ on save: save_example(good_response=corrected, rejected_response=_last_response)
# _last_response is the ORIGINAL bad response — stored as the DPO rejected sample
```

---

## Data Formats — Reference

### Trace log entry (`data/logs/traces/`)
```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "execution_time_seconds": 3.42,
  "workflow": "grounded_answer",
  "template": "grounded_answer",
  "hyperparameters": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 512},
  "rag_context_used": ["chunk 1", "chunk 2"],
  "compiled_prompt": "<|im_start|>system\n...",
  "raw_output": "<think>...</think> final answer",
  "parsed_thought": "...",
  "parsed_response": "..."
}
```

### Training example (`data/training/curated.jsonl`)
```json
{
  "timestamp": "...", "source": "corrected",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."},
    {"role": "assistant", "content": "corrected response"}
  ],
  "rejected": "original bad response"
}
```

### Eval dataset case
```json
{"id": "e001", "prompt": "...", "context": "...", "grader": "json_valid", "schema_keys": ["date"]}
```

### Fine-tuning alpaca format (`data/train.jsonl`)
```json
{"instruction": "Rewrite professionally.", "input": "yo this is trash", "output": "I'm sorry..."}
```

### Fine-tuning eval case (`data/eval.jsonl`)
```json
{"id": "eval_001", "instruction": "...", "input": "...", "expected_keywords": ["sorry", "help"]}
```

---

## Key Gotchas — Read Before You Touch Anything

1. **`llama-cpp-python` compiled from source** — pre-built wheels throw `Illegal Instruction`
   on Intel 12th Gen. Compile: `$env:CMAKE_ARGS="-DGGML_NATIVE=ON"; pip install llama-cpp-python --no-binary llama-cpp-python`

2. **Training deps are separate** — do NOT add torch/transformers/peft to `requirements.txt`.
   They live in `requirements-training.txt` only. Mixing them can break llama-cpp-python's memory layout.

3. **Logit bias uses live tokenisation** — `_parse_logit_bias()` calls `llm.tokenize()` at
   generation time. If no model is loaded, it silently returns `{}`. Do NOT cache token IDs
   across model switches — the vocab is model-specific.

4. **`_fire_generation()` must forward `_last_*` fields** — continuation of a truncated
   response must use the same logit_bias, workflow, and template as the original generation.
   This is already implemented. If you refactor generation start, preserve this.

5. **Session list sort is by mtime** — `list_sessions()` uses `os.path.getmtime()`.
   In test environments without real file writes, sort order may be unexpected.

6. **DPO pairs require `rejected` field** — `export_dpo()` filters for records where
   `source == "corrected"` AND `"rejected" in record`. Old curated.jsonl entries from
   before this feature was added won't appear in DPO export — that's intentional.

7. **EvalRunThread monkey-patches harness.run** — the live runner in `eval_dashboard.py`
   wraps the harness run method to emit `case_done` signals. If `eval/harness.py` changes
   its internal structure significantly, review `_patched_run` in `eval_dashboard.py`.

8. **`data/model_registry.json` is source-controlled** — edit it to add model tiers.
   The upgrade manager reads it at runtime.

9. **Smoke test must pass before any commit** — `python smoke_test.py` tests the
   template/workflow/grader bridge without a model. If this fails, something in `core/` broke.

10. **`outputs/` is gitignored** — fine-tuning adapters and comparison reports are local only.
    If you want to persist a trained adapter, users must manually back it up.

---

## What Is Not Yet Built (Genuine Gaps)

### Open Risk
- **R08: Trace log rotation** — `data/logs/traces/` grows indefinitely. Need to add log rotation
  (keep last N days) to `app/utils/trace_logger.py`. Low urgency but real on heavy use.

### Not in scope (by design)
- **Training execution in-UI** — The UI has no "Start Training" button. Fine-tuning runs headless
  via `karl_finetune/train_lora.py`. This is intentional: training deps are heavy and optional.
  A future milestone could add a TrainingThread that launches the training script as a subprocess
  and streams stdout back to a progress panel.
- **Multi-model comparison** — Run same prompt against two different GGUF files.
- **Streamlit UI for fine-tuning** — The concept doc mentioned this. Not built.

---

## How to Verify Everything Works

```bash
# 1. Syntax check all key files
python -m py_compile main.py app/engine/llm_thread.py app/ui/main_window.py \
  app/utils/memory_manager.py app/utils/training_curator.py \
  app/ui/diff_viewer.py app/ui/eval_dashboard.py \
  karl_finetune/privacy_guard.py karl_finetune/validate_dataset.py \
  karl_finetune/format_dataset.py karl_finetune/train_lora.py \
  karl_finetune/run_eval.py karl_finetune/compare_outputs.py

# 2. Smoke test (no model needed)
python smoke_test.py

# 3. Validate the seed dataset
python -m karl_finetune.validate_dataset data/train.jsonl

# 4. Format dataset dry run
python -m karl_finetune.format_dataset data/train.jsonl --template alpaca

# 5. Fine-tuning dry run (no GPU, no deps needed for --dry-run flag check fails early)
python -m karl_finetune.train_lora configs/finetune_config.json --dry-run

# 6. Full app (needs model in data/models/)
python main.py
```

---

## Interview Positioning (Context for Why This Exists)

Karl was built to demonstrate systems-level prompt engineering thinking for a technical interview.
The pitch: "I'm not trying to be just a chatbot user. I built tooling around LLM behavior —
prompt testing, RAG, fine-tuning preparation, and evaluation — because that's what a real
Prompt Engineer does in a production environment."

Key interview lines embedded in the system:
- *"RAG is for knowledge. Fine-tuning is for behavior. Those are different problems."*
- *"I don't trust a prompt change until I've run it against a dataset and scored it."*
- *"Every generation is logged — prompt, hyperparams, retrieved chunks, reasoning trace, response.
  I can diff two runs and see exactly what changed."*
- *"I validate the dataset first because fine-tuning doesn't fix bad data — it amplifies it."*
- *"I added a privacy guard because fine-tuned models can reproduce training data verbatim."*
