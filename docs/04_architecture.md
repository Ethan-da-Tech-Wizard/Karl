# Karl Architecture

## High-Level Components

```text
PyQt6 MainWindow
  |
  |-- Chat page
  |     |-- MemoryManager
  |     |-- RAGPipeline
  |     |-- reasoning QTextBrowser
  |     |-- response QTextBrowser
  |
  |-- Configure page
  |     |-- workflow selector
  |     |-- system prompt editor
  |     |-- hyperparameter controls
  |     |-- reflect-loop controls
  |
  |-- Tuning page
        |-- dataset stats
        |-- export and validation guidance

Worker threads
  |
  |-- LLMThread
  |     |-- ModelLoader singleton
  |     |-- core.interaction_loop hot reload
  |     |-- streaming parser
  |     |-- TraceLogger
  |
  |-- AgenticThread
        |-- ModelLoader singleton
        |-- core.interaction_loop hot reload
        |-- core.agentic_loop hot reload
        |-- streaming parser
        |-- TraceLogger
```

## Data Flow: Single Generation

```text
User sends message
  |
  |-- MainWindow appends user turn to chat_history
  |-- RAGPipeline.retrieve() if top_k > 0
  |-- MainWindow renders system prompt
  |     |-- custom prompt: append formatted RAG context
  |     |-- workflow prompt: get_template(template, rag_context, schema, code)
  |-- LLMThread starts
        |
        |-- reload core.interaction_loop
        |-- ModelLoader.get_instance()
        |-- token-aware history trim
        |-- build_prompt(system_prompt, trimmed_history)
        |-- clamp generation tokens to context window
        |-- stream llama-cpp chunks
        |-- write raw .tokens archive
        |-- route chunks through thought/response parser
        |-- log JSONL trace
        |-- emit generation_finished
```

## Data Flow: Reflect Loop

```text
User clicks reflect
  |
  |-- MainWindow injects first loop prompt if last turn is assistant
  |-- AgenticThread starts
        |
        |-- reload core.interaction_loop
        |-- reload core.agentic_loop
        |-- loop:
              |-- trim history
              |-- build prompt
              |-- clamp generation tokens
              |-- stream and parse one generation
              |-- log iteration trace
              |-- append assistant response
              |-- emit iteration_finished
              |-- reload core.agentic_loop
              |-- should_continue(iteration, response)
              |-- build_next_prompt(response, iteration)
              |-- append next user prompt
        |-- emit loop_finished
```

## Hot-Reload Layer

`core/` is the user-editable control plane.

| File | Runtime role |
|---|---|
| `interaction_loop.py` | Converts system prompt plus chat history into final ChatML. |
| `agentic_loop.py` | Decides whether reflect mode continues and what user turn to inject next. |
| `prompt_templates.py` | Stores named workflow templates and placeholder replacement. |
| `workflows.py` | Stores workflow metadata used by the UI and eval harness. |
| `cognitive_parser.py` | Batch parser used by headless tests. |
| `hardware_scout.py` | Hardware profile for model upgrade suggestions. |

The engine threads reload `interaction_loop.py` before generation. The reflect
thread reloads `agentic_loop.py` between iterations.

## Model Loader

`app/engine/model_loader.py` owns a class-level singleton:

- default model: `data/models/deepseek-r1-1.5b.gguf`
- active model config: `data/active_model.json`
- context size: `n_ctx=4096`
- `reset_instance()` unloads the current singleton reference

## Context Window Strategy

Both `LLMThread` and `AgenticThread` use token counts from `llm.tokenize()`:

- cap very long individual messages
- preserve the first seed message when possible
- drop older middle turns until prompt fits
- reserve room for generation
- clamp `max_tokens` before calling llama-cpp

## RAG Storage

```text
data/vector_db/
  index.faiss
  metadata.json
```

Each metadata record contains:

- `text`
- `source_file`
- `chunk_id`
- `ingested_at`

## Logs and Artifacts

```text
data/logs/traces/trace_YYYY-MM-DD.jsonl
data/logs/raw/*.tokens
data/sessions/*.json
data/training/curated.jsonl
data/training/export_unsloth.jsonl
eval/results/*.jsonl
```

Most runtime artifacts are gitignored. `data/model_registry.json` is
source-controlled. `data/active_model.json` may be committed by the upgrade
manager when the model tier changes.

## Thread Safety

Worker threads must never mutate UI widgets directly. They emit PyQt signals,
and `MainWindow` slots update the visible widgets.
