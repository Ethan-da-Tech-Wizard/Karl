# Karl — Multi-Agent Swarm

Karl's multi-agent swarm is an autonomous, self-correcting code-modification system
that runs entirely offline on the local LLM. It is activated from the Swarm workspace
in the PyQt6 desktop app or via the `submit_task` JSON-RPC method from the VS Code
extension.

---

## Architecture

```
SwarmOrchestratorThread (QThread)
├── SwarmSessionState          ← shared blackboard
├── ArchitectAgent             ← plans which files to change
├── CoderAgent                 ← edits each file (multi-turn tool loop)
└── TesterAgent                ← runs the user-configured test command
```

All three agents are subclasses of `BaseSwarmAgent` defined in
`app/engine/swarm_agents.py`. The orchestrator runs in a background
`QThread` (`app/engine/swarm_orchestrator.py`) so the PyQt6 UI stays
responsive during long agent runs.

---

## Shared Blackboard — SwarmSessionState

```python
class SwarmSessionState:
    workspace_path: str          # absolute path to the code workspace
    objective:      str          # the developer's natural-language goal
    test_command:   str          # shell command to verify correctness
    plan:           dict         # Architect's JSON plan (set after Phase 1)
    tasks_status:   dict[str, str]   # filepath → pending|in_progress|completed|failed|skipped
    file_diffs:     dict[str, str]   # filepath → new content (unused currently)
    test_runs:      list[dict]   # raw test run records
```

Workspaces and agents never share Python references directly. All
inter-phase communication is through `SwarmSessionState` and Qt signals.

---

## Execution Pipeline

### Phase 1 — Context Scan

`SwarmOrchestratorThread._workspace_root()` walks the workspace and
collects file contents into a `{filepath: content}` dict (the "context
map"). This snapshot is passed to the Architect and to each Coder call
so agents always see the same baseline.

### Phase 2 — Architect Planning

`ArchitectAgent.create_plan(objective, context)` calls the local LLM with
a structured prompt that requires a strict JSON response:

```json
{
  "explanation": "A high-level summary of the solution",
  "tasks": [
    {
      "filepath": "relative/path/to/file.py",
      "instructions": "What to change and why"
    }
  ]
}
```

- Temperature: `0.1` (low for deterministic JSON)
- Max tokens: `1536`
- Fallback on `JSONDecodeError`: returns `{"explanation": "...", "tasks": []}`

The orchestrator validates tasks with `_validate_tasks()` which enforces
path-traversal safety using `_safe_workspace_path()`. Any path that
resolves outside the workspace root is blocked with a security error.

The plan is emitted as `task_plan_created(dict)` signal for the UI.

### Phase 3 — Dependency Layering

`build_dependency_layers(tasks)` performs a topological sort of the task
graph based on Python import analysis:

1. Parse `ast.Import` and `ast.ImportFrom` nodes from each target file.
2. Detect intra-task imports (i.e. one modified file importing another modified file).
3. Build a directed acyclic graph (DAG) where an edge A → B means A must
   be written before B.
4. Kahn's algorithm divides tasks into layers; tasks within a layer have
   no mutual dependencies.
5. **Cycle detection**: if a cycle is found, the algorithm logs a warning
   and forces the cyclic node into a new layer (fallback to sequential).

Layers are emitted via `dependency_layers_built(list)`.

### Phase 4 — Coder Execution (Per Layer)

Each layer runs its tasks in a `ThreadPoolExecutor(max_workers=4)`.
Each task calls `CoderAgent.generate(task, workspace_ctx, workspace_path)`.

`CoderAgent` runs a **multi-turn tool loop** (up to 8 turns):

1. Build a system prompt that includes:
   - Available tool schema (`<tools>` XML block)
   - Tool call format instructions
   - **CodebaseMemory** signature reference block (from `app/engine/agent_memory.py`)
2. Send the initial user message (task file + instructions + workspace context snippet).
3. Receive model output and parse `<tool_call name='TOOL_NAME'>` tags.
4. Dispatch each tool call through `_TOOL_REGISTRY`:

| Tool | Description |
|------|-------------|
| `write_file` | Overwrites a workspace file. Path is resolved through `_safe_workspace_path()`. |
| `read_file` | Reads current content of a workspace file (capped at 6000 characters). |
| `grep_workspace` | Finds lines matching a regex pattern across all `.py` workspace files. |
| `shell_run` | Executes a shell command in the workspace (timeout 15s). |
| `lint_python` | Runs `pyflakes` on a workspace `.py` file and returns violations. |
| `done` | Signals the loop to stop. |

5. Tool results are fed back as user-role messages, and the model
   continues until it calls `done()` or 8 turns are exhausted.
6. The `reasoning_before_tool` guard (`parse_reasoning_and_tool()`)
   enforces that every `<tool_call>` must be preceded by a
   `<reasoning>...</reasoning>` block. Missing reasoning raises a
   `ValueError` that blocks the tool from executing.

After the tool loop, the orchestrator performs **client-side validation**:

- **AST check (Python)**: `ast.parse(content)` — surfaces `SyntaxError` before writing.
- **JSON check**: `json.loads(content)` for `.json` target files.
- Files that fail validation are marked `failed` and their syntax error
  string is fed back into the next self-correction retry.

### Phase 5 — Cherry-Pick Review

Before any file is written to disk, the orchestrator emits
`edits_proposed(proposals)` and blocks until the developer calls
`commit_selected_edits(selected_filepaths)`.

The UI (or the WebSocket bridge) can remove individual files from the
accept list. Only approved files are written.

### Phase 6 — Test Verification

`TesterAgent.run(command, workspace_path)` executes the developer's
configured test command via `subprocess.run` (timeout 30s). It returns
`(passed: bool, trace: str)`.

If the test fails:
- The full traceback is injected into `layer_failure_traces[filepath]`.
- On the next retry, the Coder's task `instructions` are extended with:
  `"Warning: Previous test failed with this trace:\n{trace}\nCorrect the code."`

### Phase 7 — Self-Correction Loop

Each dependency layer retries up to **3 times** if verification fails.
The `Span("Self Reflection")` context manager wraps each retry for
tracing. After 3 failed attempts the layer is marked permanently failed
and the overall run continues with the remaining layers (collecting
partial success).

---

## Qt Signals

| Signal | Payload | Meaning |
|--------|---------|---------|
| `status_update` | `str` | Human-readable log/status message |
| `task_plan_created` | `dict` | Architect's full JSON plan |
| `dependency_layers_built` | `list[list[task]]` | Topologically sorted task groups |
| `layer_started` | `int, int, list` | Layer index, total layers, task list |
| `layer_finished` | `int, bool, str` | Layer index, success flag, summary |
| `task_status_changed` | `str, str, str` | Filepath, new status, detail |
| `verification_started` | `int, str` | Layer index, test command |
| `traceback_captured` | `str, str` | Context (filepath/layer), traceback |
| `verification_failed` | `str, str` | Context, full traceback |
| `edits_proposed` | `list[{filepath, content}]` | Awaits cherry-pick confirmation |
| `file_edited` | `str, str` | Filepath, new content (post-write) |
| `test_result` | `bool, str` | Passed flag, error traceback |
| `coder_token` | `str, str` | Filepath, streaming token |
| `finished_swarm` | `bool, str` | Success flag, final summary |

---

## Security & Safety

All agent file access is routed through `_safe_workspace_path(workspace_path, rel)`:

```python
def _safe_workspace_path(workspace_path: str, rel: str) -> str | None:
    ws_real = os.path.realpath(workspace_path)
    target = os.path.realpath(os.path.join(ws_real, rel))
    if target == ws_real or target.startswith(ws_real + os.sep):
        return target
    return None
```

- Parent traversal (`../../etc/passwd`) → blocked.
- Absolute path injection (`/etc/passwd`) → blocked.
- Symlink escape (`workspace/evil → /etc/passwd`) → blocked (via `realpath`).

Any blocked access logs a `SECURITY ALERT` at `WARNING` level and returns
`_SECURITY_BLOCK_MSG` to the agent instead of executing.

---

## Codebase Memory Integration

Before each Coder turn the orchestrator queries `CodebaseMemory` from
`app/engine/agent_memory.py`:

1. `CodebaseMemory(workspace_path).build_index()` — AST-scans all `.py`
   files and extracts class names, function names, arguments, and docstrings.
   Persists to `data/agent_memory.json`.
2. `query_memory(keywords)` — searches index by keywords extracted from the
   task description and returns a formatted signature reference block.
3. The block is injected into the Coder's system prompt as:
   ```
   Codebase Interfaces & Signatures Reference:
   Use the following existing codebase signatures to ensure integration:
   - utils.py: def add(a, b) → Add two numbers.
   ```

This eliminates hallucinated API calls that reference non-existent function
signatures.

---

## Tracing & Observability

The orchestrator wraps each major phase in a `Span` from
`app/utils/tracing.py`:

| Span Name | Attributes |
|-----------|------------|
| `Swarm Run` | `workspace_path`, `objective`, `test_command` |
| `Retrieve Context` | `query`, `chunks`, `bytes` |
| `Agent Reasoning` | `agent`, `prompt_size`, `token_count`, `task_count` |
| `Test Execution` | `layer_index`, `command`, `task_count`, `success`, `trace_length` |
| `Self Reflection` | `layer_index`, `correction_loop`, `max_correction_loops`, `failed_files` |

Spans are persisted as JSONL to `data/logs/traces/spans_YYYY-MM-DD.jsonl`.

---

## Stopping

`stop_task()` sets `_stop_requested = True`. The orchestrator checks this
flag at every loop boundary and exits cleanly, emitting
`finished_swarm(False, "Execution stopped by user.")`.

Tool-level timeouts (shell_run: 15s, test command: 30s) prevent indefinite
hangs inside individual agent steps.
