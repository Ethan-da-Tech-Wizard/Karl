# Repository Structure — Karl v2

The repository separates three distinct concerns:

- **`core/`** — The hackable layer. Simple Python. Users edit this.
- **`app/`** — The application layer. Threading, UI, persistence. Users generally don't edit this.
- **`eval/` + `training/`** — The measurement and tuning layer. Run independently of the UI.

---

## Full Structure

```
Karl/
│
├── main.py                          # Entry point — sets telemetry env vars FIRST, then launches UI
├── requirements.txt                 # Runtime dependencies
├── smoke_test.py                    # Fast validation: templates, workflows, graders — no model needed
│
├── core/                            # ━━ THE HACKABLE LAYER ━━ hot-reloaded every generation
│   ├── interaction_loop.py          # Prompt building and ChatML formatting
│   │                                # Edit this to change how prompts are constructed
│   ├── cognitive_parser.py          # Splits <think>...</think> from final response
│   │                                # Edit this to handle custom reasoning delimiters
│   ├── prompt_templates.py          # Named system prompt registry with {placeholder} filling
│   │                                # Add templates here — takes effect immediately on next gen
│   ├── workflows.py                 # Workflow definitions: template + RAG config + eval grader
│   │                                # Add workflows here — appears in UI dropdown on next gen
│   ├── agentic_loop.py              # Stop condition and next-prompt logic for autonomous loop
│   │                                # Edit this to change when/how the agentic loop stops
│   └── hardware_scout.py            # RAM/VRAM detection for model tier recommendation
│
├── app/                             # ━━ APPLICATION LAYER ━━ threading, UI, persistence
│   │
│   ├── engine/
│   │   ├── model_loader.py          # Singleton: loads and holds the llama-cpp-python instance
│   │   ├── llm_thread.py            # QThread: streaming, logprobs, trace logging, logit bias
│   │   ├── agentic_thread.py        # QThread: autonomous loop execution with hot-reload
│   │   └── upgrade_manager.py       # Hardware-aware model download and registry update
│   │
│   ├── ui/
│   │   ├── main_window.py           # MainWindow: all panels, signals, and event handlers
│   │   ├── diff_viewer.py           # DiffViewerDialog: side-by-side trace comparison (M17)
│   │   ├── eval_dashboard.py        # EvalDashboardDialog: history + live runner (M18/M19)
│   │   └── styles/
│   │       └── neutral.qss          # Dark neutral Qt stylesheet
│   │
│   └── utils/
│       ├── memory_manager.py        # Session save / load / fork / save_version
│       ├── rag_pipeline.py          # FAISS + sentence-transformers ingest + retrieve
│       ├── trace_logger.py          # Immutable JSONL generation log writer
│       └── training_curator.py      # SFT + DPO dataset collection, stats, export
│
├── eval/                            # ━━ EVALUATION LAYER ━━ runs with or without the UI
│   ├── __init__.py
│   ├── graders.py                   # Pure scoring functions — no side effects, no model calls
│   │                                # exact_match, json_valid, keyword_hit, groundedness, not_in_context
│   ├── harness.py                   # EvalHarness.run() — dataset → scored EvalReport
│   ├── run_eval.py                  # CLI: python eval/run_eval.py --dataset ... --workflow ...
│   ├── benchmark_rag.py             # RAG retrieval quality: Hit@k and MRR
│   └── datasets/                    # Seed eval cases
│       ├── document_extractor.jsonl # 10 document extraction cases (incl. adversarial)
│       ├── grounded_answer.jsonl    # 10 grounded QA cases (incl. out-of-context refusal)
│       └── code_review.jsonl        # 10 code review cases (incl. clean code baseline)
│
├── training/                        # ━━ TRAINING PREP LAYER ━━ offline, no UI dependency
│   ├── validate_dataset.py          # Pre-flight validator: schema, count, balance, tokens, dupes
│   ├── qlora_config_template.yaml   # QLoRA starter config (1.5B model, CPU / low-VRAM)
│   └── WHEN_TO_TUNE.md              # Decision guide: prompt → RAG → SFT → DPO
│
├── data/                            # ━━ LOCAL STATE ━━ gitignored
│   ├── models/                      # GGUF model files (place models here)
│   ├── model_registry.json          # Hardware tier → recommended model mapping
│   ├── vector_db/
│   │   ├── index.faiss              # Persisted FAISS index
│   │   └── metadata.json           # Chunk metadata (source, id, timestamp)
│   ├── logs/
│   │   ├── traces/                  # trace_YYYY-MM-DD.jsonl — one entry per generation
│   │   └── raw/                     # TIMESTAMP.tokens — raw streaming token files
│   ├── sessions/                    # session_TIMESTAMP[_fork_*][_v_*].json
│   └── training/
│       ├── curated.jsonl            # Append-only collected examples
│       ├── export_unsloth.jsonl     # SFT export (ShareGPT format)
│       └── export_dpo.jsonl         # DPO export (TRL DPOTrainer format)
│
└── docs/
    ├── 01_problem_statement.md      # Why Karl exists and what problem it solves
    ├── 02_prd.md                    # Product requirements and acceptance criteria
    ├── 03_frd.md                    # Functional requirements: UI specs, formats, threading
    ├── 04_architecture.md           # Component diagram and data flow
    ├── 05_scope_and_milestones.md   # Full milestone tracker M1–M21
    ├── 06_repo_structure.md         # This file
    └── 07_risk_register.md          # Risk identification and mitigation status
```

---

## Key Architectural Principle

The boundary between `core/` and `app/` is intentional and load-bearing.

`app/engine/llm_thread.py` imports `core/interaction_loop` via `importlib.reload()` on every generation. This means `app/` is a stable shell — it handles threading, UI events, and persistence — while `core/` is the experiment surface that changes freely. A syntax error in `core/` is caught and displayed in the UI. It never crashes the application.

The same hot-reload pattern applies to `prompt_templates.py`, `workflows.py`, and `agentic_loop.py` — any of these can be edited live.

---

## Dependency Notes

`requirements.txt` covers the runtime UI + inference stack. Training dependencies (PyTorch, transformers, peft, bitsandbytes, unsloth) are intentionally excluded — they are only needed for the training step and add 2–4 GB. Install them separately if you want to run `training/qlora_config_template.yaml`.
