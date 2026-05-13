# AGENTS.md — Handoff Document for AI Agents

> **This file is written for AI coding agents.**
> It is your primary context for continuing work on Karl.
> Read this before touching any code.

---

## What Is Karl?

Karl is a privacy-first, offline LLM **Introspection Environment** for Prompt Engineers.
It is a PyQt6 desktop application that runs DeepSeek-R1 locally via `llama-cpp-python`
(compiled from source, no pre-built binaries). Karl exposes the model's raw reasoning
process in real time, logs every generation immutably, and allows the user to manipulate
how the model thinks via hot-reloadable Python scripts.

**Philosophy:** "UI for convenience, Code for control, Introspection for insight."

---

## Current State (as of last commit)

### ✅ Milestones Completed

| # | Milestone | Key Files |
|---|-----------|-----------|
| 1 | Headless Introspection Engine | `engine_test.py`, `core/cognitive_parser.py`, `app/utils/trace_logger.py` |
| 2 | Dual-Pane Thought Stream UI | `app/ui/main_window.py`, `app/engine/llm_thread.py` |
| 3 | Memory & Context Management | `app/utils/memory_manager.py`, Force Thought button |
| 4 | Universal RAG Pipeline | `app/utils/rag_pipeline.py` — PDF, DOCX, TXT, PY, MD, CSV |
| 5 | Hackable Decoupling | `core/interaction_loop.py` + `importlib.reload()` on every generation |
| 6 | Agentic Loop | `core/agentic_loop.py`, `app/engine/agentic_thread.py`, UI buttons |
| 7 | Raw Token Archive | `new_raw_token` signal, `data/logs/raw/*.tokens` files, toggleable UI panel |
| 8 | Hardware Scout & Model Registry | `core/hardware_scout.py`, `data/model_registry.json`, `app/engine/upgrade_manager.py` |
| 9 | Auto-Loop Mode | "Auto-Loop" checkbox in UI — generation_finished → start_agentic_loop() |
| 10 | Self-Upgrade Git Push | `upgrade_manager.perform_upgrade()` → git commit + push on model upgrade |
| 11 | Training Data Curator | `app/utils/training_curator.py` — 👍/👎 rating row, correction dialog, Unsloth JSONL export |

### 🔵 Next Milestones (Planned, No Code Written Yet)

The core feature set is complete. These are enhancement ideas:

- **Tokenizer Visualization:** Display actual token IDs and probabilities alongside the raw stream.
  Requires `llama_cpp` logprobs support (set `logprobs=5` in the generation call).
- **Persistent Vector DB:** Currently the FAISS index is in-memory only — lost on restart.
  Serialize with `faiss.write_index()` / `faiss.read_index()` to `data/vector_db/index.faiss`
  and save `documents[]` as a companion JSON.
- **Session Branching:** Let the user fork a session at any point and explore alternate prompt paths.
- **Prompt Diff Tool:** Side-by-side comparison of two trace logs to see how a prompt change affected reasoning.

---

## Architecture — What You Need to Know

### The Extension Points (Hackable Core)
These three files are hot-reloaded on every generation via `importlib.reload()`.
The user is expected to edit them directly. Do NOT add complex dependencies here.

| File | What It Controls |
|------|-----------------|
| `core/interaction_loop.py` | Prompt string construction. `build_prompt(system, history) -> str` |
| `core/cognitive_parser.py` | Batch parsing of thought vs. response. Used by `engine_test.py` only. |
| `core/agentic_loop.py` | Stop condition and next-prompt injection for the agentic loop. |

### The Threading Model
- `LLMThread(QThread)` — single-shot generation. Lives in `app/engine/llm_thread.py`.
- `AgenticThread(QThread)` — autonomous loop. Lives in `app/engine/agentic_thread.py`.
- Both emit `new_thought_token(str)`, `new_chat_token(str)`, and `new_raw_token(str)` PyQt signals.
- The UI connects these signals to cursor-insert methods on `QTextBrowser`.
- **Thread safety:** Never touch UI widgets directly from inside `run()`. Only emit signals.

### The Raw Token Archive (M7)
Every raw token is emitted via `new_raw_token(str)` **before** the parser sees it.
Each generation also writes a timestamped `.tokens` file:
- Path: `data/logs/raw/<YYYYMMDD_HHMMSS_microseconds>.tokens`
- Format: one line per chunk — `{unix_float_timestamp}\t{raw_text}`
- The UI has a "Raw Token Archive" panel (hidden by default, toggle via checkbox).
- Even if a generation is killed mid-thought, everything written so far is on disk.

### The Streaming Parser (Critical — Read This)
Both threads contain an inline streaming state machine. It:
1. Accumulates tokens into a `buffer` string
2. Watches for `<think>` → sets `in_thought = True`, routes to `new_thought_token`
3. Watches for `</think>` → sets `in_thought = False`, routes to `new_chat_token`
4. Uses a suffix-guard to avoid flushing when a tag might be split across chunks:
   ```python
   if not any(buffer.endswith(s) for s in ["<", "</", "</t", ...]):
       self.new_thought_token.emit(buffer); buffer = ""
   ```
5. Always flushes the remainder after the generation loop ends.

### The Model Singleton
`ModelLoader` in `app/engine/model_loader.py` is a class-level singleton.
- `get_instance()` loads the model once, returns the same object forever.
- `reset_instance()` sets `_instance = None` — forces reload on next `get_instance()`.
- Current config: `n_ctx=4096`, `verbose=False`.
- Model path: `data/models/deepseek-r1-1.5b.gguf`

### Context Window Management (Agentic Only)
`AgenticThread._trim_history()` prevents context overflow in long loops:
- Walks history backwards, accumulates character count
- Budget = `(4096 - 1024) * 3` chars (~conservative token estimate)
- Always preserves the seed message (index 0)
- Emits a notice to the Thought Stream when trimming occurs

### The Hardware Scout & Upgrade Manager (M8 + M10)
On startup, `UpgradeCheckThread` (in `main_window.py`) runs off the UI thread:
1. `core/hardware_scout.py` → `get_hardware_profile()` returns `{ram_gb, vram_gb, storage_gb}`
2. `app/engine/upgrade_manager.py` → `check_for_upgrade()` compares profile to `data/model_registry.json`
3. If a higher tier is eligible, the UI shows a notification + "Upgrade Karl" button
4. On user approval: `perform_upgrade()` downloads GGUF, calls `ModelLoader.reset_instance()`,
   updates `data/active_model.json`, then runs `git commit + git push`

### Auto-Loop Mode (M9)
A `QCheckBox` "Auto-Loop" in the config panel.
- When ON: `handle_generation_finished()` calls `start_agentic_loop()` instead of re-enabling controls.
- The Send button label changes to "Send + Loop".
- Stop via the "■ Stop" button or the stop condition in `core/agentic_loop.py`.

### The Trace Logger
Every generation writes a JSONL entry to `data/logs/traces/trace_YYYY-MM-DD.jsonl`.
Fields: `timestamp`, `execution_time_seconds`, `hyperparameters`, `rag_context_used`,
`compiled_prompt`, `raw_output`, `parsed_thought`, `parsed_response`.

---

## The Training Data Curator (M11)

Karl records high-quality exchanges so the model can be fine-tuned on its own conversations.

**Workflow:**
1. Have a conversation in Karl.
2. Click **👍 Good** after a good response — it's saved to `data/training/curated.jsonl`.
3. Click **👎 Fix** after a bad one — a dialog opens so you can write the correct response. That corrected pair is saved instead.
4. Click **📦 Export for Unsloth** in the config panel to export a clean JSONL file ready for fine-tuning.

**What is Unsloth?**
Unsloth (`pip install unsloth`) is a fine-tuning framework that makes training LLMs 2–5× faster
with less VRAM. The exported JSONL is in HuggingFace chat format (`{"messages": [...]}`) and can
be fed directly to Unsloth's `SFTTrainer`. This is how you would eventually train a new version
of Karl's model on data collected from real sessions.

**To actually run fine-tuning (needs NVIDIA GPU, 6+ GB VRAM):**

```bash
pip install -r requirements-finetune.txt
python finetune.py
# or with explicit paths:
python finetune.py --input data/training/export_unsloth.jsonl --output data/models/karl-v2 --epochs 3
```

The script downloads the base model from HuggingFace (~3 GB, first run only),
trains a LoRA adapter on your examples, merges it back into the base weights,
and exports a `.gguf` file you can drop straight into `data/models/`.
It prints exact instructions for swapping the model in Karl when done.

**Files:**
- `data/training/curated.jsonl` — raw log with metadata (source, timestamp, messages)
- `data/training/export_unsloth.jsonl` — clean export (messages only), ready to train
- `app/utils/training_curator.py` — `save_example()`, `get_stats()`, `export_unsloth()`
- `finetune.py` — fine-tuning script
- `requirements-finetune.txt` — separate deps for fine-tuning (don't add to main requirements.txt)

---

## Recent Fixes (read before modifying these systems)

### Thinking always visible — prompt priming (latest)
DeepSeek R1 1.5B doesn't reliably generate `<think>` blocks on its own.
Fix: `core/interaction_loop.py` now ends the prompt with `<|im_start|>assistant\n<think>\n`,
forcing the model into a thought block from the first token.
Both `LLMThread` and `AgenticThread._run_single_generation()` now start with `in_thought = True`
to match. **Do not remove the `<think>` primer without also resetting `in_thought` back to `False`.**

### Agentic loop completion (latest)
The old stop signals (`[DONE]`, `[END]`, etc.) were exact-match strings the 1.5B model almost
never produced. Fixes applied to `core/agentic_loop.py`:
- `should_continue()` now does **case-insensitive substring matching** against a broad set of
  natural completion phrases (`"final answer:"`, `"in conclusion,"`, `"task complete"`, etc.)
- `build_next_prompt()` gets progressively more directive: iteration 1 asks for review, later
  iterations count down remaining steps and demand `FINAL ANSWER:` explicitly.
- `MAX_ITERATIONS` raised from 5 → 10.
- The default system prompt now instructs the model to prefix complete answers with `FINAL ANSWER:`.

---

## Key Gotchas

1. **`llama-cpp-python` must be compiled from source** for the user's Intel 12th Gen CPU.
   Pre-built wheels will throw `Illegal Instruction (0xc000001d)`.
   Compile command: `$env:CMAKE_ARGS="-DGGML_NATIVE=ON"; pip install llama-cpp-python --no-binary llama-cpp-python`

2. **`HF_TOKEN` warning on startup** — `sentence-transformers` tries to contact HuggingFace
   even in offline mode. This is a warning only; it does not break anything. To silence it,
   set `HF_HUB_OFFLINE=1` in the environment before launching.

3. **`get_sentence_embedding_dimension()` FutureWarning** — already fixed in `rag_pipeline.py`
   to use `get_embedding_dimension()`. If a future `sentence-transformers` update breaks this,
   check the `SentenceTransformer` API for the current method name.

4. **The model singleton holds state between agentic iterations.** The KV cache is NOT cleared
   between iterations by default. This is intentional — it makes the loop faster. If you need
   a clean slate, call `llm.reset()` before each generation (this will slow things down).

5. **Git remote is already configured.** Do not re-init the repo. The remote is:
   `https://github.com/Ethan-da-Tech-Wizard/Karl.git` on branch `main`.

6. **GPUtil is optional.** If no discrete GPU is detected, `vram_gb` returns `0.0` gracefully.
   The model registry tiers 1–2 require zero VRAM so the upgrade logic still works on CPU-only machines.

7. **`data/model_registry.json` is NOT gitignored.** It is source-controlled. Edit it to add
   new model tiers. `data/active_model.json` IS written at runtime and committed by the upgrade manager.

---

## How to Run

### First-time setup (or pulling onto a new machine, e.g. Antigrav)

```bash
# 1. Clone or pull the active branch
git clone https://github.com/Ethan-da-Tech-Wizard/Karl.git
cd Karl
git checkout claude/new-session-greeting-gHkb6   # or 'main' for stable
git pull origin claude/new-session-greeting-gHkb6

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
# NOTE: on Intel 12th Gen (or any CPU that needs native tuning), compile llama-cpp-python
# from source instead of using a pre-built wheel:
#   Windows: $env:CMAKE_ARGS="-DGGML_NATIVE=ON"; pip install llama-cpp-python --no-binary llama-cpp-python
#   Linux:   CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python --no-binary llama-cpp-python

# 4. Download the model (runs once, ~1 GB)
python download_test_model.py

# 5. Run Karl
python main.py
```

### Day-to-day commands

```powershell
# Activate venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# Run Karl
python main.py

# Run headless engine test (no UI)
python engine_test.py

# Re-download the model if missing
python download_test_model.py

# Check your hardware profile
python -c "from core.hardware_scout import get_hardware_profile; print(get_hardware_profile())"
```

### Pulling latest changes on an existing clone

```bash
git fetch origin
git checkout claude/new-session-greeting-gHkb6
git pull origin claude/new-session-greeting-gHkb6
pip install -r requirements.txt   # in case dependencies changed
python main.py
```

### Active development branch

`claude/new-session-greeting-gHkb6` — all current work lives here.
`main` is the last stable baseline.

---

## Repo Structure

```
Karl/
├── AGENTS.md              ← YOU ARE HERE
├── README.md              ← Human-readable overview
├── main.py                ← Entry point
├── engine_test.py         ← Headless inference test
├── download_test_model.py ← Model downloader
├── requirements.txt       ← pip dependencies
├── core/                  ← HACKABLE — user edits these
│   ├── interaction_loop.py
│   ├── cognitive_parser.py
│   ├── agentic_loop.py
│   └── hardware_scout.py
├── app/
│   ├── engine/
│   │   ├── model_loader.py
│   │   ├── llm_thread.py
│   │   ├── agentic_thread.py
│   │   └── upgrade_manager.py
│   ├── ui/
│   │   ├── main_window.py
│   │   └── styles/neutral.qss
│   └── utils/
│       ├── trace_logger.py
│       ├── memory_manager.py
│       └── rag_pipeline.py
├── data/                  ← partially gitignored
│   ├── model_registry.json   ← source controlled
│   ├── active_model.json     ← written at runtime, committed on upgrade
│   ├── models/               ← gitignored (large binaries)
│   ├── logs/                 ← gitignored
│   │   ├── traces/           ← JSONL trace logs
│   │   └── raw/              ← .tokens raw archive files
│   ├── sessions/             ← gitignored
│   └── vector_db/            ← gitignored
└── docs/
    ├── 01_problem_statement.md
    ├── 02_prd.md
    ├── 03_frd.md
    ├── 04_architecture.md
    ├── 05_scope_and_milestones.md
    ├── 06_repo_structure.md
    └── 07_risk_register.md
```
