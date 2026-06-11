# Karl VS/OSS Code Extension

Karl adds a local coding cockpit for the Karl desktop bridge.

## Main Surfaces

- **Swarm**: compose workspace tasks, refactors, reviews, and test-generation jobs.
- **Chat**: ask Karl direct questions with live introspection streaming.
- **Changes**: review proposed file edits before applying them.
- **Knowledge**: ingest files or folders into Karl's local RAG index.
- **Lab**: run prompt A/B comparisons through the local bridge.
- **Models**: inspect and activate local model registry entries.
- **Codex**: browse local reference material exposed by Karl.
- **Look**: choose visual themes, custom accent colors, and cockpit layouts.

## Appearance

The extension ships with twenty local visual presets and a custom accent picker.
Themes are applied through CSS variables inside the webview and persisted per
workspace.

Theme presets:

- Karl Obsidian Core
- Abyssal Blue Engine
- Matrix Verdant
- White Lightning Lab
- Neon Circuit
- Arctic Mainframe
- Deep Space Console
- Quantum Teal
- Solar Flare Dark
- Red Team Ops
- Ghost Glass
- Midnight Compiler
- Hologram Blue
- Synthwave Control
- Monochrome Signal
- Emerald Archive
- Storm Grid
- Plasma Lab
- Stealth Operator
- God Mode Cyan

Layout modes:

- Cockpit
- Review Bay
- Swarm Ops
- Knowledge Scout
- Prompt Lab
- Compact Sidebar
- Wide Panel

## Safety Model

Karl no longer writes swarm edits immediately from bridge notifications. Proposed
edits enter the **Changes** queue first. Use **Preview** to open a diff against a
temporary proposed file, **Apply** to write the real file with a `.original`
backup, or **Reject** to discard the pending edit.

The review bay also supports previewing all pending files, copied patch summaries,
per-file status chips, byte counts, and line-count deltas.

## Commands

- `Karl: Open Karl Panel`
- `Karl: Ask Karl to Refactor Selection`
- `Karl: Explain Selection`
- `Karl: Generate Tests for Active File`
- `Karl: Review Active File`
- `Karl: Review Staged Git Diff`
- `Karl: Explain Current Diagnostics`
- `Karl: Generate Commit Message from Staged Diff`
- `Karl: Create Implementation Plan from Selected Files`
- `Karl: Ask About Workspace`
- `Karl: Ingest Active File into Knowledge Base`
- `Karl: Ingest Workspace Folder into Knowledge Base`
- `Karl: Search Knowledge Base from Selection`
- `Karl: Send Current File to Swarm`
- `Karl: Open Pending Change Review Bay`

The extension expects the Karl desktop bridge to be listening on the configured
`karl.port`, defaulting to `8080`.
