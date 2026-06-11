# Karl VS/OSS Code Extension

Karl adds a local coding cockpit for the Karl desktop bridge.

## Main Surfaces

- **Workbench**: direct chat, live thought routing, branch tracking, quick actions,
  workspace tasks, refactors, reviews, and test-generation jobs.
- **Knowledge Base**: inspect RAG health, queue files or folders for batch ingest,
  and preview retrieval chunks with distance scores.
- **Prompt Lab**: run A/B prompt comparisons, save prompt pairs, sync prompt
  columns, and render diffs.
- **Training**: configure fine-tuning runs, adapter metadata, dataset paths, and
  loss-log surfaces. Runtime training actions show a bridge-required state until
  matching backend methods are exposed.
- **Eval**: configure benchmark datasets, progress/ETA display, log filtering,
  and summary export surfaces. Runtime eval actions require bridge harness methods.
- **System**: inspect runtime status, model registry entries, download tiers,
  RAM/context signals, and adapter compatibility warnings.
- **Codex**: browse local reference material exposed by Karl.
- **Review Bay**: review proposed file edits before applying them.
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

Recent upgrades add grouped review state, risk labels, reject-all, file opening,
path copying, and rollback for applied files when a `.original` backup exists.

## Commands

- `Karl: Open Karl Panel`
- `Karl: Ask Karl to Refactor Selection`
- `Karl: Explain Selection`
- `Karl: Generate Tests for Active File`
- `Karl: Review Active File`
- `Karl: Review Staged Git Diff`
- `Karl: Review Unstaged Git Diff`
- `Karl: Summarize Current Git Branch`
- `Karl: Explain Current Diagnostics`
- `Karl: Explain Active File Diagnostics`
- `Karl: Generate Commit Message from Staged Diff`
- `Karl: Create Implementation Plan from Selected Files`
- `Karl: Ask About Workspace`
- `Karl: Ingest Active File into Knowledge Base`
- `Karl: Ingest Workspace Folder into Knowledge Base`
- `Karl: Search Knowledge Base from Selection`
- `Karl: Send Current File to Swarm`
- `Karl: Open Pending Change Review Bay`

## Productivity Flow

The Workbench includes a Quick Actions launcher, recent objective history,
conversation branch tracking, context-size warnings, live thought routing, and a
lightweight task queue. Large files or diffs are packaged with a visible
bounded-context notice instead of being sent blindly.

The Knowledge Base keeps recent KB searches for fast reruns and supports a local
batch-ingestion queue. Bridge status shows heartbeat age, last connection time,
and bridge version when available.

The extension expects the Karl desktop bridge to be listening on the configured
`karl.port`, defaulting to `8080`.
