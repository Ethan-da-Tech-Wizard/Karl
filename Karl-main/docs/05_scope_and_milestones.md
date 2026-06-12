# Karl — Scope Lock and Defined Milestones

## Scope Lock Statement (Version 1.1 — The Introspection Pivot)
**Karl** will implement a self-contained, offline LLM graphical interface with an **explicit focus on introspective logging and cognitive manipulation**. It will separate thought traces from final outputs and log all generation variables to disk.

---

## Defined Milestones & Success Criteria

### Milestone 1: The Headless Introspection Engine
**Goal:** Prove the engine works and implement the raw logging infrastructure before any UI exists.
- **Tasks:**
  - Build `engine_test.py` (Completed).
  - Create the `TraceLogger` class that takes a prompt, hyperparams, and response, and writes a highly structured `.jsonl` file to disk.
  - Implement a basic `cognitive_parser.py` to extract `<think>` blocks from raw text.
- **Success Criteria:** A Python script generates text, successfully splits the reasoning from the answer in the terminal, and writes a perfectly formatted log file to `data/logs/`.

### Milestone 2: The Dual-Pane UI
**Goal:** Build the PyQt6 framework that supports seeing the thoughts in real-time.
- **Tasks:**
  - Build `main_window.py` with the dark neutral theme.
  - Implement the UI splitter with **three** sections: Chat, Thought Stream, and Config.
  - Implement the `QThread` that uses `cognitive_parser` to stream text to two different UI windows simultaneously.
- **Success Criteria:** User types a prompt, and the Thought Window populates with reasoning while the Chat window populates with the final answer.

### Milestone 3: Memory and Context Management (Completed)
**Goal:** Implement session persistence and context window math.
- **Tasks:**
  - Serialize/deserialize the `chat_history`.
  - Implement the System Prompt UI element.
  - Implement a "Force Thought" UI button to inject fake reasoning into the context.

### Milestone 4: The Universal RAG Pipeline (Completed)
**Goal:** Ingest documents and retrieve them locally.
- **Tasks:**
  - Integrate `sentence-transformers` and `faiss-cpu`.
  - Ingest PDF, DOCX, TXT files via UI.
  - Ensure retrieved RAG chunks are saved explicitly into the Trace Logger for that specific generation.

### Milestone 5: The "Hackable" Decoupling (Completed)
**Goal:** Finalize the "Code exposed" requirement.
- **Tasks:**
  - Abstract all conversational loop logic into `core/interaction_loop.py`.
  - Implement `importlib.reload()` so users can modify the loop on the fly without restarting the app.

### Milestone 6: The Agentic Loop (Completed)
**Goal:** Enable Karl to run autonomously, feeding its own output back in and iterating without user input.
- **Tasks:**
  - Build `core/agentic_loop.py` — the hackable stop condition and next-prompt injection logic.
  - Build `app/engine/agentic_thread.py` — a `QThread` that loops generation, hot-reloads the agentic core on each iteration, and emits per-iteration signals.
  - Wire a **"Run Agentic Loop"** button and **"Stop"** button into the UI.
  - Track iteration count in the UI status bar.
- **Success Criteria:** User sends an initial prompt, clicks "Run Agentic Loop", and Karl iterates autonomously — streaming each thought and response in the live panels — until the stop condition in `core/agentic_loop.py` is met.
