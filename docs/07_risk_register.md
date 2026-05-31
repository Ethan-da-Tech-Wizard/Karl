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
| **R11** | Eval | **Eval harness crashes with no model loaded.** | Medium | Medium | ✅ Resolved | Phase 1.5 |
| **R12** | Training | **Dataset Contamination:** bad examples exported for fine-tuning. | Medium | Low | ✅ Mitigated | — |
| **R13** | Threading | **ModelLoader race condition on `get_instance()`.** | High | Medium | ✅ Resolved | — |
| **R14** | Data | **`<think>` blocks accumulate in saved sessions.** | Medium | High | ✅ Resolved | Phase 1.4 |
| **R15** | Context | **Hardcoded `n_ctx=4096` wastes context on larger models.** | High | High | ✅ Resolved | Phase 1.3 |
| **R16** | Data | **Trace logs record `"model": "unknown"` for all generations.** | High | Certain | ✅ Resolved | Phase 1.1–1.2 |
| **R17** | Training | **DPO export has no rejected examples** — thumbs-down button absent. | High | Certain | ✅ Resolved | Phase 2.2 |
| **R18** | Architecture | **Session branching changes `chat_history` data model.** Doing it incrementally risks partial state. | High | Medium | ✅ Resolved | Phase 4.3 |
| **R19** | Build | **LoRA training requires HF model weights** not present by default. | High | High | ✅ Resolved | Phase 3.3 |
| **R20** | Architecture | **`AppState` is mutable shared state** with no locking. Concurrent workspace writes could corrupt. | Low | Low | ✅ Monitor | — |

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

**R11 — Eval Harness Crash with No Model**
Fixed in Phase 1.5. `eval/harness.py` `run()` now calls `ModelLoader.is_loaded()`
at entry; if absent, calls `get_instance()` and raises a descriptive `RuntimeError`
before the case loop begins. `progress_cb(current, total)` is also called inside
the loop.

**R12 — Dataset Contamination**
`training/validate_dataset.py` checks schema before training.
`training/WHEN_TO_TUNE.md` provides quality thresholds guidance.

**R13 — ModelLoader Race Condition**
Fixed. `threading.Lock()` added to `ModelLoader`. All three class methods
(`get_instance`, `reset_instance`, `is_loaded`) acquire the lock.

**R14 — `<think>` Blocks in Saved Sessions**
Fixed in Phase 1.4. `memory_manager.save_session()` strips all
`<think>...</think>` blocks (case-insensitive, DOTALL) from assistant messages
before writing to disk. Also applied recursively during `SessionTree` serialization.

**R15 — Hardcoded `n_ctx=4096`**
Fixed in Phase 1.3. `ModelLoader` reads `n_ctx` from `data/model_registry.json`
for the loaded model filename. Exposes `ModelLoader.n_ctx() -> int`. Both threads
call `ModelLoader.n_ctx()` for the trim budget instead of the old hardcoded constant.
Covers 4 tiers: 4096 / 8192 / 16384 / 32768.

**R16 — `"model": "unknown"` in All Traces**
Fixed in Phase 1.1–1.2. Both `llm_thread.py` and `agentic_thread.py` now pass
`model_name=ModelLoader.model_name()`, `adapter_name`, `workflow`, and `template`
to `trace_logger.log_generation()`. The agentic thread also no longer injects
synthetic `rag_context=[f"agentic_iteration_{n}"]`.

**R17 — No Thumbs-Down / No Rejected Examples**
Fixed in Phase 2.2. Workbench feedback row now has a 👎 button wired to
`curator.save_example(source="thumbs_down")`. Phase 4.2 completed the DPO pairing
algorithm in `training_curator.export_dpo()`.

**R18 — Session Branching Data Model Change**
Resolved in Phase 4.3. `chat_history` was atomically replaced with `SessionTree`
in a single isolated commit. No partial state was introduced. All `chat_history`
references were updated in one pass: `WorkbenchWorkspace`, `MemoryManager`,
`LLMThread`, `AgenticThread`.

**R19 — LoRA Training Requires HF Weights**
Resolved in Phase 3.3. Training Studio detects absence of HF model in
`data/hf_models/` and shows a clear download guide, disabling the Train button.
Export (SFT/DPO JSONL) functions independently of HF weights. `TrainingThread`
runs `trl.SFTTrainer` when weights are present; trained adapters are saved to
`data/adapters/<name>/`.

---

## Open Risk Summary

| Risk | Status |
|------|--------|
| R20 — AppState concurrent write | Monitor — low probability, no lock needed yet |

All other risks are resolved. See resolved detail above.
