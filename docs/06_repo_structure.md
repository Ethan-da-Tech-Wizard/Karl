# Repository Structure & File Specifications — Karl v2

The repository separates the **application layer** (stable, threading-safe UI and engine code)
from the **hackable core** (simple, hot-reloadable Python scripts the user edits freely).

---

## Full Tree

```
Karl/
│
├── AGENTS.md                   ← AI agent handoff document (read this first)
├── README.md                   ← Human-readable quickstart
├── main.py                     ← Entry point: boots QApplication, loads stylesheet
├── engine_test.py              ← Headless engine test (no UI — validates model + trace logger)
├── smoke_test.py               ← Import-level smoke test (no model required)
├── download_test_model.py      ← Downloads DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M to data/models/
├── requirements.txt            ← pip dependencies
│
├── core/                       ← THE HACKABLE LAYER — edit these freely
│   ├── interaction_loop.py     ← build_prompt(system_prompt, chat_history) → str
│   │                              Hot-reloaded before every generation
│   ├── agentic_loop.py         ← should_continue(i, response) + build_next_prompt(response, i)
│   │                              Hot-reloaded between every agentic iteration
│   ├── prompt_templates.py     ← TEMPLATES dict + get_template() + list_templates()
│   │                              Hot-reloaded before every generation
│   ├── workflows.py            ← WORKFLOWS dict + get_workflow() + list_workflows()
│   │                              Read at UI startup and on combo-box change
│   ├── cognitive_parser.py     ← parse_thought_stream(raw_text) → (thought, response)
│   │                              Batch parser — used by engine_test.py and eval harness only
│   └── hardware_scout.py       ← get_hardware_profile() → {ram_gb, vram_gb, storage_gb}
│                                  Used by System Config and model tier guidance
│
├── app/
│   ├── engine/
│   │   ├── model_loader.py     ← ModelLoader singleton: get_instance() / reset_instance()
│   │   │                          model-aware n_ctx context size, verbose=False
│   │   ├── llm_thread.py       ← LLMThread(QThread): single-shot streaming generation
│   │   │                          Inline state machine: routes <think> tokens to thought panel
│   │   │                          Handles truncation chaining (finish_reason == "length")
│   │   ├── agentic_thread.py   ← AgenticThread(QThread): autonomous multi-turn loop
│   │   │                          Hot-reloads agentic_loop.py between iterations
│   │   ├── swarm_orchestrator.py ← Architect/Coder/Tester loop for local code edits
│   │   ├── swarm_agents.py     ← Agent implementations used by the orchestrator
│   │   └── websocket_server.py ← Local JSON-RPC bridge for VS Code / Code OSS
│   │
│   ├── ui/
│   │   ├── main_window.py      ← MainWindow(QMainWindow): full UI layout stack
│   │   │                          Three-column layout (Sessions | Center | Config)
│   │   │                          Rich tooltips on every interactive element
│   │   │                          Status bar with live state + latency
│   │   ├── workspaces/         ← Multi-workspace widgets (Workbench, Prompt Lab, etc.)
│   │   ├── widgets/            ← Common widgets (Status bar, settings rows, downloader cards)
│   │   └── themes.py           ← Design system palette, mono fonts, and dynamically compiled QSS stylesheet
│   │
│   └── utils/
│       ├── trace_logger.py     ← TraceLogger: writes JSONL to data/logs/traces/
│       │                          Fields: timestamp, execution_time, workflow, template,
│       │                          hyperparameters, rag_context_used, compiled_prompt,
│       │                          raw_output, parsed_thought, parsed_response
│       ├── memory_manager.py   ← MemoryManager: save/load/list sessions as JSON
│       │                          Sessions stored in data/sessions/
│       ├── session_tree.py     ← SessionNode / SessionTree: nested conversation tree structure supporting branching
│       ├── rag_pipeline.py     ← RAGPipeline: ingest / retrieve / eval
│       │                          FAISS flat L2 + all-MiniLM-L6-v2 embeddings
│       │                          Persistent index in data/vector_db/
│       │                          Supports PDF, DOCX, TXT, PY, MD, CSV
│       └── training_curator.py ← save_example() / get_stats() / export_unsloth() / export_dpo()
│                                  Curated examples stored in data/training/curated.jsonl
│
├── eval/
│   ├── __init__.py
│   ├── harness.py              ← EvalHarness: loads dataset, runs generations, applies graders
│   ├── graders.py              ← 5 graders: keyword_hit, json_valid, groundedness,
│   │                              json_schema, regex_match
│   ├── run_eval.py             ← CLI: python eval/run_eval.py --workflow <name> --top_k <n>
│   ├── benchmark_rag.py        ← Retrieval-only benchmark: hit@k and MRR
│   └── datasets/
│       ├── document_extractor.jsonl
│       ├── grounded_answer.jsonl
│       └── code_review.jsonl
│
├── tests/                      ← AUTOMATED TESTS — run via run_all_tests.py
│   ├── test_cognitive_compression.py
│   ├── test_cognitive_parser.py
│   ├── test_eval_harness.py
│   ├── test_hardware_scout.py
│   ├── test_memory_manager.py
│   ├── test_rag_pipeline.py
│   ├── test_session_tree.py
│   ├── test_trace_logger.py
│   └── test_training_curator.py
│
├── training/
│   ├── WHEN_TO_TUNE.md         ← Decision guide: prompt engineering vs. fine-tuning
│   ├── qlora_config_template.yaml ← Ready-to-use QLoRA config for Unsloth
│   └── validate_dataset.py     ← Validates curated.jsonl before a training run
│
├── vscode-extension/
│   ├── extension.js            ← VS Code / Code OSS webview client and editor commands
│   ├── package.json            ← Extension manifest, commands, settings, Activity Bar view
│   ├── package-lock.json       ← npm lockfile
│   ├── media/icon.svg          ← Activity Bar icon
│   └── *.vsix                  ← Locally packaged extension artifacts
│
├── data/                       ← Local state — partially gitignored
│   ├── model_registry.json     ← Source-controlled: model tier definitions
│   ├── active_model.json       ← Written at runtime: current model path + tier
│   ├── models/                 ← GITIGNORED: GGUF model files (large binaries)
│   ├── hf_models/              ← GITIGNORED: HuggingFace weights for LoRA/QLoRA training
│   ├── adapters/               ← GITIGNORED: trained LoRA adapters
│   ├── codex_library/          ← Local reference docs served to the extension
│   ├── logs/
│   │   ├── traces/             ← GITIGNORED: trace_YYYY-MM-DD.jsonl files
│   │   └── raw/                ← GITIGNORED: *.tokens raw archive files
│   ├── sessions/               ← GITIGNORED: saved conversation JSON files
│   ├── training/               ← GITIGNORED: curated.jsonl + exported datasets
│   ├── prompt_pairs/           ← GITIGNORED: saved Prompt Lab A/B pairs
│   └── vector_db/              ← GITIGNORED: index.faiss + metadata.json
│
└── docs/
    ├── 01_problem_statement.md
    ├── 02_prd.md
    ├── 03_frd.md
    ├── 04_architecture.md
    ├── 05_scope_and_milestones.md
    ├── 06_repo_structure.md    ← THIS FILE
    ├── 07_risk_register.md
    └── 08_vscode_extension.md  ← VS Code bridge architecture and roadmap
```

---

## Architectural Principles

### 1. The Hackable Core
`core/` is the user's playground. Every file is hot-reloaded via `importlib.reload()` —
the user edits the file, saves, and clicks Generate. No restart needed.

### 2. Thread Safety
All LLM work runs on `QThread` subclasses. The UI thread only processes signals.
**Rule:** Never touch UI widgets from inside `run()`. Only emit signals.

### 3. Singleton Model
`ModelLoader` holds the `llama_cpp.Llama` instance as a class-level singleton.
Loading happens once. `reset_instance()` forces a reload on the next call.

### 4. Data Immutability
Trace logs and raw token archives are append-only. They are never modified after writing.
Even a crashed generation leaves a partially-written file that can be inspected.

### 5. Gitignore Strategy
Large binaries (`models/`), runtime artifacts (`logs/`, `sessions/`, `vector_db/`, `training/`)
are gitignored. Configuration that affects reproducibility (`model_registry.json`) is
source-controlled.
