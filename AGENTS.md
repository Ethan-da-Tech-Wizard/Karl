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

### 🔵 Next Milestones (Planned, No Code Written Yet)

In priority order:

#### Milestone 7: Raw Token Archive
Every character the model outputs, pre-parser, zero truncation — preserved even if
the dead man's switch kills the generation mid-thought.

- Add a third scrollable panel in the UI: "Raw Token Archive" (toggleable)
- In `llm_thread.py` and `agentic_thread.py`, write every raw token chunk to
  `data/logs/raw/<timestamp>.tokens` before it hits the parser
- Log file should be plain UTF-8, one chunk per line with a microsecond timestamp prefix
- The UI panel should auto-scroll like the existing thought/chat panels
- Toggle visibility via a checkbox in the config panel

#### Milestone 8: Hardware Scout & Model Registry
Karl detects available hardware and knows which model tier it should be running.

- Create `core/hardware_scout.py` using `psutil` and `GPUtil`
  - Returns: `{ "ram_gb": float, "vram_gb": float, "storage_gb": float }`
- Create `data/model_registry.json` (tiered model list)
  - Schema: `[{ "tier": int, "name": str, "min_ram_gb": float, "min_vram_gb": float,
    "min_storage_gb": float, "url": str, "filename": str, "n_ctx": int }]`
  - Pre-populate with DeepSeek-R1 tiers: 1.5B, 7B, 14B, 70B
- Create `app/engine/upgrade_manager.py`
  - On startup: compare hardware to registry, find highest eligible tier
  - If current model < eligible tier: show upgrade notification in UI
  - On approve: download GGUF → `ModelLoader.reset_instance()` → reload
  - Update `data/active_model.json` with current model info
  - Run `git commit + git push` to record the upgrade in history

#### Milestone 9: Auto-Loop Mode ("Karl Thinks Alone")
A single toggle that makes every generation automatically feed into the next —
no user clicking "Run Agentic Loop."

- Add "Auto-Loop" toggle (QCheckBox) to the config panel
- When ON: `LLMThread.generation_finished` signal triggers the agentic loop
  directly instead of re-enabling the input controls
- The user's only way to stop is the "■ Stop" button or the stop condition
  in `core/agentic_loop.py` returning `False`
- Visually: the Generate button changes label to "Send + Loop" when toggle is ON

#### Milestone 10: Self-Upgrade Git Push
When the Hardware Scout triggers a model upgrade, Karl commits and pushes automatically.

- `upgrade_manager.py` must call `subprocess.run(["git", "add", ...])` etc.
- Commit message format: `"upgrade(karl): self-upgraded to {tier_name} (Tier {n})"`
- The git remote must already be configured (it is: `origin = Ethan-da-Tech-Wizard/Karl`)
- Guard: only push if `git remote -v` returns a valid remote

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
- Both emit `new_thought_token(str)` and `new_chat_token(str)` PyQt signals.
- The UI connects these signals to cursor-insert methods on `QTextBrowser`.
- **Thread safety:** Never touch UI widgets directly from inside `run()`. Only emit signals.

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

### The Trace Logger
Every generation writes a JSONL entry to `data/logs/traces/trace_YYYY-MM-DD.jsonl`.
Fields: `timestamp`, `execution_time_seconds`, `hyperparameters`, `rag_context_used`,
`compiled_prompt`, `raw_output`, `parsed_thought`, `parsed_response`.

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

---

## How to Run

```powershell
# Activate venv
.\venv\Scripts\activate

# Run Karl
python main.py

# Run headless engine test (no UI)
python engine_test.py

# Download/re-download the model
python download_test_model.py
```

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
│   └── agentic_loop.py
├── app/
│   ├── engine/
│   │   ├── model_loader.py
│   │   ├── llm_thread.py
│   │   └── agentic_thread.py
│   ├── ui/
│   │   ├── main_window.py
│   │   └── styles/neutral.qss
│   └── utils/
│       ├── trace_logger.py
│       ├── memory_manager.py
│       └── rag_pipeline.py
├── data/                  ← gitignored (user data + large binaries)
│   ├── models/
│   ├── logs/
│   ├── sessions/
│   └── vector_db/
└── docs/
    ├── 01_problem_statement.md
    ├── 02_prd.md
    ├── 03_frd.md
    ├── 04_architecture.md
    ├── 05_scope_and_milestones.md
    ├── 06_repo_structure.md
    └── 07_risk_register.md
```
