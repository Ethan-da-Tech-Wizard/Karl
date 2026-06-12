# Karl WebSocket Bridge Protocol Specification

This document defines the WebSocket bridge contract between the Karl desktop application (`app/engine/websocket_server.py`) and the VS Code / Code OSS editor extension (`vscode-extension/`).

All communication uses standard JSON-RPC 2.0 formatting.

---

## 1. Request/Response Methods (Client to Server)

The extension issues requests to the local Karl server (default port `8080`).

### `get_runtime_status`
Retrieves current runtime, model status, and memory usage metrics.
* **Params**: None
* **Response Result**:
  ```json
  {
    "bridge": {
      "port": 8080,
      "clients": 1,
      "listening": true
    },
    "runtime": {
      "state": "idle" | "running",
      "swarm_active": false,
      "chat_active": false
    },
    "model": {
      "name": "deepseek-r1-1.5b.gguf",
      "loaded": true,
      "n_ctx": 4096
    },
    "adapter": {
      "name": "my-lora-adapter",
      "loaded": true
    },
    "system": {
      "ram_mb": 420.5
    }
  }
  ```

### `list_models`
Lists all GGUF models available in the local catalog and registry.
* **Params**: None
* **Response Result**:
  ```json
  {
    "active": {
      "filename": "deepseek-r1-1.5b.gguf",
      "adapter": null
    },
    "models": [
      {
        "name": "1.5B Qwen",
        "filename": "deepseek-r1-1.5b.gguf",
        "tier": "scout",
        "n_ctx": 4096,
        "min_ram_gb": 4,
        "installed": true,
        "active": true,
        "size_gb": 1.1
      }
    ]
  }
  ```

### `set_active_model`
Sets the active model and prompts a reload on the next generation request.
* **Params**:
  * `filename` (string): The filename of the model GGUF (e.g. `deepseek-r1-1.5b.gguf`).
  * `adapter` (string | null): The LoRA adapter name if applicable.
* **Response Result**:
  ```json
  {
    "active": { "filename": "deepseek-r1-1.5b.gguf" },
    "loaded": false,
    "message": "Active model set to deepseek-r1-1.5b.gguf."
  }
  ```

### `list_prompt_pairs`
Lists all saved prompt pairs used for Prompt Lab.
* **Params**: None
* **Response Result**:
  ```json
  {
    "pairs": [
      {
        "name": "code_refactoring",
        "system_a": "System prompt A...",
        "system_b": "System prompt B...",
        "user_a": "User prompt...",
        "user_b": "User prompt..."
      }
    ]
  }
  ```

### `get_prompt_pair`
Retrieves details of a specific prompt pair by name.
* **Params**:
  * `name` (string): The name of the saved prompt pair.
* **Response Result**: Full prompt pair JSON object.

### `save_prompt_pair`
Saves or overwrites a Prompt Lab configuration.
* **Params**:
  * `name` (string): Unique identifier name.
  * `system_a`, `system_b`, `user_a`, `user_b` (strings)
  * `rag_a`, `loop_a`, `rag_b`, `loop_b` (booleans)
  * `output_a_raw`, `output_b_raw` (strings)
  * `output_a_display`, `output_b_display` (strings)
* **Response Result**:
  ```json
  {
    "name": "code_refactoring",
    "saved": true
  }
  ```

### `delete_prompt_pair`
Deletes a saved prompt pair config file.
* **Params**:
  * `name` (string): Name of the pair.
* **Response Result**:
  ```json
  {
    "name": "code_refactoring",
    "deleted": true
  }
  ```

### `list_kb_sources`
Lists all documents currently indexed in the FAISS vector database.
* **Params**: None
* **Response Result**:
  ```json
  {
    "sources": [
      { "name": "docs/architecture.md", "chunks": 5, "ingested_at": "ISO-TIMESTAMP" }
    ],
    "total_sources": 1,
    "total_chunks": 5,
    "supported_extensions": [".pdf", ".docx", ".txt", ".md", ".py", ".csv"],
    "ingesting": false
  }
  ```

### `ingest_path`
Starts background parsing and ingestion of a file or folder into the FAISS index.
* **Params**:
  * `path` (string): Folder or file location.
  * `recursive` (boolean): Ingest directory files recursively.
  * `chunk_size` (number): Target chunk tokens/size (50-2000).
  * `overlap` (number): Chunk overlap tokens (0 < overlap < chunk_size).
* **Response Result**:
  ```json
  {
    "status": "started",
    "task_id": "uuid-string",
    "file_count": 12,
    "path": "/home/user/project"
  }
  ```

### `search_kb`
Queries the Knowledge Base database.
* **Params**:
  * `query` (string): Text search term.
  * `top_k` (number): Number of chunks to retrieve (1-25).
  * `threshold` (number): Distance threshold (lower distance is more similar).
  * `source_filter` (string | null): Retrieve chunks only from a specific file.
* **Response Result**:
  ```json
  {
    "query": "websocket port",
    "top_k": 3,
    "threshold": 0.0,
    "source_filter": null,
    "results": [
      {
        "text": "WebSocket server runs on port 8080...",
        "source_file": "docs/architecture.md",
        "chunk_id": 2,
        "rank": 0,
        "distance": 0.1234
      }
    ]
  }
  ```

### `submit_task`
Deploys the multi-agent Swarm to fulfill a coding objective.
* **Params**:
  * `objective` (string): Coding directive.
  * `workspace_path` (string): Absolute path to project workspace root.
  * `test_command` (string): Verification command.
  * `hyperparams` (object): Generation settings (temperature, top_p, etc.).
* **Response Result**:
  ```json
  { "status": "started" }
  ```

### `stop_task`
Interrupts active task / swarm thread execution.
* **Params**: None
* **Response Result**: Empty object.

### `submit_chat`
Sends a direct message to Karl.
* **Params**:
  * `message` (string): Prompt content.
  * `workspace_path` (string): Target workspace.
  * `hyperparams` (object): Generation settings (including `system_prompt` and `rag_enabled`).
* **Response Result**: Empty object. Tokens are streamed back via notifications.

---

## 2. Server Notifications (Server to Client)

The server broadcasts progress updates and model generations using JSON-RPC notification patterns.

### `status_update`
Emitted by the Swarm Orchestrator when agents transition phases.
* **Params**: `{ "message": "Planning agent starting file audit..." }`

### `task_plan_created`
Emitted when an implementation plan is drafted.
* **Params**: `{ "plan": "Markdown implementation steps..." }`

### `file_edited`
Emitted when a Swarm agent proposes editing a file.
* **Params**:
  * `filepath` (string): Targeted file.
  * `content` (string): New proposed content.
  * `summary` (string): Summary of proposed modifications.

### `test_result`
Emitted after a verification test suite runs.
* **Params**:
  * `passed` (boolean): True if exit code was 0.
  * `error_trace` (string): Stdout/stderr error trace output on failure.

### `finished_swarm`
Emitted when the multi-agent workspace execution ends.
* **Params**:
  * `success` (boolean)
  * `summary` (string)

### `kb_ingest_progress`
Emitted as files are chunked and indexed.
* **Params**:
  * `task_id` (string)
  * `current` (number): Current file index.
  * `total` (number): Total files found.
  * `filename` (string): Current file name.
  * `status` (string): "ingesting"

### `kb_ingest_finished`
Emitted when directory indexing finishes.
* **Params**:
  * `task_id` (string)
  * `file_count` (number)
  * `error_count` (number)
  * `chunks_added` (number)
  * `snapshot` (object): Updated library snapshot.

### `chat_thought_token`
Reasoning tokens streamed during DeepSeek reasoning phases.
* **Params**: `{ "token": "Let me check..." }`

### `chat_response_token`
Final output response tokens streamed.
* **Params**: `{ "token": "Here is the updated config..." }`

### `chat_finished`
Fires when final assistant response generation is complete.
* **Params**: None

### `vision_result`
Emitted by image/multimodal analysis workflows.
* **Params**:
  * `caption` (string): General description of the image.
  * `ocr` (string): Extracted text.
