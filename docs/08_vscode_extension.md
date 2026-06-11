# Karl VS Code Extension

## Purpose

Karl's VS Code / Code OSS extension is the editor-facing control surface for the
local Karl runtime. It lets a user stay inside their code editor while asking the
same local model, RAG index, prompt lab, training curator, and agentic code
tools that the PyQt application uses.

The extension is not a cloud service and it is not a second inference engine.
It is a thin client that connects to the Karl desktop process over a local
WebSocket bridge:

```
VS Code / Code OSS
  -> vscode-extension/extension.js webview
  -> ws://localhost:<karl.port>
  -> app/engine/websocket_server.py
  -> Karl engine threads, RAG, model loader, training tools
```

The design goal is simple: a consumer should be able to use Karl as a complete
open-source AI creation environment from the editor they already live in, while
all model execution, training data, adapters, traces, and code edits remain on
their own machine.

## Current Extension Surface

The extension package lives in `vscode-extension/`.

Current capabilities:

- Activity Bar view: `Karl Agent Swarm`
- Command palette / context menu command: `Ask Karl to Refactor Selection`
- Local WebSocket connection to the running Karl app
- Swarm workspace: objective, workspace path, test command, stop button, logs
- Chat workspace: direct local chat with streamed final answer
- Live introspection: streamed `<think>` content in a separate panel
- Prompt Lab: A/B prompt comparison with server-rendered character diff
- Codex Library: local reference docs served from `data/codex_library/`
- Settings drawer: temperature, top-p, max tokens, RAG toggle, loop toggle
- File edit transaction flow: write edited file, open VS Code diff, accept or
  roll back `.original` backup

The bridge methods currently handled by `app/engine/websocket_server.py` are:

| Method | Purpose |
|--------|---------|
| `get_runtime_status` | Return active model, adapter, context, RAM, bridge clients, and running state. |
| `list_models` | Return registered and locally installed GGUF models with active/install state. |
| `set_active_model` | Write `data/active_model.json` and reset `ModelLoader` for the next generation. |
| `list_prompt_pairs` | Read saved Prompt Lab pairs from `data/prompt_pairs/`. |
| `get_prompt_pair` | Load one saved Prompt Lab pair. |
| `save_prompt_pair` | Save a named A/B prompt pair using Karl's Prompt Lab schema. |
| `delete_prompt_pair` | Delete one saved Prompt Lab pair. |
| `submit_task` | Start the multi-agent coding swarm against a workspace path. |
| `submit_chat` | Start a single chat generation or agentic loop generation. |
| `stop_task` | Stop the active swarm or chat thread. |
| `compute_diff` | Render Prompt Lab output diff HTML. |
| `list_codex_topics` | List local Codex reference topics. |
| `get_codex_content` | Return one local Codex reference page. |

Server notifications sent back to the extension include:

| Notification | Purpose |
|--------------|---------|
| `status_update` | Human-readable status/log message. |
| `task_plan_created` | Architect agent produced a coding plan. |
| `file_edited` | Coder agent produced replacement file content. |
| `test_result` | Tester agent finished a verification run. |
| `finished_swarm` | Swarm stopped with success/failure summary. |
| `chat_thought_token` | Streaming reasoning/introspection token. |
| `chat_response_token` | Streaming final response token. |
| `chat_finished` | Chat or prompt-lab generation completed. |

## How To Use Locally

Start Karl first:

```bash
cd ~/karl
source venv/bin/activate
python main.py
```

Package and install the extension:

```bash
cd ~/karl/vscode-extension
npm install
npx @vscode/vsce package
code --install-extension karl-1.4.0.vsix
```

For Code OSS on Arch:

```bash
code-oss --install-extension karl-1.4.0.vsix
```

Open the Karl Activity Bar panel. The extension connects to
`ws://localhost:8080` by default. Change `karl.port` in VS Code settings if the
Karl app is running the bridge on another port.

## What "Full Karl In VS Code" Means

The target product is not just a refactor button. It is the full Karl workflow
available from the editor:

1. **Workbench in VS Code**
   - Stream model reasoning and final response.
   - Toggle RAG and agentic loop mode.
   - Use per-run hyperparameters.
   - Save feedback into the training curator.
   - Keep trace IDs visible so every answer can be audited later.

2. **Model Registry in VS Code**
   - List installed GGUF models from `data/models/`.
   - Read `data/model_registry.json` for tier metadata.
   - Select active DeepSeek model without opening the desktop app.
   - Show RAM/VRAM/context requirements before loading.
   - Trigger model downloads through Karl, not through the extension directly.

3. **Prompt Lab in VS Code**
   - Run two system prompts against the same user message.
   - Stream both outputs.
   - Render character diff and summary.
   - Save/load named prompt pairs from `data/prompt_pairs/`.

4. **Knowledge Base in VS Code**
   - Ingest workspace files and external docs into the local FAISS index.
   - Configure chunk size, overlap, top-k, and retrieval threshold.
   - Preview retrieved chunks before sending them into generation.

5. **Training Studio in VS Code**
   - Browse curated SFT examples.
   - Export Unsloth SFT and DPO JSONL.
   - Detect local HF model weights under `data/hf_models/`.
   - Start LoRA/QLoRA training via Karl's `TrainingThread`.
   - Stream loss/progress and save adapters under `data/adapters/<name>/`.
   - Load/unload adapters through `ModelLoader`.

6. **Eval Suite in VS Code**
   - Pick eval JSONL datasets.
   - Run local evals against the active model/adapter.
   - Display pass/fail, grader, latency, and response snippets.

7. **Local Agentic Maintenance**
   - Let agents read the active workspace.
   - Let the Architect create a plan.
   - Let the Coder propose file edits.
   - Always show diffs before changes are accepted.
   - Let the Tester run the configured command.
   - If tests fail, feed the trace back into the next coding attempt.

## Boundary Between Extension And Karl

Keep heavy capability in Karl:

- model loading
- inference
- RAG indexing and retrieval
- trace logging
- training and adapter loading
- eval execution
- file scanning logic
- agent planning/coding/testing

Keep editor-native capability in the extension:

- webview UI
- command registration
- selected text capture
- active workspace path detection
- VS Code diff editor
- accept/rollback UX
- settings for bridge port and auto-connect

This boundary preserves privacy and keeps the extension portable. It also
prevents the extension host from becoming a second Python runtime with its own
dependency problems.

## Practical API Roadmap

The current bridge already supports chat, swarm, prompt diff, and codex docs.
To expose the rest of Karl cleanly, add explicit JSON-RPC methods instead of
overloading `submit_chat`.

Recommended next bridge methods:

| Method | Result |
|--------|--------|
| `download_model` | Streams model download progress from Karl. |
| `list_adapters` | Installed adapters under `data/adapters/`. |
| `load_adapter` | Loads adapter into `ModelLoader`. |
| `unload_adapter` | Clears active adapter. |
| `list_training_examples` | Curated examples with source and timestamps. |
| `export_sft` | Writes Unsloth SFT JSONL. |
| `export_dpo` | Writes Unsloth DPO JSONL. |
| `start_training` | Starts LoRA/QLoRA training and streams progress. |
| `list_eval_datasets` | Available eval JSONL files. |
| `run_eval` | Runs eval harness and streams progress/results. |
| `ingest_path` | Adds a file/folder to the local knowledge base. |
| `search_kb` | Returns retrieved chunks with scores and metadata. |

For long-running methods, send an immediate JSON-RPC response:

```json
{ "jsonrpc": "2.0", "id": 1, "result": { "status": "started", "task_id": "..." } }
```

Then stream notifications:

```json
{ "jsonrpc": "2.0", "method": "training_progress", "params": { "task_id": "...", "step": 4, "total": 100 } }
```

## Safety Model For Self-Maintaining Agents

The end goal is for local agents to inspect and modify their own code when
issues arise or upgrades are useful. That is powerful, so the extension should
keep a transaction boundary around all writes.

Required guardrails:

- Agents may read the workspace, but writes must be proposed as patches or full
  replacement content.
- The extension opens a diff before accepting a write.
- User can accept or roll back each file.
- The configured test command must run after each write.
- Failed tests feed the traceback back to the Coder agent.
- No push, publish, dependency install, or destructive shell operation should
  happen without explicit user approval.
- Trace IDs should be shown for every autonomous action so users can audit why a
  change was made.

The current extension already implements the core accept/rollback pattern using
`<file>.original` backups. The next step is to make it multi-file and task-ID
aware so a whole agent run can be accepted or reverted as one transaction.

## Consumer Experience Goal

Karl should feel like a local AI production workbench:

- **Create** with local chat, prompt lab, RAG, and code agents.
- **Inspect** every reasoning stream and raw trace.
- **Evaluate** behavior against local datasets.
- **Improve** models with curated examples and LoRA/QLoRA adapters.
- **Ship** code changes only after visible diffs and local tests.

That is the "ultimate open-source experience" target: no vendor lock-in, no
remote inference, no hidden data path, and no mystery model behavior.
