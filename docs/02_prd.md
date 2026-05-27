# Product Requirements Document - Karl

## Product Vision

Karl is a local LLM introspection environment for prompt engineers.

It should feel like a polished desktop app while preserving the control of a
plain Python workbench. The user should be able to inspect what the model was
asked, what it retrieved, what it reasoned, what it answered, and how that
output should feed future evals or tuning.

Philosophy: **UI for convenience, code for control, introspection for insight.**

## Target User

- Prompt engineers
- AI solution architects
- Local model researchers
- Developers building RAG and evaluation workflows

The user is expected to be comfortable with Python, local models, prompts,
datasets, and the idea of editing files under `core/`.

## Product Constraints

### Privacy

- Inference must run locally in the Karl process.
- No localhost model server is required.
- No outbound network calls should occur during ordinary inference.
- Allowed network operations are explicit model download and optional git push during model upgrade.

### Inspectability

Karl must record enough information to reproduce and compare runs:

- timestamp
- workflow
- template
- hyperparameters
- retrieved RAG context
- compiled prompt
- raw output
- parsed thought
- parsed response
- latency

### Hackability

The user must be able to modify key behavior without restarting the app:

- `core/interaction_loop.py`
- `core/agentic_loop.py`
- prompt templates and workflows through `core/prompt_templates.py` and `core/workflows.py`

### Thread Safety

All LLM work must run outside the UI thread. Worker threads communicate through
PyQt signals only.

## Implemented Feature Set

### Chat and Introspection

- Chat page with saved sessions, RAG file ingestion, reasoning stream, response stream, and prompt input.
- Streaming parser separates `<think>` content from final response text.
- Reasoning pane can be hidden or shown.
- Stop button can terminate a single generation or request reflect-loop stop.

### Trace and Raw Token Logging

- Structured JSONL traces are written to `data/logs/traces/`.
- Raw pre-parser chunks are written to `data/logs/raw/*.tokens`.
- Raw chunks are archived on disk; they are not currently shown in a live UI panel.

### RAG

Supported file types:

- PDF
- DOCX
- TXT
- PY
- MD
- CSV
- XLSX
- XLS

RAG implementation:

- `all-MiniLM-L6-v2` sentence-transformer embeddings
- FAISS flat L2 index
- persistent `data/vector_db/index.faiss`
- persistent `data/vector_db/metadata.json`
- semantic over-fetch plus keyword reranking
- optional contextual headers
- retrieval eval metrics

### Workflow Modes

Implemented workflows:

| Workflow | Template | RAG | Output |
|---|---|---|---|
| `general_chat` | `reasoning_minimal` | Optional top-3 | Free text |
| `document_extractor` | `json_extractor` | Required top-5 by convention | JSON object |
| `grounded_answer` | `grounded_answer` | Required top-5 by convention | Grounded answer or NOT IN CONTEXT |
| `code_review` | `code_review` | Off | JSON array |

The UI renders selected workflow templates through `get_template()` so
placeholders such as `{rag_context}`, `{schema}`, and `{code}` are filled before
generation.

### Agentic Reflect Loop

- Manual `reflect` button starts the loop after a seed conversation exists.
- `halt loop` requests stop.
- `core/agentic_loop.py` controls `should_continue()` and `build_next_prompt()`.
- Default hard cap is `MAX_ITERATIONS = 20`.
- Completion signals include `FINAL ANSWER:`, `[DONE]`, `[END]`, and `[STOP]`.
- Automatic post-generation looping is intentionally disabled; reflect is opt-in.

### Training Data Curator

- `approve` saves the current prompt and response as an approved example.
- `teach` opens a correction dialog and saves the corrected answer.
- Stored path: `data/training/curated.jsonl`.
- Export path: `data/training/export_unsloth.jsonl`.
- Export format: HuggingFace/ShareGPT-style `{"messages": [...]}`.
- Tuning page shows dataset stats and export controls.

### Eval Harness

Implemented graders:

- `exact_match`
- `json_valid`
- `keyword_hit`
- `groundedness`
- `not_in_context`

CLI:

```powershell
python eval/run_eval.py --workflow code_review --dataset eval/datasets/code_review.jsonl
python eval/run_eval.py --workflow code_review --dataset eval/datasets/code_review.jsonl --dry-run --no-save
```

### Model Upgrade

- Startup hardware check reads RAM, VRAM, and free storage.
- Upgrade manager compares hardware against `data/model_registry.json`.
- If a better tier is eligible, the Configure page can show an upgrade prompt.
- User-approved upgrade downloads a GGUF, resets the model singleton, writes `data/active_model.json`, commits it, and pushes.

## Out of Scope for Current Completion

- Live raw-token UI panel.
- Token ID/logprob visualization.
- Session branching.
- Prompt diff UI.
- DPO export.
- Full training run automation.

## Completion Criteria

Karl is completion-ready when:

1. The app launches with the local model installed.
2. Chat generation streams thought and response correctly.
3. RAG ingestion and retrieval work for representative files.
4. Workflow templates render without unresolved placeholders.
5. Traces include workflow and template metadata.
6. Training data can be approved, corrected, validated, and exported.
7. Smoke tests and dry-run evals pass.
8. Documentation matches the actual code surface.
