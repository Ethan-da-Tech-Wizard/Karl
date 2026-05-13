# Karl

**Karl** is a privacy-first, offline LLM Introspection Environment for Prompt Engineers.

It is not LM Studio. It is not Ollama. It is a surgical instrument.

---

## What Karl Does Differently

- **Zero network calls.** The engine runs as a C-extension inside your Python process. No localhost servers. No telemetry.
- **You see exactly how it thinks.** Karl splits DeepSeek-R1's `<think>` reasoning blocks into a dedicated live stream panel, separate from the final response.
- **Every generation is logged.** An immutable JSONL trace file captures the exact prompt, hyperparameters, thought process, and response for every single generation. Your experimental audit trail is guaranteed.
- **The core is yours to hack.** `core/interaction_loop.py` and `core/cognitive_parser.py` are the live Python scripts that control prompt construction and thought parsing. Karl hot-reloads them on every generation — change the file and click Generate, no restart needed.
- **RAG on any file.** Drop a PDF, Word doc, Python file, markdown, or CSV into Karl's Knowledge Base. It chunks, embeds, and retrieves locally via `sentence-transformers` + `faiss-cpu`.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Microsoft C++ Build Tools (required to compile `llama-cpp-python` from source)

### 2. Install
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** `llama-cpp-python` must be compiled from source for your CPU architecture:
> ```powershell
> $env:CMAKE_ARGS="-DGGML_NATIVE=ON"; pip install llama-cpp-python --no-binary llama-cpp-python
> ```

### 3. Download Model
```powershell
python download_test_model.py
```
This downloads **DeepSeek-R1-Distill-Qwen-1.5B** (Q4_K_M, ~1GB) into `data/models/`.

### 4. Run
```powershell
python main.py
```

---

## Project Structure
```
├── core/               # THE HACKABLE LAYER — edit these freely
│   ├── interaction_loop.py   # Prompt construction logic
│   └── cognitive_parser.py  # Thought/response parsing
├── app/
│   ├── engine/         # LLM loading & threaded execution
│   └── ui/             # PyQt6 interface
│   └── utils/          # Logger, Memory Manager, RAG Pipeline
├── data/
│   ├── models/         # GGUF model files (gitignored)
│   ├── logs/           # JSONL trace logs (gitignored)
│   └── sessions/       # Saved conversations (gitignored)
├── docs/               # Architecture, PRD, FRD, Risk Register
├── engine_test.py      # Headless engine validation script
└── main.py             # Entry point
```

---

## Milestones Completed
- ✅ Milestone 1: Headless Introspection Engine
- ✅ Milestone 2: Dual-Pane Thought Stream UI
- ✅ Milestone 3: Memory & Context Management
- ✅ Milestone 4: Universal RAG Pipeline
- ✅ Milestone 5: Hackable Decoupling
