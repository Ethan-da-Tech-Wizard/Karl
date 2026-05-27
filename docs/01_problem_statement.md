# Problem Statement: The Prompt Engineering Bottleneck

## Executive Summary

Prompt engineers and AI application developers need a way to inspect, test,
and refine local LLM behavior without surrendering prompts, documents, or
trace data to external services.

Existing tools often force a tradeoff:

- Cloud APIs are powerful but move private prompts and documents off-machine.
- Local daemons are convenient but hide prompt assembly, parsing, retrieval, and telemetry details.
- Raw Python scripts are controllable but slow down interactive exploration.

Karl addresses that gap with an offline desktop workbench that combines a
usable PyQt6 interface with editable Python control points and full trace logs.

## Current Tooling Gaps

### Privacy and Isolation

Prompt engineering often involves proprietary code, contracts, policies,
incident reports, internal datasets, or experimental prompts. Cloud workflows
can be unacceptable when data must stay local.

Karl runs inference in-process through `llama-cpp-python`. It does not require
a localhost model server. Inference itself is offline. Network access is limited
to explicit user-triggered actions such as model download or model-upgrade git
push.

### Prompt and Reasoning Opacity

Prompt behavior is hard to improve when the tool hides the compiled prompt,
the workflow template, the retrieved chunks, and the model's reasoning markers.

Karl exposes the important pieces:

- The compiled ChatML prompt is logged.
- Retrieved RAG chunks are logged.
- `<think>...</think>` reasoning is streamed separately from final response text.
- Raw streaming chunks are archived before parsing.

### Slow Experiment Loops

Professional prompt work usually bounces between GUI chat tools, scripts,
logs, vector database experiments, and spreadsheets of eval results.

Karl keeps the loop inside one local project:

1. Ingest documents.
2. Select or edit a workflow.
3. Generate and inspect reasoning.
4. Save traces.
5. Approve or correct outputs into a training dataset.
6. Run evals to decide whether to prompt, retrieve, tune, or upgrade.

## Proposed Solution

Karl is an offline LLM introspection workbench for technical users.

It provides:

- A PyQt6 GUI with Chat, Configure, and Tuning pages.
- Local DeepSeek-R1 GGUF inference through `llama-cpp-python`.
- A reasoning pane that receives streamed `<think>` content.
- A response pane for final answer content.
- A hackable `core/` layer that is hot-reloaded during generation.
- Persistent FAISS-based RAG over local files.
- Immutable JSONL trace logs and raw token archives.
- Dataset curation and ShareGPT/Unsloth export.
- Eval harnesses for output and retrieval quality.

## Product Position

Karl is not meant to be a general consumer chat app. It is a prompt engineering
instrument: local, inspectable, editable, and traceable.
