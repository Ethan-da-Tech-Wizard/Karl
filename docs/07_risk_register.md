# Risk Register

| ID | Category | Risk | Impact | Status | Mitigation |
|---|---|---|---|---|---|
| R01 | Threading | Running llama-cpp on the UI thread freezes the app. | Critical | Mitigated | All inference runs in `LLMThread` or `AgenticThread`; UI updates happen through signals. |
| R02 | Build | Prebuilt `llama-cpp-python` wheels can crash on the target Intel CPU. | Critical | Documented | Build from source with `CMAKE_ARGS="-DGGML_NATIVE=ON"`. |
| R03 | Context | Prompt plus generation can exceed the 4096-token model window. | High | Mitigated | Both engine threads use token-aware history trimming and max-token clamps. |
| R04 | User edits | A bad edit in `core/` can raise exceptions during generation. | High | Mitigated | Worker `run()` methods catch exceptions and emit UI errors; controls are re-enabled. |
| R05 | RAG index drift | FAISS index and metadata can become inconsistent if interrupted during persistence. | Medium | Partially mitigated | Load failures fall back to a fresh index with warnings. Future: atomic temp-file replace. |
| R06 | Privacy | Third-party libraries may try to contact HuggingFace at import/model-load time. | High | Mitigated | `main.py` sets offline and telemetry-disabling environment variables before heavy imports. |
| R07 | Output parsing | Split `<think>` tags can leak thought into response or response into thought. | High | Mitigated | Streaming parser uses open/close suffix guards and flushes final buffer. |
| R08 | Truncation | Responses can stop mid-answer at `max_tokens`. | Medium | Mitigated | Engine threads auto-continue internally for up to five passes when `finish_reason == "length"`. |
| R09 | Upgrade push | Model upgrade git push can fail if remote diverged. | Medium | Open | Add explicit pull/rebase or clear conflict guidance before push. |
| R10 | Dataset quality | User may tune on too few or low-quality examples. | Medium | Mitigated | `training/validate_dataset.py` exits nonzero for too few records and warns on balance/length issues. |
| R11 | DPO readiness | Current curator does not store rejected responses. | Medium | Open | Store original response alongside corrected response before implementing DPO export. |
| R12 | Raw-token UX | Raw chunks are archived but not visible in a live UI panel. | Low | Open | Planned tokenizer/raw-token view can expose `.tokens` files and logprobs. |
| R13 | Eval without model | Full eval mode requires a local GGUF and compiled llama-cpp. | Low | Mitigated | `--dry-run` validates graders without a model; full eval errors should be kept clear. |

## Open Technical Debt

- Add atomic writes for FAISS index/metadata persistence.
- Add a safer git sync path before model-upgrade push.
- Add DPO data capture before DPO export.
- Add live raw-token/logprob viewer.
- Add prompt-diff tooling over trace logs.
- Grow the curated dataset before any real fine-tuning run.
