# Karl — Prompt Engineering Workbench

**Karl** is a privacy-first, offline environment for professional prompt engineers.
It is not a chatbot wrapper. It is a lab.

The philosophy: **UI for convenience. Code for control. Measurement for trust.**

---

## What Makes Karl Different

| Capability | Karl | LM Studio / Ollama |
|---|---|---|
| Zero network calls | ✅ Enforced at startup | ❌ Telemetry / update checks |
| See the reasoning trace live | ✅ Dedicated Diagnostic Lane | ❌ Hidden |
| Every generation logged | ✅ Immutable JSONL trace | ❌ No audit trail |
| Prompt templates as code | ✅ `core/prompt_templates.py` | ❌ Typed into a box |
| Scored eval harness | ✅ Built-in, headless + UI | ❌ None |
| Side-by-side run diff | ✅ Prompt Diff Viewer | ❌ None |
| Token confidence heatmap | ✅ Per-token logprob colours | ❌ None |
| Fine-tuning data pipeline | ✅ Curator → Validator → Export | ❌ None |
| Hackable core loop | ✅ Hot-reloaded on every gen | ❌ Closed |

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- Windows: Microsoft C++ Build Tools (for llama-cpp-python)
- ~1.5 GB disk for the default model

### 2. Install

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

For GPU inference (optional):
```powershell
$env:CMAKE_ARGS="-DGGML_CUDA=ON"; pip install llama-cpp-python --no-binary llama-cpp-python
```

### 3. Download the default model

```powershell
python download_test_model.py
```

Downloads **DeepSeek-R1-Distill-Qwen-1.5B** (Q4_K_M, ~1 GB) into `data/models/`.
Drop any other GGUF file into the same folder and Karl will find it.

### 4. Run

```powershell
python main.py
```

---

## UI Layout

```
┌─────────────────┬──────────────────────────────────┬──────────────────┐
│  Sessions       │  🔬 Diagnostic Lane               │  System Prompt   │
│  ─────────────  │  (reasoning trace, live)          │  ─────────────── │
│  [session list] ├──────────────────────────────────┤  Workflow Mode   │
│  New  Save      │  💬 Final Response                │  ─────────────── │
│  ⑂Fork  📌Ver  │                                   │  Hyperparameters │
│  ─────────────  │  [input] [Force Thought] [Send]   │  ─────────────── │
│  Knowledge Base │  ─────────────────────────────── │  Logit Bias      │
│  (RAG files)    │  Workflow Report | Heatmap ☐      │  ─────────────── │
│  Ingest Doc     │  Token confidence: avg logprob —  │  Training Curator│
│                 │  🔍 Diff   📊 Eval                │                  │
│                 │  Rate: 👍  👎                     │                  │
└─────────────────┴──────────────────────────────────┴──────────────────┘
```

---

## Core Concepts

### Workflows
A **Workflow** links a prompt template, a RAG configuration, and an eval grader into a named mode.
Select the workflow from the dropdown — the system prompt, RAG top-k, and grader all update automatically.

| Workflow | Template | RAG | Grader |
|---|---|---|---|
| General Chat | `reasoning_minimal` | Optional | `keyword_hit` |
| Document Extractor | `json_extractor` | Required (k=5) | `json_valid` |
| Grounded Answer | `grounded_answer` | Required (k=5) | `groundedness` |
| Code Review | `code_review` | Off | `json_valid` |

Add your own in `core/workflows.py` — no restart needed.

### Prompt Templates
Named, versioned system prompts in `core/prompt_templates.py`.
Templates use `{rag_context}`, `{schema}`, `{code}` placeholders filled at generation time.
The file is hot-reloaded — edit and click Generate, changes apply immediately.

### Diagnostic Lane
The top center panel shows the model's raw `<think>` reasoning in real time, routed separately from the final response. This is where you see *why* the model answered the way it did.

### Workflow Report
After every generation, a one-line receipt appears below the input:
```
workflow=grounded_answer  template=grounded_answer  rag_chunks=3  sources=[doc.pdf]  latency=4.2s
```

### Token Confidence Heatmap
Check the **Confidence Heatmap** box to render the response with per-token colour coding.
Green = high confidence (logprob near 0). Red = uncertain (logprob below −5).
The average logprob also appears in the confidence bar above.

---

## RAG — Knowledge Base

1. Click **Ingest Document** — supports PDF, DOCX, TXT, PY, MD, CSV
2. The file is chunked, embedded locally via `sentence-transformers`, and saved to `data/vector_db/`
3. On next generation, relevant chunks are retrieved and injected into the system prompt
4. Enable **Contextual chunk headers** to prepend `[Source: file | Chunk N]` — lets the model cite sources

The FAISS index persists across sessions. Ingested documents survive restarts.

---

## Eval Harness

### Headless (CLI)
```bash
python eval/run_eval.py --dataset eval/datasets/grounded_answer.jsonl --workflow grounded_answer
python eval/run_eval.py --dataset eval/datasets/document_extractor.jsonl --workflow document_extractor --dry-run
```

### From the UI
Click **📊 Eval** → select a dataset and workflow → click **▶ Run Eval**.
Results stream live and are saved to `eval/results/`. The history table shows pass-rate trends across runs.

### Graders
| Grader | Use case |
|---|---|
| `exact_match` | Short deterministic answers |
| `json_valid` | JSON output with required keys |
| `keyword_hit` | Keyword presence check |
| `groundedness` | Response grounded in retrieved context |
| `not_in_context` | Correct refusal when evidence is absent |

### Adding eval cases
```json
{"id": "case_001", "prompt": "...", "context": "...", "grader": "json_valid", "schema_keys": ["title", "date"]}
```

---

## Prompt Diff Viewer

Click **🔍 Prompt Diff** to compare any two trace entries side by side.
Pick two runs from the dropdowns. Click **Highlight Differences** to colour differing response lines red.
All traces live in `data/logs/traces/` as JSONL.

---

## Session Management

| Action | Description |
|---|---|
| **New** | Clear history, start fresh |
| **Save** | Persist current session to `data/sessions/` |
| **⑂ Fork** | Clone to a new branch file — diverge without losing the original |
| **📌 Save Version** | Snapshot with a human-readable tag (e.g. `v2-with-rag`) |

Sessions are sorted newest-first. Double-click any session to load it.

---

## Logit Bias Editor

In the config panel, enter token-level biases — one per line:
```
json: +3.0
sorry: -5.0
however: -2.0
```
Karl tokenises each word and passes `logit_bias` directly to the inference engine.
Bias persists across auto-continued (truncated) responses.

---

## Training Data Pipeline

### Step 1 — Curate
After each generation, rate with 👍 (good) or 👎 Fix (opens correction editor).
Every correction stores the original response as the **rejected** sample automatically — no extra steps for DPO.

### Step 2 — Validate
```bash
python training/validate_dataset.py
```
Checks: schema, minimum count, token length, source balance, duplicates.

### Step 3 — Export
- **📦 Export SFT** — Unsloth / HuggingFace ShareGPT format
- **⚖️ Export DPO Pairs** — TRL DPOTrainer chosen/rejected format

### Step 4 — Train
See `training/qlora_config_template.yaml` for a QLoRA config tuned for 1.5B models on CPU/low-VRAM.
See `training/WHEN_TO_TUNE.md` for the decision guide: **prompt → RAG → SFT → DPO**.

### Step 5 — Reload
Drop the merged GGUF into `data/models/` and restart Karl.

---

## Agentic Loop

Karl can run autonomously — feeding its own output back as the next input.

- **Auto-Loop** — each response automatically seeds the next generation
- **▶ Run Agentic Loop** — start a controlled autonomous loop
- **■ Stop** — halt at the next iteration boundary

Edit `core/agentic_loop.py` to define the stop condition and next-prompt injection logic.
It is hot-reloaded on every iteration.

---

## Hackable Core

Every file in `core/` is hot-reloaded on each generation — no restart required.

| File | What it controls |
|---|---|
| `core/interaction_loop.py` | Prompt construction and ChatML formatting |
| `core/cognitive_parser.py` | Thought/response splitting logic |
| `core/prompt_templates.py` | Named system prompt template registry |
| `core/workflows.py` | Workflow → template → RAG → grader mappings |
| `core/agentic_loop.py` | Autonomous loop stop condition and next-prompt logic |

---

## Project Structure

```
Karl/
├── main.py                        # Entry point — enforces telemetry isolation first
├── requirements.txt
├── smoke_test.py                  # Fast bridge validation (no model needed)
│
├── core/                          # THE HACKABLE LAYER — hot-reloaded every generation
│   ├── interaction_loop.py
│   ├── cognitive_parser.py
│   ├── prompt_templates.py
│   ├── workflows.py
│   ├── agentic_loop.py
│   └── hardware_scout.py
│
├── app/
│   ├── engine/
│   │   ├── model_loader.py        # Singleton llama-cpp-python instance
│   │   ├── llm_thread.py          # Streaming, logprobs, trace logging
│   │   ├── agentic_thread.py      # Autonomous loop execution
│   │   └── upgrade_manager.py     # Hardware-aware model selection
│   ├── ui/
│   │   ├── main_window.py         # All panels, signals, and handlers
│   │   ├── diff_viewer.py         # Prompt Diff Viewer (M17)
│   │   ├── eval_dashboard.py      # Eval history + live runner (M18/M19)
│   │   └── styles/neutral.qss
│   └── utils/
│       ├── memory_manager.py      # Session save / load / fork / version
│       ├── rag_pipeline.py        # FAISS + sentence-transformers
│       ├── trace_logger.py        # Immutable JSONL generation logs
│       └── training_curator.py    # SFT + DPO dataset collection and export
│
├── eval/
│   ├── graders.py                 # Pure scoring functions
│   ├── harness.py                 # Headless eval runner
│   ├── run_eval.py                # CLI entry point
│   ├── benchmark_rag.py           # RAG retrieval quality benchmark
│   └── datasets/                  # Seed eval cases (JSONL)
│
├── training/
│   ├── validate_dataset.py        # Pre-flight dataset validator
│   ├── qlora_config_template.yaml # QLoRA config for 1.5B models
│   └── WHEN_TO_TUNE.md            # Decision guide: prompt vs RAG vs SFT vs DPO
│
└── data/                          # Local state — gitignored
    ├── models/                    # GGUF files
    ├── vector_db/                 # Persistent FAISS index
    ├── logs/traces/               # Per-day JSONL generation traces
    ├── sessions/                  # Saved conversations
    └── training/                  # Curated dataset and exports
```

---

## Milestone Tracker

| # | Milestone | Status |
|---|---|---|
| M1 | Headless Introspection Engine | ✅ Complete |
| M2 | Dual-Pane Thought Stream UI | ✅ Complete |
| M3 | Memory & Context Management | ✅ Complete |
| M4 | Universal RAG Pipeline | ✅ Complete |
| M5 | Hackable Core (hot-reload) | ✅ Complete |
| M6 | Agentic Loop | ✅ Complete |
| M7 | Raw Token Archive | ✅ Complete |
| M8 | Hardware-Aware Upgrade Manager | ✅ Complete |
| M9 | Auto-Loop & Agentic Controls | ✅ Complete |
| M10 | Self-Upgrade via Model Registry | ✅ Complete |
| M11 | Training Data Curator | ✅ Complete |
| M12 | Prompt Template Registry | ✅ Complete |
| M13 | Workflow Engine | ✅ Complete |
| M14 | Eval Harness & Graders | ✅ Complete |
| M15 | Hardened RAG (persistence, metadata, retrieval metrics) | ✅ Complete |
| M16 | Session Branching (Fork / Save Version) | ✅ Complete |
| M17 | Prompt Diff Viewer | ✅ Complete |
| M18 | Eval Results Dashboard | ✅ Complete |
| M19 | Live Eval Runner (UI) | ✅ Complete |
| M20 | Logit Bias Editor | ✅ Complete |
| M21 | Token Confidence Heatmap | ✅ Complete |
