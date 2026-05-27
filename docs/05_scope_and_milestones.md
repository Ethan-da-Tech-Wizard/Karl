# Scope and Milestones

## Scope Lock

Karl is an offline LLM introspection workbench. Its core scope is:

- local in-process inference
- visible reasoning stream
- hackable prompt and loop logic
- local RAG
- immutable traces
- training-data curation
- eval-driven iteration

Karl is not a consumer chatbot, hosted model server, or full training platform.
It prepares data and guidance for tuning, but it does not currently run the
training job end to end.

## Implemented Milestones

### 1. Headless Introspection Engine

Files:

- `engine_test.py`
- `raw_test.py`
- `core/cognitive_parser.py`
- `app/utils/trace_logger.py`

Status:

- local model can be loaded headlessly
- raw output can be parsed after generation
- traces are written as JSONL

### 2. Dual-Pane Thought Stream UI

Files:

- `app/ui/main_window.py`
- `app/engine/llm_thread.py`

Status:

- reasoning and response streams are visually separated
- streaming parser routes `<think>` content to the reasoning pane
- final answer content goes to the response pane

### 3. Session and Context Management

Files:

- `app/utils/memory_manager.py`
- `app/engine/llm_thread.py`
- `app/engine/agentic_thread.py`

Status:

- sessions save/load as JSON
- token-aware trimming protects the 4096-token model window
- generation tokens are clamped to remaining context room

### 4. Universal RAG Pipeline

File:

- `app/utils/rag_pipeline.py`

Status:

- supports PDF, DOCX, TXT, PY, MD, CSV, XLSX, XLS
- persists FAISS index and metadata
- uses semantic retrieval plus keyword reranking
- includes retrieval eval helpers

### 5. Hackable Decoupling

Files:

- `core/interaction_loop.py`
- `core/prompt_templates.py`
- `core/workflows.py`
- `core/agentic_loop.py`

Status:

- prompt building and loop logic are user-editable Python
- core prompt logic is hot-reloaded at runtime

### 6. Manual Agentic Reflect Loop

Files:

- `core/agentic_loop.py`
- `app/engine/agentic_thread.py`
- `app/ui/main_window.py`

Status:

- Configure page exposes `reflect` and `halt loop`
- loop runs until stop condition, user stop, or `MAX_ITERATIONS`
- default max iterations: 20
- auto-triggering after every generation is disabled by design

### 7. Raw Token Archive

Files:

- `app/engine/llm_thread.py`
- `app/engine/agentic_thread.py`

Status:

- every raw chunk is emitted before parsing
- every generation writes a `.tokens` file
- current UI does not expose a live raw-token panel

### 8. Hardware Scout and Model Registry

Files:

- `core/hardware_scout.py`
- `data/model_registry.json`
- `app/engine/upgrade_manager.py`

Status:

- RAM, VRAM, and storage profile are checked
- model registry describes upgrade tiers
- eligible upgrades can be surfaced in the UI

### 9. Model Self-Upgrade Record

File:

- `app/engine/upgrade_manager.py`

Status:

- approved upgrade downloads the model
- resets model singleton
- writes `data/active_model.json`
- commits and pushes the active-model update

### 10. Training Data Curator

Files:

- `app/utils/training_curator.py`
- `app/ui/main_window.py`

Status:

- `approve` saves the current response
- `teach` saves a corrected response
- export writes ShareGPT/Unsloth-style JSONL
- tuning page shows stats and export button

### 11. Eval Harness

Files:

- `eval/harness.py`
- `eval/graders.py`
- `eval/run_eval.py`
- `eval/benchmark_rag.py`

Status:

- JSONL dataset runner
- dry-run mode for grader validation
- output report writer
- RAG benchmark support
- graders: `exact_match`, `json_valid`, `keyword_hit`, `groundedness`, `not_in_context`

### 12. Workflow Modes

Files:

- `core/prompt_templates.py`
- `core/workflows.py`
- `app/ui/main_window.py`

Status:

- workflows are selectable in Configure
- selected workflow sets template and default RAG top-k
- templates are rendered before generation
- workflow/template names are logged in traces

### 13. Training Path Formalization

Files:

- `training/validate_dataset.py`
- `training/qlora_config_template.yaml`
- `training/WHEN_TO_TUNE.md`

Status:

- validator checks dataset shape and readiness
- template config documents QLoRA settings
- guidance explains when to prompt, use RAG, tune, or upgrade

## Planned Milestones

| # | Name | Description |
|---|---|---|
| 14 | Tokenizer visualization | Show token IDs and logprobs beside raw stream. |
| 15 | Session branching | Fork a conversation at a selected point. |
| 16 | Prompt diff tool | Compare trace logs by prompt, workflow, retrieved context, reasoning, and answer. |
| 17 | DPO export | Store rejected responses and export chosen/rejected preference pairs. |
| 18 | Training runner | Optional local script or workflow for running adapter training from exported data. |

## Completion Readiness

Karl's application loop is ready for completion testing. The remaining readiness
work is mostly validation and dataset depth:

- launch the app with the installed GGUF
- run a live prompt
- ingest a representative document
- test each workflow mode
- approve and teach a few examples
- validate and export the dataset
- run smoke tests and dry-run evals

The local curated dataset is not yet fine-tuning-ready because it has too few
examples. This is expected and is reported by `training/validate_dataset.py`.
