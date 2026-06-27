# Karl UI Architecture

Karl's desktop shell is a PyQt6 `QMainWindow` with a fixed-width sidebar, a
`QStackedWidget` workspace router, and a persistent status bar.

## Shell Coordinates

| Area | File | Notes |
|------|------|-------|
| Main shell | `app/ui/main_window.py` | Owns `AppState`, creates workspaces, connects status/model/theme signals, starts deferred model and WSS startup. |
| Sidebar | `app/ui/sidebar.py` | Fixed 56 px navigator with ten accessible workspace buttons. |
| Status bar | `app/ui/widgets/status_bar.py` | Shows model, adapter, generation state, context stats, and hardware summary. |
| Theme engine | `app/ui/themes.py` | Theme palettes plus dynamically compiled QSS. |

`MainWindow._build_ui()` adds workspaces to the stack in the same order emitted
by `Sidebar.workspace_changed`.

## Active Workspaces

| Index | Sidebar Label | Widget | File |
|-------|---------------|--------|------|
| 0 | Workbench | `WorkbenchWorkspace` | `app/ui/workspaces/workbench/workspace.py` |
| 1 | Prompt Lab | `PromptLabWorkspace` | `app/ui/workspaces/prompt_lab.py` |
| 2 | Knowledge | `KnowledgeBaseWorkspace` | `app/ui/workspaces/knowledge_base.py` |
| 3 | Vision | `VisionWorkbench` | `app/ui/workspaces/vision_workbench.py` |
| 4 | Training | `TrainingStudioWorkspace` | `app/ui/workspaces/training_studio/__init__.py` |
| 5 | Eval | `EvalSuiteWorkspace` | `app/ui/workspaces/eval_suite.py` |
| 6 | Swarm | `SwarmStudioWorkspace` | `app/ui/workspaces/swarm_studio.py` |
| 7 | System | `SystemConfigWorkspace` | `app/ui/workspaces/system_config/workspace.py` |
| 8 | Codex | `DocsWorkspace` | `app/ui/workspaces/docs.py` |
| 9 | Flywheel | `FlywheelStudioWorkspace` | `app/ui/workspaces/flywheel_studio.py` |

Keyboard routing is owned by `MainWindow._setup_shortcuts()`: `Ctrl+1` through
`Ctrl+9` select indexes 0-8, and `Ctrl+0` selects Flywheel.

## Theme System

`app/ui/themes.py` defines named palettes in `THEMES`, with `PALETTE` aliased to
`Karl Obsidian Core`. The public theme APIs are:

```python
get_theme_colors(state_or_name, custom_accent=None, bg_tone="Default", mode=None) -> dict
get_theme_stylesheet(state_or_name, custom_accent=None, bg_tone="Default", mode=None) -> str
stylesheet(accent=ACCENT_DEFAULT, mode="midnight") -> str
```

Each palette exposes the base keys `accent`, `accent_alt`, `bg_deep`,
`bg_surface`, `bg_raised`, `border`, `border_hi`, `text_hi`, `text_mid`,
`text_lo`, `success`, `warning`, `danger`, `glow_strength`, and `motion_style`.
`get_theme_colors()` expands those into QSS-facing keys such as `bg_base`,
`bg_input`, `think_bg`, `think_text`, `sidebar_bg`, `sidebar_sel`,
`bg_surface_glass`, `border_glass`, `idle_border`, `generating_border`, and
`error_border`.

The default layout preset is `Focused Workbench`, which compiles to 12 px outer
workspace padding and 10 px standard spacing. Other presets intentionally change
density: `Compact Laptop`, `Wide Monitor Command`, and `Minimal Distraction`.

## QSS Object Names

The QSS contract is object-name based. Workspaces and widgets should reuse these
names instead of ad hoc inline styling where possible:

| Object Name | Purpose |
|-------------|---------|
| `workspace-root` | Top-level workspace background and model-state border. |
| `sidebar`, `sidebar-btn`, `sidebar-logo` | Navigation rail and active button styling. |
| `panel` | Framed utility panels and repeated cards. |
| `section-header` | Small uppercase section labels. |
| `lbl-accent`, `lbl-muted`, `lbl-green`, `lbl-red` | Semantic label emphasis. |
| `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`, `btn-success`, `btn-warning`, `btn-icon` | Button hierarchy and intent. |
| `reasoning-view`, `chat-view` | Streaming text surfaces. |
| `tabs`, `inspector-tabs` | Tab containers. |
| `line`, `splitter` | Separators and split handles. |

Model runtime state is exposed through dynamic properties such as
`modelState="idle"`, `modelState="generating"`, and `modelState="error"` on
`workspace-root`, panels, and overlays.

## Accessibility

Sidebar buttons call `setAccessibleName()` with `Workspace Navigator: <label>`
and `setAccessibleDescription()` with the target workspace description.
Workbench custom icon buttons, including the settings drawer toggle, also set
accessible names/descriptions where the icon alone would be ambiguous.

Reusable custom symbols live in `app/ui/widgets/symbolic_icon.py`. `IconBtn`
wraps a theme-aware painted `BaseSymbol` subclass in a fixed-size `QPushButton`.
The button object name is `btn-ghost`, so icon controls inherit normal keyboard
focus, tooltip, enabled, and hover states from Qt and QSS.

## Workbench

`WorkbenchWorkspace` is a `QMainWindow` so it can host dock widgets:

| Component | File | Notes |
|-----------|------|-------|
| Workspace controller | `app/ui/workspaces/workbench/workspace.py` | Owns session tree, inference service, hyperparameters, docks, model selectors, and generation lifecycle. |
| Chat view | `app/ui/workspaces/workbench/chat_view.py` | Renders streamed user/assistant bubbles. |
| Session panel | `app/ui/workspaces/workbench/session_panel.py` | Lists saved sessions and drives session switching. |
| Branch panel | `app/ui/workspaces/workbench/branch_panel.py` | Displays session-tree branch navigation. |
| Params drawer | `app/ui/workspaces/workbench/params_drawer.py` and workspace overlay builder | Temperature, top-p, max tokens, RAG, scheduling, and feedback controls. |
| Feedback panel | `app/ui/workspaces/workbench/feedback_panel.py` | Thumbs up/down and correction affordances. |
| HUD toolbar | `app/ui/workspaces/workbench/hud_toolbar.py` | Dock visibility shortcuts and HUD state. |

The Workbench emits status/model/adapter/context signals back to `MainWindow`.
Generation is started through `InferenceService`, and tokens arrive through Qt
signals from `LLMThread` or `AgenticThread`.

## Knowledge Base

`KnowledgeBaseWorkspace` enables `setAcceptDrops(True)` and accepts dropped local
files with `.pdf`, `.docx`, `.txt`, `.md`, `.py`, or `.csv` extensions. Dropped
files are appended to the ingest queue and processed through the same queued
ingestion path as the Browse controls.

Primary tabs:

| Tab | Builder | Purpose |
|-----|---------|---------|
| Explorer | `_build_explorer_tab()` | Source list, source stats, and chunk inspection. |
| Ingest | `_build_ingest_tab()` | Queue, chunk size, overlap, and ingest status. |
| Search | `_build_search_tab()` | Query runner, top-k, threshold, and source filtering. |
| Sandbox | `_build_sandbox_tab()` | TF-IDF/vector projection visualization. |

`AppState.rag_top_k`, `AppState.rag_threshold`, and retrieval mode are updated by
the KB controls and read by Workbench generation.

## Prompt Lab

`PromptLabWorkspace` stores prompt pairs in `data/prompt_pairs/` and provides a
left-side saved-pair browser. The main panel contains:

| Tab | Purpose |
|-----|---------|
| A/B Playground | Side-by-side prompt/system/model execution columns. |
| Difference View | Character-level diff rendered by `generate_char_diff_html()`. |
| Tokenizer Visualizer | Calls the active model tokenizer and colors token spans. |
| Model Compare | Sequentially compares two GGUF models and restores the default model. |

The diff renderer uses `difflib.ndiff()` and highlights additions/deletions in
HTML. Saved pairs persist system prompts, user prompts, outputs, and rendered
diff state.

## Training And Eval

`TrainingStudioWorkspace` is tabbed:

| Tab | File | Purpose |
|-----|------|---------|
| Flywheel | `training_studio/flywheel_tab.py` | Training loop telemetry and flywheel stats. |
| Dataset | `training_studio/dataset_tab.py` | Curated example browser/import/delete. |
| Export | `training_studio/export_tab.py` | SFT and DPO JSONL export. |
| Train | `training_studio/train_tab.py` | LoRA/QLoRA config, dependency status, training progress/logs. |
| Auto-Train | `training_studio/auto_train_tab.py` | Automated training orchestration. |
| Mini-GPT Sandbox | `training_studio/mini_gpt_tab.py` | Small-model experimentation. |

`EvalSuiteWorkspace` uses a horizontal splitter: dataset controls and case list on
the left, result tree/detail panels on the right. It wires harness progress into
the progress bar and supports case editing plus grader selection.

## System Config

`SystemConfigWorkspace` is a mixin-composed tabbed controller:

| Tab | Mixin/File | Purpose |
|-----|------------|---------|
| Model | `model_panel.py` | Active model/adapter, speculative draft model, quantization controls. |
| Registry | `registry_panel.py` | Model registry browser, download, install, quantize actions. |
| Defaults | `defaults_panel.py` | Default generation hyperparameters, theme mode, log governance, auth, thermal settings. |
| Identity | `defaults_panel.py` | Persona/system identity text. |
| Vision | `vision_hardware_panel.py` | Vision model selection and state. |
| MCP | `mcp_panel.py` | MCP server configuration. |
| Theme | `appearance_panel.py` and `appearance_runtime.py` | Theme presets, custom accent, layout density, glow/motion/reduced-motion controls. |
| Observability | `observability_tab.py` | Aggregates average TTFT, TPS, KV hit rate, error count, and VRAM delta from logs. |
| Hardware | `vision_hardware_panel.py` | Live CPU/RAM/disk meters and hardware profile, refreshed every 2 seconds. |

Quantization jobs run in `QuantizerThread` and update progress/status controls in
the Model tab. Hardware monitoring is started by `SystemConfigWorkspace.__init__`
with a `QTimer` connected to `_update_live_hardware()`.
