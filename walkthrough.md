# Karl Architecture Audit Walkthrough

## Scope

This audit compared the live codebase against `AGENTS.md` and the documents in
`docs/`, then focused implementation work on thread lifecycle safety, model
resource ownership, WebSocket bridge state, and documentation drift.

## Technical Debt Removed

### Model teardown race

Before this audit, generation threads called `ModelLoader.get_instance()` and
then marked the singleton as locked in a separate call. During that gap, another
UI or bridge action could call `ModelLoader.reset_instance()` and close the
llama-cpp object while a generation was about to use it. `reset_instance()` also
only logged when the model was locked, then continued teardown anyway.

The fix makes active inference an explicit lifecycle state:

- `ModelLoader._lock` is now an `RLock`, allowing atomic wrapper methods to call
  existing loader code without deadlocking.
- `ModelLoader.acquire_instance()` loads or returns the model and increments an
  active-generation counter before any reset can interleave.
- `ModelLoader.inference_session()` provides a context-managed form for future
  callers.
- `ModelLoader.reset_instance()` now raises while inference is active instead
  of closing C-level resources under a running thread.
- `LLMThread` and `AgenticThread` now use `acquire_instance()` and still release
  the active count from `finally`.

Impact: model reloads, adapter changes, and bridge model switches can no longer
invalidate the loaded llama-cpp handle while a generation is streaming.

### Cancellation cleanup

The generation threads already had stop flags, but streaming iterators were only
abandoned by breaking the loop. The audit added best-effort generator close calls
when cancellation is observed:

- `LLMThread` closes `response_generator` when `_stop_requested` is set.
- `AgenticThread` closes `response_gen` when `_stop_requested` is set.

Impact: cancellation releases Python-side generator resources promptly and
reduces the chance of delayed cleanup after a user presses stop.

### AppState cross-thread signal emission

`AppState.__setattr__()` emitted `state_changed` directly from whichever thread
updated the value. That is risky because UI slots connected to that signal can
run from worker contexts depending on connection type.

The fix routes worker-thread updates through the `AppState` object's Qt owner
thread using `QMetaObject.invokeMethod(..., QueuedConnection, ...)`.

Impact: state updates from worker threads are delivered to UI consumers through
the main Qt event loop, reducing accidental cross-thread widget mutation.

### WebSocket bridge mutable state

The bridge kept `clients`, `client_metadata`, and `client_histories` as mutable
shared containers used by the asyncio loop, Qt thread callbacks, status queries,
and shutdown code.

The fix adds a `_clients_lock` and applies it to:

- client registration and cleanup
- client count/status reads
- shutdown clear operations
- broadcast snapshots
- pruning clients that fail during notification sends

Chat thread references are also cleared when the QThread finishes, preventing
runtime status from reporting stale active work after completion.

Impact: bridge status and broadcasts are less likely to race with disconnects or
finished threads, and failed WebSocket clients are removed rather than retained.

### Documentation drift

The docs still described an older six-workspace shell, plain `ws://` bridge
transport, and unauthenticated bridge roadmap items. Updated docs now cover:

- current MainWindow stack, including Vision, Swarm, Codex, Flywheel, and AI Lab
- guarded ModelLoader acquisition/reset semantics
- queued AppState state emissions
- WSS bridge URL and `data/bridge_token.json`
- current bridge methods for KB, custom agents, vector tracing, and mini-train
- current security checklist marking bridge token auth as implemented
- current repo structure entries for vision and runtime bridge artifacts

## Architectural Rationale

Karl has one expensive native model handle shared by UI workspaces, background
threads, and the editor bridge. The important invariant is therefore simple:
generation owns the model until generation cleanup completes. The new active
counter enforces that invariant at the only place that can safely do so:
`ModelLoader`.

The WebSocket bridge is a second control surface over the same engine, so its
state must tolerate Qt signals arriving from QThreads while the asyncio server
is accepting disconnects and broadcasts. Locking only the short metadata
sections keeps the bridge responsive while protecting container integrity.

For `AppState`, queuing the signal emission through Qt's event system keeps the
shared-state convenience while respecting the GUI rule: worker threads may
compute and emit, but UI mutation belongs on the GUI thread.

## Uptime And UI-Freeze Benefits

- Prevents model reset during active inference, avoiding crashes or undefined
  behavior inside llama-cpp.
- Makes cancellation release streaming generators sooner, reducing lingering
  work after stop requests.
- Prevents stale chat-thread references from keeping bridge status in a false
  running state.
- Avoids cross-thread UI updates from shared state changes.
- Keeps failed WebSocket clients from accumulating in broadcast sets.
- Documents the real bridge security model so operators use the tokenized WSS
  endpoint instead of stale unauthenticated `ws://` instructions.

## Verification

Added `tests/test_architecture_audit.py` covering:

- `ModelLoader.reset_instance()` blocking during active inference
- generation threads using guarded model acquisition and generator close paths
- AppState queued signal emission guardrails
- WebSocket failed-client pruning
- thread-safe bridge client count implementation

Full suite result:

```text
112 passed, 14 skipped, 3 warnings in 25.37s
```

---

# Security Hardening Assessment

## Threat Model

Karl exposes a local WebSocket RPC bridge to browser-based editor extensions (VS Code). Any local process that obtains the bridge token — or a malicious VS Code extension already installed in the user's environment — can send arbitrary RPC commands. The fixes below protect against path traversal, arbitrary file loading, and markup injection within that threat surface.

---

## Finding 1 — Symlink Bypass in `_is_safe_path`

**File:** `app/engine/websocket_server.py` · `_is_safe_path()`

**Root cause:** `os.path.abspath()` normalises `.` / `..` segments but does **not** resolve symlinks. A symlink inside the allowed project tree that points to `/etc/shadow` or `~/.ssh/id_rsa` would pass `abspath`-based checks and then be read by the actual `open()` call.

The blocklist was also incomplete, omitting `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.kube`, `~/.docker`, `~/.config`, `~/.local`, `/tmp`, and system library paths.

**Fix:** Replaced `abspath` with `realpath` throughout `_is_safe_path`. Each blocked path is also `realpath`-resolved before comparison. Project root is checked first and unconditionally allowed. Expanded `blocked_paths` with all credential and config directories above.

**Effect:** A symlink chain cannot smuggle a blocked path past the allowance logic.

---

## Finding 2 — Symlink Escape in `_collect_kb_files`

**File:** `app/engine/websocket_server.py` · `_collect_kb_files()`

**Root cause:** Individual file candidates collected via `os.walk` were not realpath-resolved before being queued for ingestion, so a symlink file inside an allowed directory could point outside.

**Fix:** Initial path expansion changed to `realpath`. Added `followlinks=False` explicitly to `os.walk`. Every individual file candidate is now passed through `os.path.realpath()` before insertion.

---

## Finding 3 — Arbitrary Model / Adapter Paths via Agent Creation

**File:** `app/engine/websocket_server.py` · `create_custom_agent` handler

**Root cause:** `base_model` and `adapter` were stored verbatim in `data/custom_agents.json`. When used for a chat session these values reach `llama-cpp-python` as file paths. An authenticated bridge client could supply `../../etc/shadow` as `base_model`.

**Fix:**
- `base_model` — must be a bare filename (no `/`), must end with `.gguf`, and the file must exist in `data/models/`. A `basename()` equality check ensures nothing was stripped.
- `adapter` — must be a bare directory name (no `/`), and the directory must exist in `data/adapters/`.

The same checks were applied to `_set_active_model()`.

---

## Finding 4 — Unvalidated `adapter` in `_set_active_model`

**File:** `app/engine/websocket_server.py` · `_set_active_model()`

**Root cause:** Model filename was validated but `adapter` was stored and forwarded without any check.

**Fix:** Added `basename` equality check and `isdir` inside `data/adapters/`; raises `ValueError` / `FileNotFoundError` on violation.

---

## Finding 5 — Special Characters in Auto-Train Subprocess Args

**File:** `app/engine/websocket_server.py` · `start_auto_train` handler

**Root cause:** `topic` and `adapter_name` were passed as CLI arguments to `auto_train.py` via `Popen`. While `Popen` with a list avoids shell injection, these values are used for file-system operations inside `auto_train.py` where path traversal characters could apply.

**Fix:** Two `re.match` allowlist guards before the subprocess call:
- `topic`: `^[a-zA-Z0-9][a-zA-Z0-9 _\-]*$`
- `adapter_name`: `^[a-zA-Z0-9][a-zA-Z0-9_\-]*$`

---

## Finding 6 — XSS via RAG Text in SVG Tooltip

**File:** `vscode-extension/media/karl_render.js` · `renderAilabPipeline()`

**Root cause:** Document text from the RAG index (`pt.text`) was embedded directly into SVG `<title>` elements without HTML-escaping. A crafted ingested document containing `</title></circle></svg><script>evil()</script>` would break out of the SVG context and execute JavaScript inside the VS Code webview, which has access to the `postMessage` RPC channel.

**Fix:** Wrapped `pt.text` with the existing `escapeHtml()` helper.

---

## Finding 7 — Predictable CSP Nonce

**File:** `vscode-extension/src/sidebarProvider.js` · `getHtmlForWebview()`

**Root cause:** The CSP nonce was `String(Date.now())` — a millisecond timestamp, predictable by any process that can observe the webview load event.

**Fix:** Replaced with `require('crypto').randomBytes(16).toString('hex')` — 128 bits of cryptographic entropy.

---

## Summary

| # | Vector | Severity | Status |
|---|---|---|---|
| 1 | Symlink bypass in `_is_safe_path` | High | Fixed |
| 2 | Symlink escape in KB file walk | High | Fixed |
| 3 | Arbitrary model/adapter path via agent creation | High | Fixed |
| 4 | Unvalidated adapter in `set_active_model` | Medium | Fixed |
| 5 | Special chars in auto-train subprocess args | Medium | Fixed |
| 6 | XSS via RAG text in SVG tooltip | High | Fixed |
| 7 | Predictable CSP nonce | Medium | Fixed |

All seven findings are covered by `tests/test_security_guards.py`.

```bash
venv/bin/pytest tests/test_security_guards.py -v
```
