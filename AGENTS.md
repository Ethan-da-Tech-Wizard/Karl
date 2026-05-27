# AGENTS.md - Handoff Document for AI Coding Agents

Read this before touching code in Karl.

## What Karl Is

Karl is a privacy-first, offline LLM Introspection Environment for prompt engineers.
It is a PyQt6 desktop application that runs DeepSeek-R1 locally through
`llama-cpp-python`, exposes the model's `<think>` stream in real time, logs
every generation, and lets the user steer the prompt and loop logic through
hot-reloadable Python files.

Philosophy: **UI for convenience, code for control, introspection for insight.**

## Current Product State

The app currently has three pages:

- **Chat:** saved sessions, knowledge-base ingestion, reasoning pane, response pane, input row, stop/send controls, approve/teach training buttons.
- **Configure:** workflow selector, system prompt editor, theme picker, RAG top-k, temperature/top-p/max-tokens, manual reflect-loop controls, model upgrade prompt.
- **Tuning:** dataset stats, ShareGPT export button, validation guidance, QLoRA notes, and links to hackable core files.

Important clarification: raw token chunks are archived to disk through the
`new_raw_token` signal and `.tokens` files. The current UI does not show a live
raw-token panel.

## Milestones Implemented

| # | Milestone | Key files |
|---|---|---|
| 1 | Headless introspection engine | `engine_test.py`, `core/cognitive_parser.py`, `app/utils/trace_logger.py` |
| 2 | Dual-pane thought stream UI | `app/ui/main_window.py`, `app/engine/llm_thread.py` |
| 3 | Session and context management | `app/utils/memory_manager.py`, token-accurate trim logic in engine threads |
| 4 | Universal RAG pipeline | `app/utils/rag_pipeline.py` |
| 5 | Hackable decoupling | `core/interaction_loop.py`, `importlib.reload()` |
| 6 | Manual agentic reflect loop | `core/agentic_loop.py`, `app/engine/agentic_thread.py` |
| 7 | Raw token archive | `new_raw_token`, `data/logs/raw/*.tokens` |
| 8 | Hardware scout and model registry | `core/hardware_scout.py`, `data/model_registry.json`, `app/engine/upgrade_manager.py` |
| 9 | Opt-in reflect mode | Configure page `reflect` and `halt loop` buttons |
| 10 | Self-upgrade git record | `app/engine/upgrade_manager.py` |
| 11 | Training data curator | `app/utils/training_curator.py`, approve/teach UI |
| 12 | Eval harness | `eval/harness.py`, `eval/graders.py`, `eval/run_eval.py` |
| 13 | Workflow modes | `core/prompt_templates.py`, `core/workflows.py` |
| 14 | RAG hardening | persistent FAISS index, metadata, hybrid rerank, eval metrics |
| 15 | Training path formalization | `training/validate_dataset.py`, `training/qlora_config_template.yaml`, `training/WHEN_TO_TUNE.md` |

## Planned Next Milestones

- **Tokenizer visualization:** show token IDs and log probabilities next to raw stream. Requires llama-cpp logprobs support.
- **Session branching:** fork a saved conversation at any turn.
- **Prompt diff tool:** compare trace logs by workflow/template/prompt/output.
- **DPO export:** store rejected response text alongside corrected response to export chosen/rejected pairs.

## Hackable Core

These files are intentionally simple and should stay dependency-light:

| File | Purpose |
|---|---|
| `core/interaction_loop.py` | Builds the final ChatML prompt: `build_prompt(system, history) -> str`. Hot-reloaded before generation. |
| `core/prompt_templates.py` | Stores named system prompt templates and placeholder rendering. |
| `core/workflows.py` | Stores workflow definitions: template, RAG top-k, schema, grader. |
| `core/agentic_loop.py` | Controls reflect-loop stop condition and next-prompt injection. Hot-reloaded between iterations. |
| `core/cognitive_parser.py` | Batch parsing for `engine_test.py`; live UI parsing is inline in the engine threads. |
| `core/hardware_scout.py` | Hardware profile for upgrade eligibility. |

Do not add complex dependencies to `core/` unless the user explicitly asks.

## Threading Model

- `LLMThread(QThread)` in `app/engine/llm_thread.py` handles one generation.
- `AgenticThread(QThread)` in `app/engine/agentic_thread.py` handles autonomous reflect iterations.
- Both emit `new_thought_token(str)`, `new_chat_token(str)`, and `new_raw_token(str)`.
- The UI updates widgets only from signal handlers in `MainWindow`.

Thread safety rule: never touch UI widgets directly from inside `run()`.

## Streaming Parser

Both generation threads use an inline state machine:

1. Append each streaming chunk to a buffer.
2. Detect `<think>` and route subsequent text to the reasoning pane.
3. Detect `</think>` and route subsequent text to the response pane.
4. Use suffix guards so split tags such as `<thi` or `</th` are not flushed early.
5. Flush any remaining buffer after streaming ends.

The prompt builder pre-seeds `<think>\n` at the assistant turn so DeepSeek-R1 starts in reasoning mode.

## Model Loading

`ModelLoader` is a class-level singleton in `app/engine/model_loader.py`.

- Reads `data/active_model.json` when present.
- Falls back to `data/models/deepseek-r1-1.5b.gguf`.
- Uses `n_ctx=4096`, `verbose=False`.
- `reset_instance()` forces reload on next `get_instance()`.

`llama-cpp-python` must be compiled from source on this Intel 12th Gen target:

```powershell
$env:CMAKE_ARGS="-DGGML_NATIVE=ON"
pip install llama-cpp-python --no-binary llama-cpp-python
```

## Context Management

Both engine threads use token-aware prompt trimming with `llm.tokenize()`.
They preserve the first seed message when possible, drop older middle turns,
cap long individual messages, and clamp generation tokens so prompt plus output
fits the 4096-token context window.

## RAG

`RAGPipeline` supports PDF, DOCX, TXT, PY, MD, CSV, XLSX, and XLS. It stores a
persistent FAISS index and JSON metadata in `data/vector_db/`.

Retrieval uses semantic over-fetch plus keyword reranking so exact strings such
as IDs and table values have a better chance of surfacing.

## Workflows

Workflow definitions live in `core/workflows.py`:

- `general_chat`
- `document_extractor`
- `grounded_answer`
- `code_review`

The UI renders selected workflow templates through `core.prompt_templates.get_template()`
and passes workflow/template names into trace logs.

## Trace and Raw Logs

Trace files:

```text
data/logs/traces/trace_YYYY-MM-DD.jsonl
```

Each record includes timestamp, execution time, workflow, template, hyperparameters,
RAG context, compiled prompt, raw output, parsed thought, and parsed response.

Raw token files:

```text
data/logs/raw/<timestamp>.tokens
data/logs/raw/agentic_<timestamp>_iter<N>.tokens
```

Each line is `{unix_float_timestamp}\t{raw_text}`.

## Training Path

Approve/teach buttons save examples through `app/utils/training_curator.py`:

- `source="approved"` for approve.
- `source="corrected"` for teach.
- Dataset path: `data/training/curated.jsonl`.
- Export path: `data/training/export_unsloth.jsonl`.
- Export format: `{"messages": [...]}`.

Validate before tuning:

```powershell
python training/validate_dataset.py
```

The validator intentionally exits nonzero with too few examples. At the time of
this handoff, the local dataset has only a couple examples and is not tuning-ready.

## Eval Harness

Graders currently implemented:

- `exact_match`
- `json_valid`
- `keyword_hit`
- `groundedness`
- `not_in_context`

Useful commands:

```powershell
python smoke_test.py
python eval/run_eval.py --workflow code_review --dataset eval/datasets/code_review.jsonl --dry-run --no-save
python eval/benchmark_rag.py
```

## Git and Runtime State

The remote is already configured:

```text
https://github.com/Ethan-da-Tech-Wizard/Karl.git
```

Do not reinitialize the repo.

Source-controlled:

- `data/model_registry.json`
- application code
- docs
- eval datasets
- training templates

Runtime/user state:

- `data/models/`
- `data/logs/`
- `data/sessions/`
- `data/training/`
- `data/vector_db/`
- `data/active_theme.json`

`data/active_model.json` is written by the upgrade manager and intentionally may
be committed when a model upgrade is performed.

## Known Completion Gaps

- No live raw-token panel in the current UI; only disk archive exists.
- DPO export is not implemented because rejected responses are not stored.
- Prompt diffing is not implemented, but trace metadata now supports it.
- Session branching is not implemented.
- Full training readiness requires a larger curated dataset.
