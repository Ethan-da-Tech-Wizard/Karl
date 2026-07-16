# Karl VS/OSS Code Extension

Karl adds a local high-end programming cockpit for the Karl desktop bridge, exposing real-time LLM introspection, offline RAG pipelines, and multi-iteration agentic swarm loops.

## Main Surfaces (11-Tab Webview)

- **Cockpit**: The central home view showing connection status, active workspace, active file, current git branch, pending changes count, diagnostics count, recent tasks history (click-to-rerun), and a Quick Actions launcher.
- **Chat**: Dedicated chat panel for direct assistant queries, live thought streaming, and conversation branch forks.
- **Swarm**: Swarm composition, workspace-wide objectives execution, agent timeline, and task queue management.
- **Changes**: The pending changes review bay for previewing, applying, rejecting, and rolling back code modifications.
- **Git**: Workspace branch display, diff review (staged, unstaged, and combined), and commit message generation.
- **Diag**: Diagnostics summary counts (errors, warnings, info, hints), grouped by file problem lists, and click-to-reveal navigation.
- **Knowledge**: Merges RAG index controls (ingestion queue, chunk configurations) and the seeded Codex Library.
- **Vision**: OCR and image caption analysis workflows, supporting active image reviews and error screenshots.
- **Lab**: A/B prompt comparisons, prompt pairs save/load, tokenizer previews, and character-level inline diff comparisons.
- **Settings**: Appearance presets (with dynamically rendered catalog previews), custom accent picker, VS Code theme sync, high-contrast, reduced motion, animation speed controls, and bridge port/hyperparameter configs.
- **Logs**: Swarm logs, fine-tuning loss outputs, and eval harness execution readouts.

## Look / Aesthetics System

The appearance tab supports twenty local visual presets matched to the desktop app. Previews are rendered as circular color dots showing the background, panel, border, and accent colors for each theme.
Additional controls include:
- **VS Code Theme Sync**: Mixes active VS Code colors into Karl's glass panel layouts.
- **High Contrast**: Toggles high-contrast layout borders.
- **Reduced Motion**: Disables scanning animations, glow transitions, and moving trace rails.
- **Animation Intensity Slider**: Scales key visual speed properties from 0% to 100%.

## Safety Model

Karl never overwrites files blindly. Swarm edits queue into the **Changes** review bay where they are categorized by risk level (based on line and byte deltas).
Buttons let you:
- **Preview Diff**: Opens VS Code's side-by-side diff comparing the original to the proposed code.
- **Apply File**: Copies a `.original` backup and writes the proposed changes.
- **Reject File**: Discards the proposed changes.
- **Rollback**: Restores the backup file if edits were already applied.
- **Preview All / Reject All / Copy Summary**: Group operations to speed up review.

## Commands

All commands are contributed to the Command Palette with predictable, keyboard-friendly labels:
- `Karl: Open Karl Panel`
- `Karl: Ask Karl to Refactor Selection`
- `Karl: Explain Selection`
- `Karl: Generate Tests for Active File`
- `Karl: Review Active File`
- `Karl: Review Staged Git Diff`
- `Karl: Review Unstaged Git Diff`
- `Karl: Review Combined Git Diff`
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
- `Karl: Analyze Image with Karl Vision`
- `Karl: Review Screenshot Error with Karl`

## Context Bounding

Before large files or diffs are packaged and sent, Karl estimates the context size. If it exceeds 30,000 characters, it prompts the user with a warning dialog allowing them to choose between sending full context, sending a bounded head/tail summary, or canceling.

## Bridge Connection

The extension communicates with the Karl desktop bridge over WebSockets. The status bar displays heartbeat age, connection states, model metadata, and supports reconnection count timers.
Default port: `8080`.
