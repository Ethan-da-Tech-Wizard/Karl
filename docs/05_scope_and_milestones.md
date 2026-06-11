# Karl — Scope Lock & Milestones

## Scope Statement

Karl is a self-contained, offline LLM **Introspection Environment** for prompt engineers.

Core invariants that must never be compromised:
- Zero network calls during inference
- Every generation is immutably logged
- The hackable core (`core/`) is always hot-reloadable without restart
- Privacy: no telemetry, no remote model servers, no localhost proxies

---

## Completed Milestones

### ✅ M1 — Headless Introspection Engine
**Files:** `engine_test.py`, `core/cognitive_parser.py`, `app/utils/trace_logger.py`

Proved the engine works and established the raw logging infrastructure.
`TraceLogger` writes structured JSONL to `data/logs/traces/`. `cognitive_parser.py`
batch-parses `<think>` blocks from raw output.

---

### ✅ M2 — Streaming Thought/Response Split UI
**Files:** `app/engine/llm_thread.py`, `app/engine/agentic_thread.py`

Inline streaming state machine in both threads routes tokens to the correct display:
- `<think>` → `new_thought_token` signal → reasoning panel
- after `</think>` → `new_chat_token` signal → response panel
- suffix guard prevents flushing partial tags across chunk boundaries
- auto-continuation: if `finish_reason == "length"`, re-queries up to 5 passes

---

### ✅ M3 — Memory & Context Management
**Files:** `app/utils/memory_manager.py`, both threads

`MemoryManager` serialises chat history as JSON. `_trim_history()` in both threads
enforces character budget `(n_ctx - 1024) * 3` and always preserves the seed message.

---

### ✅ M4 — Universal RAG Pipeline
**Files:** `app/utils/rag_pipeline.py`

Persistent FAISS flat L2 index. Embeddings via `all-MiniLM-L6-v2`.
Formats: PDF, DOCX, TXT, PY, MD, CSV. 200-word chunks / 50-word overlap.
Retrieval eval metrics: hit@1, hit@3, hit@k, reciprocal rank.
Index persists across restarts at `data/vector_db/`.

---

### ✅ M5 — Hackable Core Decoupling
**Files:** `core/interaction_loop.py`, `importlib.reload()` in both threads

All prompt construction in `core/interaction_loop.py`. Both threads call
`importlib.reload()` before every generation. User edits the file → clicks
Generate → new logic runs immediately. No restart.

---

### ✅ M6 — Agentic Loop
**Files:** `core/agentic_loop.py`, `app/engine/agentic_thread.py`

`AgenticThread` loops: generate → parse → check stop → inject next prompt → repeat.
`should_continue()` and `build_next_prompt()` hot-reloaded per iteration.
Hard cap: `MAX_ITERATIONS = 20`.

---

### ✅ M7 — Raw Token Archive
**Files:** `app/engine/llm_thread.py`, `app/engine/agentic_thread.py`

Every token emitted via `new_raw_token` before the parser sees it.
Each generation writes a micro-timestamped `.tokens` file to `data/logs/raw/`.
Data persists even if generation is killed mid-stream.

---

### ✅ M8 — Hardware Scout & Model Registry
**Files:** `core/hardware_scout.py`, `data/model_registry.json`

`get_hardware_profile()` reads RAM, VRAM, storage.
`data/model_registry.json` defines 4 model tiers with RAM requirements and
context window sizes (4096 → 8192 → 16384 → 32768).
Note: self-upgrade functionality has been permanently removed (see M10 below).

---

### ✅ M9 — Auto-Loop Mode
**Files:** `app/ui/workspaces/workbench.py`

Loop checkbox in Workbench. When checked, send spawns `AgenticThread` instead
of `LLMThread`. Stop button sends `request_stop()` to the running thread.

---

### ~~M10 — Self-Upgrade Git Push~~ — REMOVED
`app/engine/upgrade_manager.py` has been permanently deleted.
Self-upgrade was cut because it introduced fragile git subprocess calls and
a push-conflict risk with no rollback. Hardware detection and model registry
remain (M8); automatic downloading will be reimplemented in Phase 3.4.

---

### ✅ M11 — Training Data Curator
**Files:** `app/utils/training_curator.py`, `app/ui/workspaces/workbench.py`

👍 Good response → `curator.save_example(source="thumbs_up")`.
✎ Correct response → user edits → saved as `source="corrected"`.
All data in `data/training/curated.jsonl` in Unsloth SFT format.

---

### ✅ M12 — Eval Harness
**Files:** `eval/harness.py`, `eval/graders.py`, `eval/run_eval.py`

5 graders: `exact_match`, `json_valid`, `keyword_hit`, `groundedness`, `not_in_context`.
CLI: `python eval/run_eval.py --dataset path/to/dataset.jsonl`.
Dry-run mode tests graders without model.

---

### ✅ M13 — Workflow Modes & Prompt Templates
**Files:** `core/workflows.py`, `core/prompt_templates.py`

4 workflows: `general_chat`, `document_extractor`, `grounded_answer`, `code_review`.
5 templates: `reasoning_minimal`, `gpt_structured`, `json_extractor`, `grounded_answer`, `code_review`.
Workflow selector in Workbench combo box.

---

### ✅ M14 — RAG Hardening
**Files:** `app/utils/rag_pipeline.py`

Persistent FAISS index with file-level metadata. Optional contextual chunk headers.
`source_filter` on `retrieve()`. Retrieval eval metrics built in.

---

### ✅ M15 — Training Path Formalisation
**Files:** `training/validate_dataset.py`, `training/qlora_config_template.yaml`, `training/WHEN_TO_TUNE.md`

`validate_dataset.py` validates curated JSONL before training.
`qlora_config_template.yaml` ready for Unsloth.
`WHEN_TO_TUNE.md` decision guide.

---

### ✅ M16 — Multi-Workspace UI Rebuild
**Files:** `app/ui/`, `app/state.py`

Replaced two-page layout with sidebar + 6-workspace architecture.
Sidebar: Workbench, Prompt Lab, Knowledge Base, Training Studio, Eval Suite, System.
`AppState` shared state container. Single dark design system (`themes.py`).
`StatusBar`: always shows model name, generation state, RAM usage.

---

### ✅ M17 — Foundation Hardening
**Files:** `app/engine/model_loader.py`, `core/cognitive_parser.py`, `app/utils/trace_logger.py`

- `ModelLoader`: `threading.Lock()` eliminates race condition on `get_instance()`
- `cognitive_parser`: state machine replaces `str.split()`; handles any tag casing,
  multiple blocks, unclosed tags
- `trace_logger`: new Unsloth-compatible schema (`id`, `session_id`, `feedback`,
  `corrected_response`, `model`, `adapter`, `timing`); 50 MB log rotation

---

### ✅ M18 — VS Code / Code OSS Bridge
**Files:** `vscode-extension/extension.js`, `vscode-extension/package.json`,
`app/engine/websocket_server.py`, `app/engine/swarm_orchestrator.py`,
`tests/test_websocket_bridge.py`

Karl now has an editor-facing WebSocket bridge and VS Code / Code OSS extension.
The extension exposes the local swarm, chat, live introspection stream, prompt
lab diffing, Codex reference library, and basic generation overrides. Agent file
edits open in the VS Code diff editor and can be accepted or rolled back.

This is the foundation for the full editor-native Karl experience: model
selection, RAG controls, evals, LoRA/QLoRA training, adapter loading, and local
self-maintaining code agents controlled from the editor while all heavy work
continues to run inside Karl.

---

## Completed Phase Plan

The phases below are preserved as the historical build plan. They are complete
as of the current repo state.

---

### Phase 1 — Wire It Together
**Strategy:** Single commit. All 6 items are targeted bug fixes in existing files.
No new components. No architecture changes.
**Risk:** Low.

| # | Task | File(s) |
|---|------|---------|
| 1.1 | Fix trace_logger call in LLMThread: pass `model_name`, `adapter_name`, `workflow`, `template` | `app/engine/llm_thread.py` |
| 1.2 | Fix trace_logger call in AgenticThread: same + fix synthetic `rag_context` | `app/engine/agentic_thread.py` |
| 1.3 | Model-aware context budget: `ModelLoader` reads `n_ctx` from `model_registry.json`; threads read from `ModelLoader` | `app/engine/model_loader.py`, both threads |
| 1.4 | Strip `<think>` blocks in `memory_manager.save_session()` | `app/utils/memory_manager.py` |
| 1.5 | Eval harness model guard: check `ModelLoader.is_loaded()` at top of `run()`; implement `progress_cb` call in case loop | `eval/harness.py` |
| 1.6 | Workbench params drawer: collapsible widget above input exposing temperature, top-p, max-tokens | `app/ui/workspaces/workbench.py` |

**Exit criteria:** All 6 items complete, tests pass, single clean commit.

---

### Phase 2 — Complete the Data Pipeline
**Strategy:** Single commit. All items wire existing components together.
**Risk:** Low-Medium.

| # | Task | File(s) |
|---|------|---------|
| 2.1 | Add `rag_threshold` and `rag_top_k` to `AppState`; KB workspace writes them; Workbench reads them at retrieve() | `app/state.py`, `knowledge_base.py`, `workbench.py` |
| 2.2 | Add thumbs-down button to Workbench feedback row; wire to `curator.save_example(source="thumbs_down")` | `app/ui/workspaces/workbench.py`, `app/utils/training_curator.py` |
| 2.3 | Connect `MemoryManager` to Workbench: sessions list panel, save on new session, load on click | `app/ui/workspaces/workbench.py` |
| 2.4 | Update `feedback` field in trace log when user rates a generation | `app/engine/llm_thread.py`, `app/ui/workspaces/workbench.py` |
| 2.5 | Normalise `training_curator.export_unsloth()` return to path string only (remove tuple) | `app/utils/training_curator.py`, `app/ui/workspaces/training_studio.py` |

**Exit criteria:** Full trace → curate → export → Unsloth-ready loop works end-to-end.

---

### Phase 2.5 — UX Polish Pass
**Strategy:** Four commits, one per workspace group. No new functionality in any of them.**
Must come after Phase 2. Phase 1 adds the params drawer (changes Workbench layout).
Phase 2 adds sessions panel and thumbs-down (changes Workbench layout again).
Polishing before these land means polishing twice.
**Risk:** None — layout and visual hierarchy changes only.

| Sub-phase | Scope | Workspaces |
|-----------|-------|-----------|
| 2.5a | Workbench layout, chat bubbles, input area, params drawer, sessions panel, feedback row | Workbench |
| 2.5b | Inspection tool polish, A/B column balance, KB source/inspector proportion | Knowledge Base, Prompt Lab |
| 2.5c | Data tool tab hierarchy, dataset row scannability, results tree columns | Training Studio, Eval Suite |
| 2.5d | System Config tabs + global consistency pass (margins, fonts, buttons, separators) | System Config + all |

**Rule for all 2.5 sub-phases:** If a change requires new logic, signals, or data — it belongs in a different phase. Every change is spacing, sizing, proportion, hierarchy, or clutter removal.

---

### Phase 3.1 — Small Workspace Fixes
**Strategy:** Single commit. Mechanical additions to two workspaces.
**Risk:** Low.

| # | Task | File(s) |
|---|------|---------|
| 3.1a | KB workspace: add chunk_size and overlap spinboxes; pass to `ingest_file()` | `app/ui/workspaces/knowledge_base.py` |
| 3.1b | Eval Suite: connect `progress_cb` from `EvalSuiteWorkspace` to `harness.run()` | `eval/harness.py`, `app/ui/workspaces/eval_suite.py` |

---

### Phase 3.2 — Prompt Lab Completion
**Strategy:** Single commit. Self-contained UI feature.
**Risk:** Low-Medium.

| # | Task | File(s) |
|---|------|---------|
| 3.2a | After both A/B runs complete, render character-level diff of the two outputs | `app/ui/workspaces/prompt_lab.py` |
| 3.2b | Save/load named prompt pairs to `data/prompt_pairs/` | `app/ui/workspaces/prompt_lab.py` |

---

### Phase 3.3 — LoRA / QLoRA Training Thread
**Strategy:** Single commit. High-risk; isolated from other Phase 3 work.
**Risk:** High — new threading pattern, HF model dependency, optional deps.

Dependencies: `peft`, `trl`, `transformers`, `datasets`.
HF model weights must be present in `data/hf_models/`.

| # | Task | File(s) |
|---|------|---------|
| 3.3a | Detect HF model in `data/hf_models/`; show clear guide if absent | `app/ui/workspaces/training_studio.py` |
| 3.3b | `TrainingThread(QThread)` running `SFTTrainer` from `trl`; streams loss to log view | `app/ui/workspaces/training_studio.py` |
| 3.3c | Save trained adapter to `data/adapters/<name>/`; load adapter into ModelLoader | `app/engine/model_loader.py`, `app/ui/workspaces/training_studio.py` |
| 3.3d | QLoRA path: if `bitsandbytes` is available, offer 4-bit quantised training | `app/ui/workspaces/training_studio.py` |

**Exit criteria:** Training runs on a 5-example dataset, loss curve visible, adapter saved.

---

### Phase 3.4 — System Config Model Registry
**Strategy:** Single commit. Self-contained workspace enhancement.
**Risk:** Low.

| # | Task | File(s) |
|---|------|---------|
| 3.4a | Read `model_registry.json`; render tier table (name, RAM req, n_ctx, size) | `app/ui/workspaces/system_config.py` |
| 3.4b | Download button per tier: fetch GGUF to `data/models/`, show progress, set active | `app/ui/workspaces/system_config.py`, `app/engine/model_loader.py` |

---

### Phase 4.1 — Tokenizer Visualization
**Strategy:** Single commit. Self-contained display feature.
**Risk:** Low.

Expose `llm.tokenize(text)` from `llama-cpp-python`. Render tokens as colored
spans in a dedicated panel. Lives in Prompt Lab or as a drawer in Workbench.

| # | Task | File(s) |
|---|------|---------|
| 4.1a | Add tokenize panel: text input → token spans with IDs | `app/ui/workspaces/prompt_lab.py` |
| 4.1b | Color tokens by type (punctuation, word, subword, special) | same |

---

### Phase 4.2 — DPO Export Completion
**Strategy:** Single commit. Depends on Phase 2.2 (thumbs-down) being complete.
**Risk:** Low-Medium.

| # | Task | File(s) |
|---|------|---------|
| 4.2a | `training_curator` pairing algorithm: match thumbs-up (chosen) with thumbs-down (rejected) on same prompt | `app/utils/training_curator.py` |
| 4.2b | `export_dpo(path)` produces Unsloth-compatible DPO JSONL: `{prompt, chosen, rejected}` | `app/utils/training_curator.py`, `app/ui/workspaces/training_studio.py` |

**Exit criteria:** Exported DPO file loadable by Unsloth without modification.

---

### Phase 4.3 — Session Branching
**Strategy:** Single commit. Architecturally significant — isolated for safety.
**Risk:** High — changes `chat_history` from `list[dict]` to a tree structure.

This is the most architecturally complex item in the plan. `chat_history` currently
lives in `WorkbenchWorkspace` as a flat list. Branching requires it to become a tree
where each node can have multiple child turns. Plan carefully before touching code.

| # | Task | File(s) |
|---|------|---------|
| 4.3a | Design `SessionTree` data structure: node = `{role, content, children[], id}` | new `app/utils/session_tree.py` |
| 4.3b | Replace flat `chat_history` list in `WorkbenchWorkspace` with `SessionTree` | `app/ui/workspaces/workbench.py` |
| 4.3c | "Branch from here" action on any message in chat view | `app/ui/workspaces/workbench.py` |
| 4.3d | Branch navigator: show tree of branches, switch between them | `app/ui/workspaces/workbench.py` |
| 4.3e | `MemoryManager` serialise/deserialise `SessionTree` | `app/utils/memory_manager.py` |

**Exit criteria:** User can fork any message, explore alternate path, return to original.

---

### Phase 5 — Documentation, Tests, Accuracy
**Strategy:** Single commit. No code risk.
**Risk:** None.

| # | Task | File(s) |
|---|------|---------|
| 5.1 | Rewrite `README.md` for Linux/Arch: remove all PowerShell, add Arch-specific install | `README.md` |
| 5.2 | Rewrite all 7 `docs/` files to match current architecture | `docs/01–07` |
| 5.3 | Update `AGENTS.md` to reflect final completed state | `AGENTS.md` |
| 5.4 | Write unit tests: `cognitive_parser`, `trace_logger`, `training_curator` | `tests/` (new) |
| 5.5 | Fix `smoke_test.py` and `engine_test.py` hardcoded model paths | root |

---

## Milestone Summary Table

| ID | Name | Status |
|----|------|--------|
| M1 | Headless Introspection Engine | ✅ Done |
| M2 | Streaming Thought/Response Split | ✅ Done |
| M3 | Memory & Context Management | ✅ Done |
| M4 | Universal RAG Pipeline | ✅ Done |
| M5 | Hackable Core Decoupling | ✅ Done |
| M6 | Agentic Loop | ✅ Done |
| M7 | Raw Token Archive | ✅ Done |
| M8 | Hardware Scout & Model Registry | ✅ Done |
| M9 | Auto-Loop Mode | ✅ Done |
| M10 | Self-Upgrade Git Push | ~~Removed~~ |
| M11 | Training Data Curator | ✅ Done |
| M12 | Eval Harness | ✅ Done |
| M13 | Workflow Modes & Prompt Templates | ✅ Done |
| M14 | RAG Hardening | ✅ Done |
| M15 | Training Path Formalisation | ✅ Done |
| M16 | Multi-Workspace UI Rebuild | ✅ Done |
| M17 | Foundation Hardening | ✅ Done |
| M18 | VS Code / Code OSS Bridge | ✅ Done |
| — | Phase 1: Wire It Together | ✅ Done |
| — | Phase 2: Data Pipeline | ✅ Done |
| — | Phase 2.5a: UX Polish — Workbench | ✅ Done |
| — | Phase 2.5b: UX Polish — KB + Prompt Lab | ✅ Done |
| — | Phase 2.5c: UX Polish — Training + Eval | ✅ Done |
| — | Phase 2.5d: UX Polish — System + Global | ✅ Done |
| — | Phase 3.1: Small Workspace Fixes | ✅ Done |
| — | Phase 3.2: Prompt Lab Completion | ✅ Done |
| — | Phase 3.3: LoRA/QLoRA Training | ✅ Done |
| — | Phase 3.4: Model Registry Browser | ✅ Done |
| — | Phase 4.1: Tokenizer Visualization | ✅ Done |
| — | Phase 4.2: DPO Export Completion | ✅ Done |
| — | Phase 4.3: Session Branching | ✅ Done |
| — | Phase 5: Docs, Tests, Accuracy | ✅ Done |

---

## Next Product Horizon — Full Karl In VS Code

The next major product direction is to expose the complete Karl app through the
VS Code extension without duplicating the Python runtime in the extension host.
The PyQt app remains the local engine and system tray/control process; the
extension becomes a first-class editor shell over the same local APIs.

Priority order:

| Priority | Capability | Practical target |
|----------|------------|------------------|
| 1 | Runtime status | Extension shows active model, adapter, RAM/VRAM, bridge state, generation state. |
| 2 | Model registry | Extension can list installed GGUF files, show registry tiers, and set active model. |
| 3 | Prompt Lab parity | Extension can save/load prompt pairs and run A/B comparisons with diff output. |
| 4 | Knowledge Base parity | Extension can ingest selected files/folders and test retrieval with top-k/threshold controls. |
| 5 | Training Studio parity | Extension can browse curated examples, export SFT/DPO, start LoRA/QLoRA training, stream loss, and load adapters. |
| 6 | Eval Suite parity | Extension can run local eval datasets and show grader results. |
| 7 | Agent transactions | Multi-file swarm edits are grouped under task IDs with accept-all/rollback-all. |
| 8 | Self-maintenance loop | Local agents can inspect Karl's own code, propose upgrades, run tests, and hand the diff to the user for approval. |

Non-negotiable constraints:

- Inference remains local.
- Training remains local.
- RAG data remains local.
- The extension never sends user code or traces to a remote service.
- Agent writes remain inspectable and reversible.
- Git push, dependency installation, and destructive filesystem operations
  require explicit user approval.

The detailed extension architecture and JSON-RPC roadmap live in
[`docs/08_vscode_extension.md`](08_vscode_extension.md).
