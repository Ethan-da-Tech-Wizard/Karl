# Risk Register — Karl v2

| Risk ID | Category | Description | Impact | Likelihood | Status | Mitigation |
|---------|----------|-------------|--------|------------|--------|------------|
| **R01** | Threading | **GUI Freeze on Inference:** `llama_cpp` runs a blocking C-loop. Calling generation on the main PyQt thread causes "Not Responding." | Critical | High | ✅ Resolved | All inference runs inside `LLMThread(QThread)` or `AgenticThread(QThread)`. Signals (`new_thought_token`, `new_chat_token`, `new_raw_token`) stream results back to the UI thread safely. |
| **R02** | Memory | **RAM Overflow:** The 1.5B Q4 model requires ~1.1GB RAM. Larger models or long agentic loops with many RAG chunks can spike allocation. | High | Medium | ✅ Mitigated | `_trim_history()` enforces a character budget `(4096-1024)*3` chars. Seed message always preserved. Future: expose `n_ctx` in UI. |
| **R03** | Context | **Context Window Exhaustion:** Chat history exceeding 4096 tokens causes `llama_cpp` errors or hallucination. | High | High | ✅ Resolved | `_trim_history()` in both `LLMThread` and `AgenticThread` drops oldest messages when approaching budget. Emits a notice to the Diagnostic Lane when trimming occurs. |
| **R04** | User Error | **Bad Core Modifications:** User edits `core/interaction_loop.py` with a syntax error or infinite loop. | High | High | ✅ Resolved | All `thread.run()` methods are wrapped in `try/except Exception`. Error message is emitted via `error_occurred(str)` signal and displayed in red in the Final Response panel. UI controls are re-enabled. |
| **R05** | Build | **`llama-cpp-python` Compile Failure:** Pre-built wheels fail on Intel 12th Gen CPU with `Illegal Instruction (0xc000001d)`. | Critical | High | ✅ Documented | README and AGENTS.md document the source-compile command: `$env:CMAKE_ARGS="-DGGML_NATIVE=ON"; pip install llama-cpp-python --no-binary llama-cpp-python` |
| **R06** | Data | **FAISS Index Corruption:** App closed during ingestion leaves index and metadata out of sync. | Medium | Low | ✅ Mitigated | `save_index()` writes FAISS file first, then metadata JSON. If FAISS write fails, metadata is not written. On load, if either file is missing or corrupt, `_load_index()` falls back to a fresh empty index with a printed warning. |
| **R07** | Privacy | **Accidental Telemetry:** `sentence-transformers` / `huggingface_hub` attempt to contact HuggingFace at import time. | High | High | ✅ Mitigated | AGENTS.md documents setting `HF_HUB_OFFLINE=1`. The warning is cosmetic and does not break offline operation. Future: inject env vars in `main.py` before first import. |
| **R08** | Generation | **Early Generation Cutoff ("end of code"):** Qwen-derived models emit `<\|endoftext\|>` as their EOS token. If this is not in the stop list, `llama-cpp-python` passes it through and the model produces garbled short outputs. | High | High | ✅ Resolved | Stop tokens: `["<\|im_end\|>", "<\|endoftext\|>", "<\|end_of_text\|>"]`. `echo=False` prevents prompt echo. Applied to both `LLMThread` and `AgenticThread`. |
| **R09** | Generation | **Truncated Response Chaining:** Model hits `max_tokens` mid-sentence with `finish_reason == "length"`. | Medium | Medium | ✅ Resolved | `LLMThread` emits `generation_finished(truncated=True, ended_in_thought=bool)`. `MainWindow` fires a continuation `LLMThread` with `{"role": "user", "content": "Continue."}` appended. |
| **R10** | Upgrade | **Model Upgrade Data Loss:** `perform_upgrade()` runs `git push` which could fail if remote has diverged. | Medium | Low | ⚠️ Open | Currently no conflict resolution. Mitigation: upgrade manager should `git pull --rebase` before pushing. Tracked as technical debt. |
| **R11** | Eval | **Eval Harness Model Dependency:** `eval/harness.py` requires a loaded model to run. Running eval with no model produces an unhandled `FileNotFoundError`. | Low | Medium | ⚠️ Open | `eval/run_eval.py` should catch `FileNotFoundError` from `ModelLoader.get_instance()` and print a clear message. Tracked as technical debt. |
| **R12** | Training | **Dataset Contamination:** User exports training data and fine-tunes on bad examples (thumbs-up'd by mistake). | Medium | Low | ✅ Mitigated | `training/validate_dataset.py` checks schema and flags suspicious entries. `training/WHEN_TO_TUNE.md` guides the user on quality thresholds before running a fine-tuning job. |

---

## Open Risk Summary

| Risk | Action Required |
|---|---|
| R10 — Git push conflict on upgrade | Add `git pull --rebase` before `git push` in `upgrade_manager.perform_upgrade()` |
| R11 — Eval harness with no model | Add `FileNotFoundError` handling in `eval/run_eval.py` with a clear error message |
