# Karl

**Karl** is a privacy-first, offline LLM Introspection Environment for Prompt Engineers.

It is not LM Studio. It is not Ollama. It is a surgical instrument.

---

## What Karl Does Differently

- **Zero remote inference calls.** The model runs as a C-extension inside your Python process. The optional VS Code bridge uses localhost only; there is no telemetry and no cloud model server.
- **You see exactly how it thinks.** Karl splits DeepSeek-R1's `<think>` reasoning blocks into a dedicated live stream panel, separate from the final response.
- **Session Branching.** Interactive conversation tree view allowing you to branch off any message to explore alternate prompts and generation paths.
- **Every generation is logged.** An immutable JSONL trace file captures the exact prompt, hyperparameters, thought process, and response for every single generation. Your experimental audit trail is guaranteed.
- **The core is yours to hack.** `core/interaction_loop.py` and `core/cognitive_parser.py` are the live Python scripts that control prompt construction and thought parsing. Karl hot-reloads them on every generation — change the file and click Generate, no restart needed.
- **RAG on any file.** Drop a PDF, Word doc, Python file, markdown, or CSV into Karl's Knowledge Base. It chunks, embeds, and retrieves locally via `sentence-transformers` + `faiss-cpu`.

---

## Getting Started (Arch Linux / Linux)

### 1. Prerequisites
- Python 3.10+
- C/C++ compiler toolchain (gcc, cmake, make)
- NVIDIA GPU with CUDA drivers (optional, for LoRA training/GPU inference)

On Arch Linux, install base build tools and system headers:
```bash
sudo pacman -S base-devel cmake python
```

### 2. Install Virtual Environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Compile `llama-cpp-python` from source for native CPU optimizations:
```bash
CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python --no-binary llama-cpp-python
```

### 3. GPU Acceleration (CUDA / LoRA Training Setup)
If you have an NVIDIA graphics card, run the provided GPU setup script to compile CUDA drivers, install CUDA PyTorch, and set up PEFT/TRL training tools in your virtual environment:
```bash
# Switching graphics manager to hybrid/nvidia mode may be required beforehand
sudo ./setup_gpu.sh
```

### 4. Download Model
```bash
python download_test_model.py
```
This downloads **DeepSeek-R1-Distill-Qwen-1.5B** (Q4_K_M, ~1GB) into `data/models/`.

### 5. Run Karl
```bash
source venv/bin/activate
python main.py
```

---

## Docker CUDA Deployment

Karl can also run as a CUDA-backed containerized backend for editor integrations.
This avoids host Python, CUDA Toolkit, GCC, and CMake drift while still using the
host NVIDIA driver through NVIDIA Container Toolkit.

### 1. Host prerequisites
Install Docker with the Compose plugin, an NVIDIA driver, and NVIDIA Container
Toolkit. Verify GPU passthrough before building Karl:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.2-runtime-ubuntu22.04 nvidia-smi
```

### 2. Build the CUDA image
The Dockerfile uses a CUDA devel stage to compile `llama-cpp-python` with
`CMAKE_ARGS="-DLLAMA_CUDA=on"` and copies only built wheels into the runtime
stage.

```bash
docker compose build
```

### 3. Run the headless backend
Compose starts Karl with `python main.py --headless`, binds the WSS bridge on
container port `8080`, and persists local state through `./data:/app/data`.

```bash
mkdir -p data/models data/vector_db data/logs
docker compose up
```

The bridge token and localhost certificate are generated under `data/`. Model
GGUFs should be placed in `data/models/` on the host, not baked into the image.

### 4. Verify CUDA llama-cpp
After startup, inspect logs for CUDA initialization from `llama-cpp-python`
when a model is loaded:

```bash
docker compose logs -f karl-backend
```

Expected log text varies by llama.cpp version, but look for CUDA or cuBLAS
initialization lines such as `ggml_cuda_init`, `ggml_init_cublas`, or `CUDA`.

### 5. Stop the backend
```bash
docker compose down
```

---

## VS Code & Code OSS Extension

Karl contains an integrated editor extension under `oss/vss_extension/`. It is a
local WSS client for the running Karl app, so the editor can use Karl's
chat, reasoning stream, prompt lab, Codex docs, and multi-agent coding swarm
without moving inference or training out of your machine.

The extension is the bridge toward the full "Karl inside VS Code" experience:
model selection, prompt comparison, RAG, evals, LoRA/QLoRA training, adapter
loading, and local code-maintenance agents controlled from the editor.

See [docs/08_vscode_extension.md](docs/08_vscode_extension.md) for the current
bridge API, safety model, and roadmap.

The bridge token is stored in `data/bridge_token.json` and service discovery is
written to `~/.karl/service_discovery.json` when the WSS server starts.

### 1. Compile & Package Extension
Make sure you have Node.js installed, then compile the extension into a local package:
```bash
cd oss/vss_extension
npm install
npx @vscode/vsce package
```
This produces `karl-1.4.0.vsix` in the directory.

### 2. Install on VS Code
Install the package directly into VS Code:
```bash
code --install-extension karl-1.4.0.vsix
```

### 3. Install on Code OSS (Arch Linux)
To install the package directly into Code OSS on Arch:
```bash
code-oss --install-extension karl-1.4.0.vsix
```

### 4. Publish to Open VSX Registry (for Code OSS Marketplace)
To publish the extension under your own verified namespace on Open VSX (open-vsx.org):
```bash
npx ovsx create-namespace your-github-username -p <your-open-vsx-access-token>
npx ovsx publish karl-1.4.0.vsix -p <your-open-vsx-access-token>
```

---

## Security and Safety

Karl is a local-first application, but it has the power to execute code and
interact with your filesystem. 

- **Privacy:** Karl does not phone home. All inference and RAG are offline.
- **Bridge Security:** The VS Code bridge uses localhost WSS, token validation, and scoped JSON-RPC permissions. The token store is `data/bridge_token.json`.
- **Path Protection:** Critical system paths are blocked from being targeted by agents or RAG.
- **Sandboxing:** Code verifications in the auto-train pipeline run inside isolated Docker containers.

See [docs/10_security_and_safety.md](docs/10_security_and_safety.md) for the full security model and safe usage guidelines.

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

The core text model is managed by `app/engine/model_loader.py`. It reads
`data/model_registry.json` for context limits, retries `mlock` failures without
memory locking, scales context down on VRAM pressure, supports draft-model
speculative decoding, and uses a circuit breaker to avoid repeated OOM reloads.

---

## Milestones Completed
- ✅ Milestone 1: Headless Introspection Engine
- ✅ Milestone 2: Dual-Pane Thought Stream UI
- ✅ Milestone 3: Memory & Context Management
- ✅ Milestone 4: Universal RAG Pipeline
- ✅ Milestone 5: Hackable Decoupling
- ✅ Milestone 6: Agentic Loop (Autonomous Self-Iteration)
- ✅ Milestone 7: Interactive Session Branching (Conversation Tree)
