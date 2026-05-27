# Repository Structure

Karl separates stable application code from user-editable control files.

## Top Level

```text
Karl/
  AGENTS.md
  README.md
  main.py
  engine_test.py
  raw_test.py
  smoke_test.py
  download_test_model.py
  requirements.txt
  core/
  app/
  eval/
  training/
  docs/
  data/
```

## Root Scripts

| File | Purpose |
|---|---|
| `main.py` | Sets offline/noise-suppression environment and starts the PyQt6 app. |
| `download_test_model.py` | Downloads the default DeepSeek-R1 1.5B GGUF. |
| `raw_test.py` | Minimal direct llama-cpp generation test. |
| `engine_test.py` | Headless generation plus parser and trace test. |
| `smoke_test.py` | No-model smoke test for templates, workflows, and graders. |

## `core/`

The hackable layer:

| File | Purpose |
|---|---|
| `interaction_loop.py` | Builds ChatML prompts and pre-seeds `<think>`. |
| `prompt_templates.py` | Stores named system templates and placeholder filling. |
| `workflows.py` | Stores workflow definitions used by UI and evals. |
| `agentic_loop.py` | Controls reflect-loop stop and next-prompt logic. |
| `cognitive_parser.py` | Batch parser used by headless tests. |
| `hardware_scout.py` | Reports RAM, VRAM, and free storage. |

## `app/engine/`

| File | Purpose |
|---|---|
| `model_loader.py` | Singleton wrapper around `llama_cpp.Llama`. |
| `llm_thread.py` | Single generation worker thread. |
| `agentic_thread.py` | Reflect-loop worker thread. |
| `upgrade_manager.py` | Hardware-based model upgrade logic. |

## `app/ui/`

| File | Purpose |
|---|---|
| `main_window.py` | Main PyQt6 UI: Chat, Configure, Tuning. |
| `themes.py` | Theme palette registry and stylesheet generation. |
| `styles/neutral.qss` | Static Qt stylesheet assets. |

## `app/utils/`

| File | Purpose |
|---|---|
| `trace_logger.py` | Writes generation traces to JSONL. |
| `memory_manager.py` | Saves and loads session JSON. |
| `rag_pipeline.py` | Extracts, chunks, embeds, stores, retrieves, and evaluates document chunks. |
| `training_curator.py` | Saves approved/corrected examples and exports ShareGPT JSONL. |

## `eval/`

| File | Purpose |
|---|---|
| `harness.py` | Runs JSONL eval cases through the local model. |
| `graders.py` | Implements `exact_match`, `json_valid`, `keyword_hit`, `groundedness`, `not_in_context`. |
| `run_eval.py` | CLI for eval runs and dry runs. |
| `benchmark_rag.py` | Retrieval-only benchmark. |
| `datasets/*.jsonl` | Example datasets for workflow testing. |
| `results/` | Eval run artifacts; gitignored. |

## `training/`

| File | Purpose |
|---|---|
| `validate_dataset.py` | Checks curated dataset readiness. |
| `qlora_config_template.yaml` | Starter QLoRA configuration notes. |
| `WHEN_TO_TUNE.md` | Decision guide for prompt/RAG/tuning choices. |

## `docs/`

| File | Purpose |
|---|---|
| `01_problem_statement.md` | Why Karl exists. |
| `02_prd.md` | Product requirements and current scope. |
| `03_frd.md` | Functional requirements. |
| `04_architecture.md` | System architecture and data flow. |
| `05_scope_and_milestones.md` | Implemented and planned milestones. |
| `06_repo_structure.md` | This file. |
| `07_risk_register.md` | Risks, mitigations, and open issues. |

## `data/`

`data/` is local runtime state.

```text
data/
  model_registry.json      source-controlled model tier registry
  active_model.json        written by upgrade manager
  active_theme.json        runtime UI preference
  models/                  GGUF files, gitignored
  logs/
    traces/                trace JSONL, gitignored
    raw/                   raw token archives, gitignored
  sessions/                saved chats, gitignored
  training/                curated/exported datasets and adapters, gitignored
  vector_db/               FAISS index and metadata, gitignored
```

## Gitignore Policy

Source-controlled:

- application code
- docs
- eval datasets
- training templates
- `data/model_registry.json`

Ignored runtime state:

- model binaries
- traces
- raw token archives
- saved sessions
- vector indexes
- curated/exported training data
- theme preference
- eval results
