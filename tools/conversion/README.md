# Vendored llama.cpp Conversion Helpers

This directory contains build-time conversion helper modules vendored from
`llama.cpp` for Karl's local GGUF/LoRA conversion tooling.

These files are not Karl runtime application code. Do not edit them as normal
`app/` modules, and do not rely on them as a stable Python API.

Provenance:

- Source project: <https://github.com/ggml-org/llama.cpp>
- Upstream llama.cpp commit: **unrecorded in the original vendoring commit**
- Karl import commit: `30215c8` (`Phase 3.3: Implement background SFT training thread...`)

If these helpers need an update, replace the directory from a known llama.cpp
commit and update the upstream commit line above in the same change.
