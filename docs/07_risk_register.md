# Risk Register — Karl

Risks are assessed against the current codebase state.
Resolved risks are kept for history. Open risks have assigned phases.

---

## Active Risk Table

| ID | Category | Description | Impact | Likelihood | Status | Phase |
|----|----------|-------------|--------|------------|--------|-------|
| **R01** | Threading | **GUI Freeze on Inference:** `llama_cpp` blocks the calling thread. | Critical | High | ✅ Resolved | — |
| **R02** | Memory | **RAM Overflow on large models or long agentic loops.** | High | Medium | ✅ Mitigated | — |
| **R03** | Context | **Context Window Exhaustion:** history exceeds `n_ctx`. | High | High | ✅ Resolved | — |
| **R04** | User Error | **Bad Core Modifications:** syntax error in `core/` script. | High | High | ✅ Resolved | — |
| **R05** | Build | **`llama-cpp-python` compile failure** on native CPU. | Critical | High | ✅ Documented | — |
| **R06** | Data | **FAISS Index Corruption:** app closed during ingest. | Medium | Low | ✅ Mitigated | — |
| **R07** | Privacy | **Accidental Telemetry:** HuggingFace imports attempt network calls. | High | High | ✅ Mitigated | — |
| **R08** | Generation | **Early Cutoff:** Qwen EOS token not in stop list. | High | High | ✅ Resolved | — |
| **R09** | Generation | **Truncated Response:** model hits `max_tokens` mid-sentence. | Medium | Medium | ✅ Resolved | — |
| **R10** | Upgrade | **Git push conflict in upgrade manager.** | Medium | Low | ✅ Closed | — |
| **R11** | Eval | **Eval harness crashes with no model loaded.** | Medium | Medium | ⚠️ Open | Phase 1.5 |
| **R12** | Training | **Dataset Contamination:** bad examples exported for fine-tuning. | Medium | Low | ✅ Mitigated | — |
| **R13** | Threading | **ModelLoader race condition on `get_instance()`.** | High | Medium | ✅ Resolved | — |
| **R14** | Data | **`<think>` blocks accumulate in saved sessions.** | Medium | High | ⚠️ Open | Phase 1.4 |
| **R15** | Context | **Hardcoded `n_ctx=4096` wastes context on larger models.** | High | High | ⚠️ Open | Phase 1.3 |
| **R16** | Data | **Trace logs record `"model": "unknown"` for all generations.** | High | Certain | ⚠️ Open | Phase 1.1–1.2 |
| **R17** | Training | **DPO export has no rejected examples** — thumbs-down button absent. | High | Certain | ⚠️ Open | Phase 2.2 |
| **R18** | Architecture | **Session branching changes `chat_history` data model.** Doing it incrementally risks partial state. | High | Medium | ⚠️ Open | Phase 4.3 |
| **R19** | Build | **LoRA training requires HF model weights** not present by default. | High | High | ⚠️ Open | Phase 3.3 |
| **R20** | Architecture | **`AppState` is mutable shared state** with no locking. Concurrent workspace writes could corrupt. | Low | Low | ⚠️ Monitor | — |

---

## Resolved Risk Detail

**R01 — GUI Freeze**
Resolved by `LLMThread(QThread)` and `AgenticThread(QThread)`. Signals carry results
back to UI thread. Rule: never touch Qt widgets from inside `run()`.

**R02 — RAM Overflow**
Mitigated by `_trim_history()` in both threads. Character budget enforces
`(n_ctx - 1024) * 3` chars. Seed message always preserved. Exposed in Phase 1.3
when `n_ctx` becomes model-aware.

**R03 — Context Exhaustion**
Same mitigation as R02. Both threads trim before building prompt.

**R04 — Bad Core Modifications**
All `thread.run()` wrapped in `try/except Exception`. Error emitted via
`error_occurred(str)` signal. UI re-enables controls. Generation does not hang.

**R05 — Compile Failure**
Documented in README and AGENTS.md. Linux compile command:
`CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python --no-binary llama-cpp-python`

**R06 — FAISS Corruption**
`save_index()` writes FAISS file first, then metadata JSON. If either file
is missing or corrupt on load, `_load_index()` falls back to a fresh empty index
with a printed warning. No crash.

**R07 — Accidental Telemetry**
`main.py` sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and
`HF_HUB_DISABLE_TELEMETRY=1` before any imports run. The C-level stderr
redirect during heavy imports silences remaining noise.

**R08 — Early Cutoff**
Stop tokens `["<|im_end|>", "<|endoftext|>", "<|end_of_text|>", "<|im_start|>"]`
applied to both threads. `echo=False` prevents prompt echo.

**R09 — Truncated Response Chaining**
Both threads run generation inside a `while continuation_count <= 5` loop.
`finish_reason == "length"` triggers continuation with `raw_output` appended to prompt.
`ended_in_thought` flag passed so continuation resumes in correct parse state.

**R10 — Git Push Conflict in Upgrade Manager**
`app/engine/upgrade_manager.py` has been permanently deleted. Risk is closed.
Self-upgrade has been replaced with a model registry browser + manual download
(Phase 3.4).

**R12 — Dataset Contamination**
`training/validate_dataset.py` checks schema before training.
`training/WHEN_TO_TUNE.md` provides quality thresholds guidance.

**R13 — ModelLoader Race Condition**
Fixed. `threading.Lock()` added to `ModelLoader`. All three class methods
(`get_instance`, `reset_instance`, `is_loaded`) acquire the lock.

---

## Open Risk Detail

**R11 — Eval Harness Crash with No Model**
`eval/harness.py` `run()` calls `ModelLoader.get_instance()` inside the case loop.
If no model file exists, `FileNotFoundError` surfaces after "Running N cases" is
printed. Fix: add `ModelLoader.is_loaded()` guard at entry to `run()`, raise
`RuntimeError("no model loaded")` immediately. Assigned to Phase 1.5.

**R14 — `<think>` Blocks in Saved Sessions**
`memory_manager.save_session()` dumps raw `chat_history`. If history contains
`{"role": "assistant", "content": "<think>...</think>response"}`, the thinking
tokens are reinjected into context on reload. The model then re-reasons already-
completed thoughts, wasting tokens and producing inconsistent outputs.
Fix: strip `<think>...</think>` from all assistant content before writing.
Assigned to Phase 1.4.

**R15 — Hardcoded `n_ctx=4096`**
`model_loader.py` hardcodes `n_ctx=4096`. Both threads hardcode
`_CONTEXT_BUDGET = 4096`. `data/model_registry.json` defines per-model contexts
(4096 / 8192 / 16384 / 32768). A user loading the 14B tier model (16384 context)
has their history trimmed to 4096-token budget — wasting 12,000 tokens they paid
for in RAM. Fix: `ModelLoader` reads `n_ctx` from registry at load time and exposes
it as `ModelLoader.n_ctx()`. Threads call that instead of the hardcoded constant.
Assigned to Phase 1.3.

**R16 — `"model": "unknown"` in All Traces**
`llm_thread.py` and `agentic_thread.py` call `trace_logger.log_generation()` without
passing `model_name` or `adapter_name`. Every trace entry reads `"model": "unknown"`.
This breaks Unsloth export attribution and makes multi-model experiments
untrackable. Fix: pass `ModelLoader.model_name()` to the call.
Assigned to Phase 1.1–1.2.

**R17 — No Thumbs-Down / No Rejected Examples**
The DPO export in Training Studio attempts to pair chosen/rejected examples, but the
Workbench only has a thumbs-up button. There are no rejected examples to pair.
Fix: add thumbs-down button; wire to `curator.save_example(source="thumbs_down")`.
DPO export then pairs matching-prompt chosen + rejected entries.
Assigned to Phase 2.2.

**R18 — Session Branching Data Model Change**
`chat_history` is currently a flat `list[dict]` owned by `WorkbenchWorkspace`.
Session branching (Phase 4.3) requires it to become a tree.
Risk: if branching is implemented without isolating the change, partial state
(some code using list, some using tree) will cause silent corruption.
Mitigation: Phase 4.3 must introduce `SessionTree` in its own isolated commit
and replace all `chat_history` references atomically. Do not mix Phase 4.3
changes with any other work.

**R19 — LoRA Training Requires HF Weights**
Phase 3.3 LoRA training uses `peft` + `trl` `SFTTrainer`, which requires
HuggingFace model weights in `data/hf_models/`. The default Karl install only
has a GGUF file. Risk: Phase 3.3 code is written but untestable for most users.
Mitigation: Training Studio must detect absence of HF model, show a clear
download guide, and gracefully disable the Train button. Export (SFT/DPO)
must still work regardless.

**R20 — AppState Concurrent Write**
`AppState` is a plain Python object with mutable fields (`generating`, `model_name`,
`adapter_name`). If two workspaces write to the same field simultaneously from
different Qt threads, there is no lock. Currently low risk because only
`WorkbenchWorkspace` sets `generating` and only `SystemConfigWorkspace` sets
`model_name`, and these don't overlap. Monitor as Phase 3 adds more active workspaces.
If conflicts emerge, add `threading.Lock` to `AppState`.

---

## Open Risk Summary

| Risk | Fix | Phase |
|------|-----|-------|
| R11 — Eval harness crash | Add `is_loaded()` guard | Phase 1.5 |
| R14 — `<think>` in sessions | Strip on save | Phase 1.4 |
| R15 — Hardcoded `n_ctx` | Read from registry | Phase 1.3 |
| R16 — `"model": "unknown"` | Pass `ModelLoader.model_name()` | Phase 1.1–1.2 |
| R17 — No thumbs-down | Add button + wire | Phase 2.2 |
| R18 — Branching data model | Isolate in own commit | Phase 4.3 |
| R19 — LoRA needs HF weights | Detect + guide; degrade gracefully | Phase 3.3 |
| R20 — AppState concurrent write | Monitor; lock if needed | Ongoing |
