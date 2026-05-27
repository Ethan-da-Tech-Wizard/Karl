# Karl

Karl is a privacy-first, offline LLM Introspection Environment for prompt engineers.

It is a PyQt6 desktop app that runs a local DeepSeek-R1 GGUF model through
`llama-cpp-python`, streams the model's `<think>` reasoning into a separate pane,
logs every generation, and keeps the prompt/workflow logic editable in plain Python.

Philosophy: **UI for convenience, code for control, introspection for insight.**

## What Karl Does

- Runs local inference in-process with `llama-cpp-python`; no local server is required.
- Splits DeepSeek-style `<think>...</think>` output into a live reasoning pane and a final response pane.
- Writes structured JSONL traces to `data/logs/traces/`.
- Writes pre-parser raw streaming chunks to `data/logs/raw/*.tokens`.
- Lets users edit prompt construction and agentic-loop behavior in `core/`, with hot reload before generation or between loop iterations.
- Ingests local documents into a persistent FAISS vector index for retrieval-augmented prompting.
- Captures approved or corrected responses into a ShareGPT/Unsloth-ready training dataset.
- Provides workflow modes for general chat, document extraction, grounded answering, and code review.
- Includes a headless eval harness and a RAG benchmark path.

## Current App Surface

Karl has three top-level pages:

- **Chat:** saved sessions, knowledge-base ingestion, reasoning stream, final response, input controls, approve/teach buttons.
- **Configure:** workflow mode, system prompt, theme selection, RAG top-k, generation hyperparameters, reflect-loop controls, model upgrade prompt.
- **Tuning:** dataset stats, ShareGPT export, validation guidance, QLoRA notes, and links to hackable core files.

## Requirements

- Python 3.10+
- Microsoft C++ Build Tools on Windows
- A source-built `llama-cpp-python` install for the target CPU

On this machine, prebuilt `llama-cpp-python` wheels may fail with `Illegal Instruction (0xc000001d)`.
Build from source:

```powershell
$env:CMAKE_ARGS="-DGGML_NATIVE=ON"
pip install llama-cpp-python --no-binary llama-cpp-python
```

Install the rest:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Model

Download the default model:

```powershell
python download_test_model.py
```

This downloads DeepSeek-R1-Distill-Qwen-1.5B Q4_K_M into `data/models/`.

Karl also checks `data/active_model.json` at runtime. If that file is missing or points to a missing GGUF, Karl falls back to `data/models/deepseek-r1-1.5b.gguf`.

## Run

```powershell
python main.py
```

Useful checks:

```powershell
python smoke_test.py
python eval/run_eval.py --workflow code_review --dataset eval/datasets/code_review.jsonl --dry-run --no-save
python training/validate_dataset.py
python -m compileall -q app core eval training smoke_test.py
```

## Project Layout

```text
Karl/
  main.py                         App entry point
  engine_test.py                  Headless model/trace test
  raw_test.py                     Minimal raw llama-cpp test
  smoke_test.py                   Import-level and grader smoke test
  download_test_model.py          Default GGUF downloader
  requirements.txt
  AGENTS.md                       AI-agent handoff

  core/                           Hackable hot-reload layer
    interaction_loop.py           ChatML prompt builder
    prompt_templates.py           Named prompt templates
    workflows.py                  Workflow definitions
    agentic_loop.py               Reflect-loop stop/next-prompt logic
    cognitive_parser.py           Batch parser for headless tests
    hardware_scout.py             RAM/VRAM/storage profile

  app/
    engine/                       QThread workers and model loading
    ui/                           PyQt6 main window, themes, stylesheet
    utils/                        RAG, trace logging, sessions, training curation

  eval/                           Dataset-driven eval harness and graders
  training/                       Dataset validation and tuning guidance
  docs/                           Product, architecture, scope, risk docs
  data/                           Local runtime state; mostly gitignored
```

## Completion Status

Karl is a working local introspection workbench. The core completion path is now:

1. Run and test local generation.
2. Use RAG and workflow modes for real tasks.
3. Approve/teach outputs into `data/training/curated.jsonl`.
4. Validate and export training data.
5. Use evals and trace logs to decide whether to prompt, retrieve, tune, or upgrade the model.

Planned extensions remain tokenizer/logprob visualization, session branching, prompt diffing, and DPO export.
