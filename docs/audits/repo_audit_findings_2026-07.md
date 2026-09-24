# NPUWU — Karl Audit Findings & Fix Tracker

Generated from a full-repo audit (2026-07-15). Each item is tracked to completion below.
Status legend: `[ ]` open · `[x]` fixed · `[~]` partial/deferred (reason noted).

## Critical

- [x] **1. TLS disabled in every real deployment + token-refresh privilege escalation** — `app/engine/websocket_server.py`. `_start_server` drops TLS whenever `KARL_WS_HOST` is `localhost`/`127.0.0.1`/`0.0.0.0`; `docker-compose.yml`, `k8s/deployment.yaml`, `helm/karl/values.yaml` all set `KARL_WS_HOST=0.0.0.0` with the port published externally, so the bearer token goes out in cleartext. `refresh_token` only checks "authenticated," not scope, and always mints a full-admin token back to the caller — any `read:telemetry` client can self-escalate to admin. `k8s/ingress.yaml`/Helm also declare `backend-protocol: HTTPS`, so ingress will TLS-handshake against a now-plaintext backend.
- [x] **2. Encrypted trace archives can never be decrypted by the app itself** — `app/utils/trace_logger.py`. Archive step derives the Fernet key from the hardware-UUID salt; decrypt step derives it from an unrelated salt (RAM/storage/CPU-flags/OS string). Every `.jsonl.enc` archive is permanently unreadable.
- [x] **3. Model output can trigger arbitrary tool execution via prompt injection** — `app/engine/llm_thread.py`, `app/engine/tool_executor.py`, `app/engine/mcp_client.py`. Full generated output (including RAG-retrieved document text) is regex-scanned for `<tool_call>` tags and auto-executed with no check the tool was actually offered, no confirmation.

## High

- [x] **4. ~230KB dead code silently shadowing live workspaces** — `app/ui/workspaces/training_studio.py`, `app/ui/workspaces/system_config.py` (shadowed by same-named packages; Python prefers the package), `app/ui/workspaces/swarm_workspace.py` (orphaned, nothing imports it). AGENTS.md's "Repo Structure" section and `docs/05_scope_and_milestones.md`, `docs/09_vision_implementation_plan.md` still cite the dead flat files.
- [~] **5. "AI Lab" sidebar button opens Training Studio instead of AI Lab** — relabeled the sidebar button/tooltip to "Training" to match what index 4 actually opens (matches AGENTS.md's canonical 10-workspace list, which never included an "AI Lab" slot). `app/ui/workspaces/ai_lab.py` (813 lines, has its own test file) remains genuinely unwired — deliberately not auto-added as an 11th sidebar slot since that's a product decision, not a bug fix.
- [x] **6. Documented `<think>`-stripping safety layer never runs on the real save path** — `app/utils/memory_manager.py` vs `app/utils/session_tree.py`. Real saves go through `SessionTree.save()`, which writes raw `thought` fields unsanitized to `data/sessions/*.json`.
- [x] **7. Dataset merge crashes on same-batch prompt collisions** — `app/utils/dataset_merger.py`. Stores a future-list index, reads it back indexed into the wrong (shorter) list → `IndexError`.
- [~] **8. Secrets committed to git** — `data/bridge_token.json`/`data/bridge_token.txt` untracked, gitignored, `.txt` deleted (unused by any code path). Token value itself NOT rotated — that's a live-credential change outside this pass; do it manually (delete `data/bridge_token.json`, restart the bridge) when convenient. History still contains the old token; scrubbing it needs `git filter-repo`/BFG + force-push, a deliberate call, not done here.
- [x] **9. `Karl-main/` stale duplicate tree still tracked** — AGENTS.md says it "was removed... do not re-create it," but it's a full tracked duplicate in the repo.

## Medium

- [x] **10. Path traversal via session rename** — `app/ui/workspaces/workbench/session_panel.py`, `app/repository/session_repository.py`. Unsanitized `os.path.join`/`os.rename` on user-supplied name.
- [x] **11. Three workspaces bypass `AppState`, hold live `WorkbenchWorkspace` refs** — `VisionWorkbench`, `DocsWorkspace`, `SystemConfigWorkspace` call `WorkbenchWorkspace` methods directly instead of routing through `AppState`.
- [x] **12. CPU-affinity pinning pins the wrong thread, races under concurrency** — `app/engine/llm_thread.py`, `app/engine/agentic_thread.py`. `psutil.Process()` with no PID affects the main thread, not the QThread worker; process-global affinity races across concurrent generations.
- [x] **13. `AgenticThread` never registers with `TaskSupervisor`; `LLMThread` watchdog timeout leaks a phantom RUNNING task** — `app/engine/agentic_thread.py`, `app/engine/llm_thread.py`.
- [x] **14. `eval/graders.py` near-zero pytest coverage** — 4 of 5 graders only exercised by `smoke_test.py`, which pytest never collects.
- [x] **15. `karl.sh` bootstraps `.venv`; README/AGENTS.md/actual repo use `venv`** — redundant venv + re-download on first run via the script.

## Low

- [x] **16. `SharedMemoryManager.active_names` raises `NameError`** — `app/utils/ipc_helper.py`, loop variable typo.
- [x] **17. `raw_test.py` hardcodes a model path, bypasses `ModelLoader`** — crashes if active model tier differs.
- [x] **18. `AGENTS.md` self-contradictory** — claims "all phases complete" while its own diagram still flags `engine_test.py`/`smoke_test.py` as needing a Phase-5 fix that was actually already done.
- [~] **19. Order-dependent flaky test** — the originally-flagged `test_model_loader_corrupted_file` case no longer reproduces, but the same root cause (a leaked asyncio resource getting GC'd mid-suite, promoted to a hard failure by `filterwarnings = error`) still surfaces intermittently elsewhere (observed on `tests/test_dataset_merger.py::test_validate_file_missing_path`, ~2 of 3 runs). Fixed two confirmed leaks (`asyncio.new_event_loop().run_until_complete(...)` with no `.close()` in `test_custom_agents.py` and `test_websocket_bridge.py`, swapped for `asyncio.run(...)`), but those tests are `@pytest.mark.integration`-deselected by default so they weren't the actual source of the observed flake. Didn't find the real leak site — `PYTHONTRACEMALLOC` tracing made runs too slow (95s+ vs 16s) to bisect further within this pass. Root cause still open.
- [x] **20. `SessionRepository` (real file/DB-backed session persistence) has no dedicated test** — only a hand-rolled in-memory fake is tested.
