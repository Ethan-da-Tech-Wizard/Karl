"""
Workbench — primary interaction space.

Layout:
  ┌─────────────────────────────────────────────────┐
  │  [reasoning panel]  │  [chat history]           │
  │  live <think> stream│  user + assistant messages │
  │                     │  ─────────────────────────│
  │                     │  [input area]              │
  │                     │  [controls row]            │
  └─────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QTextBrowser, QTextEdit, QComboBox,
    QLabel, QFrame, QCheckBox,
    QDoubleSpinBox, QSpinBox, QListWidget,
    QTreeWidget, QTreeWidgetItem, QMainWindow, QDockWidget,
    QTabWidget, QLineEdit, QMenu, QInputDialog, QMessageBox, QColorDialog,
    QApplication, QProgressBar, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QRect, QPropertyAnimation
from PyQt6.QtGui import QTextCursor, QKeySequence, QShortcut, QColor


from app.engine.inference_service import InferenceService
from app.engine.image_analysis_thread import ImageAnalysisThread
from app.engine.model_loader import CircuitBreakerOpenException
from app.engine import hot_reload
from core.workflows import list_workflows
from app.utils.session_tree import SessionTree
from app.ui.widgets.tracing_panel import TracingPanel
from app.ui.themes import get_theme_colors
from app.ui.widgets.symbolic_icon import IconBtn, GearIcon, HamburgerIcon, BrainIcon
from app.ui.widgets.toast import ToastOverlay

from app.ui.workspaces.workbench.chat_view import ChatView
from app.ui.workspaces.workbench.profiles import AGENT_PROFILES
from app.utils.correlation_logger import new_correlation_id, set_correlation_id


logger = logging.getLogger("karl.workbench")


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _label(text: str, obj: str = "") -> QLabel:
    lbl = QLabel(text)
    if obj:
        lbl.setObjectName(obj)
    return lbl


# ── chat display ─────────────────────────────────────────────────────────────


# ── workbench workspace ───────────────────────────────────────────────────────

class WorkbenchWorkspace(QMainWindow):
    """Primary chat workspace with dockable sessions, reasoning, and RAG HUDs."""

    status_changed = pyqtSignal(str, bool)   # (text, active)
    model_changed = pyqtSignal(str)          # (model_name)
    adapter_changed = pyqtSignal(str)        # (adapter_name)
    appearance_requested = pyqtSignal()
    context_stats = pyqtSignal(int, int, int, int) # (total, hist, rag, budget)

    def __init__(self, state, parent=None):
        """Initialize Workbench state, session tree, generation params, and docks."""
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")

        self._inference_service = InferenceService(state)
        self.chat_history = SessionTree()
        self._thread = None
        self._active_threads: set = set()
        self._last_response = ""
        self._last_thought = ""
        self._hyperparams = {
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 2048,
            "enable_dynamic_scheduling": getattr(self.state, "enable_dynamic_scheduling", True),
            "thinking_temperature": getattr(self.state, "thinking_temperature", 0.8),
            "answering_temperature": getattr(self.state, "answering_temperature", 0.1),
        }
        self._system_prompt = (
            "You are Karl, a precise and thoughtful AI assistant. "
            "Always respond in English. "
            "Analyze and break down problems step-by-step. "
            "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
            "Double-check your derivations and arithmetic before writing the final answer."
        )
        self._agent_profile = "karl"
        self._current_session_file: str | None = None
        self._session_id: str | None = None
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)  # 30s
        self._autosave_timer.timeout.connect(self._autosave_session)
        self._autosave_timer.start()
        self._is_correcting = False
        self._pending_image_attachments: list[dict] = []
        self._pending_generation_history: list[dict] | None = None
        self._image_threads = set()

        self.setProperty("modelState", "idle")
        self._settings_overlay = None
        self._responsive_mode: str | None = None

        self._build_ui()

        # Set up dynamic glow effects & pulse timer
        self._setup_glow_effects()
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow_pulse)
        self._glow_val = 0.0
        self._glow_dir = 1
        if getattr(self.state, "reduced_motion", False):
            self._glow_timer.stop()
        else:
            self._glow_timer.start(50)

        # Intercept setHtml for chat bubble fade-in animations
        self._setup_chat_animations()
        
        # Initialize dynamic chat bubble colors from theme config
        from app.ui.themes import get_theme_colors
        self._chat_view.set_theme(get_theme_colors(self.state))

        self._connect_shortcuts()
        self._refresh_sessions()
        self._refresh_model_combo()
        self._update_expert_strip()
        self._update_token_budget()
        QTimer.singleShot(0, lambda: self._apply_responsive_layout(self.width()))

        # Hot-reload global signals
        hot_reload.signals.reload_success.connect(self._on_reload_success)
        hot_reload.signals.reload_failed.connect(self._on_reload_failed)


    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        """Build chat center panel and dockable sessions/reasoning/RAG/context HUDs."""
        # Set central widget
        self._chat_panel = self._build_chat_panel()
        self.setCentralWidget(self._chat_panel)

        # Build Sessions Dock
        self._sessions_dock = QDockWidget("SESSIONS", self)
        self._sessions_dock.setObjectName("sessions-dock")
        self._sessions_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._sessions_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._sessions_panel = self._build_sessions_panel()
        self._sessions_dock.setWidget(self._sessions_panel)

        # Build Reasoning Dock
        self._reasoning_dock = QDockWidget("REASONING", self)
        self._reasoning_dock.setObjectName("reasoning-dock")
        self._reasoning_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._reasoning_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._reasoning_panel = self._build_reasoning_panel()
        self._reasoning_dock.setWidget(self._reasoning_panel)

        # Dock Nesting and layout initialization
        self.setDockNestingEnabled(True)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._sessions_dock)
        self.splitDockWidget(self._sessions_dock, self._reasoning_dock, Qt.Orientation.Horizontal)
        self.resizeDocks([self._sessions_dock, self._reasoning_dock], [200, 280], Qt.Orientation.Horizontal)
        self._sessions_dock.hide()
        self._reasoning_dock.hide()

        # Build settings overlay (this creates all hyperparam and feedback buttons)
        self._build_settings_overlay()
        
        # Populate HUD views toolbar
        self._populate_hud_toolbar()

    def _build_sessions_panel(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setObjectName("left-tabs")
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Tab 1: Sessions
        sessions_tab = QWidget()
        sl = QVBoxLayout(sessions_tab)
        sl.setContentsMargins(4, 4, 4, 4)
        sl.setSpacing(4)
        
        self._session_search = QLineEdit()
        self._session_search.setPlaceholderText("Search sessions...")
        self._session_search.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #1F1F3D; border-radius: 4px; "
            "color: #F0F5FF; font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; padding: 4px;"
        )
        self._session_search.textChanged.connect(self._filter_sessions)
        sl.addWidget(self._session_search)

        self._sessions_list = QListWidget()
        self._sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._sessions_list.customContextMenuRequested.connect(self._show_session_context_menu)
        self._sessions_list.currentItemChanged.connect(self._on_session_clicked)
        sl.addWidget(self._sessions_list, 1)
        tabs.addTab(sessions_tab, "Sessions")
        
        # Tab 2: Branches

        branches_tab = QWidget()
        bl = QVBoxLayout(branches_tab)
        bl.setContentsMargins(4, 4, 4, 4)
        bl.setSpacing(4)
        self._branch_stats_lbl = QLabel("Branches: 0 · Depth: 0 · Active: root")
        self._branch_stats_lbl.setObjectName("lbl-muted")
        self._branch_stats_lbl.setWordWrap(True)
        bl.addWidget(self._branch_stats_lbl)
        self._branch_focus_btn = QPushButton("Fork From Selected")
        self._branch_focus_btn.setObjectName("btn-ghost")
        self._branch_focus_btn.setToolTip("Move the active conversation cursor to the selected message and continue a new branch from there.")
        self._branch_focus_btn.clicked.connect(self._branch_from_selected_tree_item)
        bl.addWidget(self._branch_focus_btn)
        self._branches_tree = QTreeWidget()
        self._branches_tree.setHeaderHidden(True)
        self._branches_tree.itemClicked.connect(self._on_branch_clicked)
        bl.addWidget(self._branches_tree, 1)
        tabs.addTab(branches_tab, "Branches")
        
        return tabs

    def _build_reasoning_panel(self) -> QWidget:
        self._reasoning_panel_container = TracingPanel(self.state, self)
        self._reasoning_panel_container.setObjectName("panel")
        accent = get_theme_colors(self.state).get("accent", "#00C2FF")
        self._reasoning_panel_container.set_accent_color(accent)
        
        layout = QVBoxLayout(self._reasoning_panel_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Place the stats label directly in the layout with padding
        self._reasoning_stats_lbl = QLabel("")
        self._reasoning_stats_lbl.setObjectName("lbl-muted")
        self._reasoning_stats_lbl.setStyleSheet("font-weight: normal; font-size: 8pt; padding: 4px 10px;")
        layout.addWidget(self._reasoning_stats_lbl)

        self._reasoning_view = QTextBrowser()
        self._reasoning_view.setObjectName("reasoning-view")
        self._reasoning_view.setReadOnly(True)
        self._reasoning_view.setPlaceholderText("reasoning tokens will appear here...")
        layout.addWidget(self._reasoning_view, 1)

        return self._reasoning_panel_container

    def _build_chat_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # expert control strip
        self._expert_strip = self._build_expert_strip()
        layout.addWidget(self._expert_strip)

        self._command_header = self._build_command_header()
        layout.addWidget(self._command_header)

        # HUD Toolbar placeholder (populated at the end of _build_ui)
        self._hud_toolbar = QFrame()
        self._hud_toolbar.setObjectName("hud-toolbar")
        self._hud_toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._hud_toolbar)

        # chat display
        self._chat_view = ChatView(w)
        self._chat_view.anchorClicked.connect(self._on_chat_link_clicked)
        self._chat_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._chat_view, 1)

        # Hot-reload notice banner (hidden until a generation triggers a reload)
        self._reload_notice = QLabel("")
        self._reload_notice.setObjectName("reload-notice")
        self._reload_notice.setVisible(False)
        self._reload_notice.setStyleSheet(
            "background: #0F1D36; color: #7EC8E3; font-size: 8pt; "
            "padding: 2px 10px; border-left: 2px solid #7EC8E3;"
        )
        self._reload_hide_timer = QTimer(self)
        self._reload_hide_timer.setSingleShot(True)
        self._reload_hide_timer.timeout.connect(lambda: self._reload_notice.setVisible(False))
        layout.addWidget(self._reload_notice)

        # Context HUD bar — shows token budget usage
        self._context_bar = QProgressBar()
        self._context_bar.setRange(0, 100)
        self._context_bar.setValue(0)
        self._context_bar.setFixedHeight(10)
        self._context_bar.setTextVisible(True)
        self._context_bar.setFormat("Connect a model to see context usage")
        self._context_bar.setStyleSheet("QProgressBar { font-size: 7.5pt; } QProgressBar::chunk { background: #2DD4A0; }")
        self._context_bar.setVisible(False)
        layout.addWidget(self._context_bar)

        # RAG attribution panel — shown after each generation that used RAG
        self._rag_sources_view = QTextBrowser()
        self._rag_sources_view.setFixedHeight(120)
        self._rag_sources_view.setVisible(False)
        self._rag_sources_view.setObjectName("panel")
        layout.addWidget(self._rag_sources_view)

        # input area
        input_container = QFrame()
        input_container.setObjectName("chat-composer")
        input_container.setFixedHeight(124)
        input_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._input_container = input_container
        ic_layout = QVBoxLayout(input_container)
        ic_layout.setContentsMargins(10, 8, 10, 8)
        ic_layout.setSpacing(5)

        # Token Budget HUD
        self._token_row = QWidget()
        self._token_row.setObjectName("token-row")
        token_layout = QHBoxLayout(self._token_row)
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.setSpacing(8)

        self._token_lbl = QLabel("0 / 4,096 tokens")
        self._token_lbl.setObjectName("lbl-muted")
        self._token_lbl.setStyleSheet("font-size: 8pt;")
        self._token_remaining_lbl = QLabel("free 4,096")
        self._token_remaining_lbl.setObjectName("lbl-muted")
        self._token_remaining_lbl.setStyleSheet("font-size: 8pt;")

        self._token_bar = QProgressBar()
        self._token_bar.setObjectName("token-budget-bar")
        self._token_bar.setFixedHeight(6)
        self._token_bar.setTextVisible(False)
        self._token_bar.setRange(0, 100)
        self._token_bar.setValue(0)

        token_layout.addWidget(self._token_bar, 1)
        token_layout.addWidget(self._token_lbl)
        token_layout.addWidget(self._token_remaining_lbl)

        ic_layout.addWidget(self._token_row)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Ask Karl...")
        self._input.setFixedHeight(58)
        self._input.installEventFilter(self)
        self._input.textChanged.connect(self._update_token_budget)
        ic_layout.addWidget(self._input)

        # controls
        ctrl = QWidget()
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        self._workflow_combo = QComboBox()
        self._workflow_combo.setMinimumWidth(116)
        self._workflow_combo.setMaximumWidth(150)
        self._workflow_combo.setToolTip("Active prompt generation workflow template")
        for name, label in list_workflows():
            self._workflow_combo.addItem(label, name)
        # Select "general_chat" by default
        default_idx = self._workflow_combo.findData("general_chat")
        if default_idx >= 0:
            self._workflow_combo.setCurrentIndex(default_idx)
        ctrl_layout.addWidget(self._workflow_combo)

        self._agent_combo = QComboBox()
        self._agent_combo.setMinimumWidth(96)
        self._agent_combo.setMaximumWidth(120)
        self._agent_combo.setToolTip("Select Karl's active workbench agent profile")
        for key, data in AGENT_PROFILES.items():
            self._agent_combo.addItem(data["label"], key)
            idx = self._agent_combo.count() - 1
            self._agent_combo.setItemData(idx, data["description"], Qt.ItemDataRole.ToolTipRole)
        self._agent_combo.currentIndexChanged.connect(self._on_agent_selected)
        ctrl_layout.addWidget(self._agent_combo)

        self._rag_check = QCheckBox("RAG")
        self._rag_check.setToolTip("Inject relevant knowledge base context into prompt")
        self._rag_check.toggled.connect(self._update_expert_strip)
        ctrl_layout.addWidget(self._rag_check)

        self._loop_check = QCheckBox("Loop")
        self._loop_check.setToolTip("Run generation in an autonomous iterative agentic loop")
        self._loop_check.toggled.connect(self._update_expert_strip)
        ctrl_layout.addWidget(self._loop_check)

        self._params_toggle = IconBtn(GearIcon, self.state, tooltip="Toggle Settings drawer")
        self._params_toggle.clicked.connect(self._toggle_settings_overlay)
        self._params_toggle.setAccessibleName("Toggle Settings Drawer")
        self._params_toggle.setAccessibleDescription("Slide open or collapse the settings and feedback panel")
        ctrl_layout.addWidget(self._params_toggle)

        self._sessions_toggle = IconBtn(HamburgerIcon, self.state, tooltip="Toggle Sessions panel")
        self._sessions_toggle.clicked.connect(self._toggle_sessions)
        self._sessions_toggle.setAccessibleName("Toggle Sessions Panel")
        self._sessions_toggle.setAccessibleDescription("Slide open or collapse the chat session history log")
        ctrl_layout.addWidget(self._sessions_toggle)

        self._reasoning_toggle = IconBtn(BrainIcon, self.state, tooltip="Toggle Reasoning panel")
        self._reasoning_toggle.clicked.connect(self._toggle_reasoning)
        self._reasoning_toggle.setAccessibleName("Toggle Reasoning Panel")
        self._reasoning_toggle.setAccessibleDescription("Slide open or collapse the introspection thoughts panel")
        ctrl_layout.addWidget(self._reasoning_toggle)

        ctrl_layout.addStretch()

        self._model_pill = QLabel("")
        self._model_pill.setObjectName("model-pill")
        self._model_pill.setFixedWidth(0)
        self._model_pill.setToolTip("Active base model and adapter overlay")
        ctrl_layout.addWidget(self._model_pill)

        self._stop_btn = QPushButton("■ stop")
        self._stop_btn.setObjectName("btn-danger")
        self._stop_btn.setFixedWidth(76)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setToolTip("Interrupt the active generation thread")
        self._stop_btn.clicked.connect(self._stop)
        self._stop_btn.setAccessibleName("Stop Generation")
        self._stop_btn.setAccessibleDescription("Interrupt the current LLM generation thread immediately")
        ctrl_layout.addWidget(self._stop_btn)

        self._send_btn = QPushButton("send ↵")
        self._send_btn.setObjectName("btn-primary")
        self._send_btn.setFixedWidth(86)
        self._send_btn.setToolTip("Send prompt to Karl (Ctrl+Enter)")
        self._send_btn.clicked.connect(self._send)
        self._send_btn.setAccessibleName("Send Prompt")
        self._send_btn.setAccessibleDescription("Submit the text in the prompt input field to Karl")
        ctrl_layout.addWidget(self._send_btn)

        ic_layout.addWidget(ctrl)
        layout.addWidget(input_container)

        return w


    def _build_command_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("panel")
        root = QVBoxLayout(header)
        root.setContentsMargins(10, 6, 10, 6)
        root.setSpacing(6)

        model_row = QWidget()
        ml = QHBoxLayout(model_row)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)

        model_title = QLabel("Model")
        model_title.setObjectName("section-header")
        ml.addWidget(model_title)

        self._header_model_combo = QComboBox()
        self._header_model_combo.setMinimumWidth(240)
        self._header_model_combo.setMaximumWidth(520)
        self._header_model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._header_model_combo.setToolTip("Installed GGUF models from data/models/. Select a row, then click Load Selected Model.")
        self._header_model_combo.currentIndexChanged.connect(self._on_header_model_staged)
        ml.addWidget(self._header_model_combo, 2)

        self._header_load_model_btn = QPushButton("Load Model")
        self._header_load_model_btn.setObjectName("btn-primary")
        self._header_load_model_btn.setMinimumWidth(92)
        self._header_load_model_btn.setMaximumWidth(150)
        self._header_load_model_btn.clicked.connect(self._load_header_selected_model)
        ml.addWidget(self._header_load_model_btn)

        self._header_reload_model_btn = QPushButton("Reload Active")
        self._header_reload_model_btn.setObjectName("btn-ghost")
        self._header_reload_model_btn.setMaximumWidth(120)
        self._header_reload_model_btn.clicked.connect(self._reload_active_model)
        ml.addWidget(self._header_reload_model_btn)

        self._header_model_status = QLabel("Model: none")
        self._header_model_status.setObjectName("lbl-muted")
        self._header_model_status.setMinimumWidth(220)
        self._header_model_status.setMaximumWidth(360)
        self._header_model_status.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        ml.addWidget(self._header_model_status, 1)
        root.addWidget(model_row)

        appearance_row = QWidget()
        al = QHBoxLayout(appearance_row)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(8)

        agent_title = QLabel("Agent")
        agent_title.setObjectName("section-header")
        al.addWidget(agent_title)

        self._header_agent_combo = QComboBox()
        self._header_agent_combo.setMinimumWidth(130)
        self._header_agent_combo.setMaximumWidth(160)
        self._header_agent_combo.setToolTip("Select Karl's active Workbench agent profile.")
        for key, data in AGENT_PROFILES.items():
            self._header_agent_combo.addItem(data["label"], key)
            idx = self._header_agent_combo.count() - 1
            self._header_agent_combo.setItemData(idx, data["description"], Qt.ItemDataRole.ToolTipRole)
        self._header_agent_combo.currentIndexChanged.connect(self._on_header_agent_selected)
        al.addWidget(self._header_agent_combo)

        self._theme_indicator = QLabel("Theme: Karl Obsidian Core")
        self._theme_indicator.setObjectName("lbl-muted")
        self._theme_indicator.setMinimumWidth(120)
        al.addWidget(self._theme_indicator, 1)

        self._appearance_btn = QPushButton("Appearance")
        self._appearance_btn.setObjectName("btn-secondary")
        self._appearance_btn.setMaximumWidth(120)
        self._appearance_btn.setToolTip("Open the System Theme tab to change palettes, accent color, glow, and motion.")
        self._appearance_btn.clicked.connect(self.appearance_requested.emit)
        al.addWidget(self._appearance_btn)

        self._accent_btn = QPushButton("Accent")
        self._accent_btn.setObjectName("btn-primary")
        self._accent_btn.setMaximumWidth(92)
        self._accent_btn.setToolTip("Open a color wheel and apply a custom Karl accent color immediately.")
        self._accent_btn.clicked.connect(self._pick_header_accent)
        al.addWidget(self._accent_btn)
        root.addWidget(appearance_row)

        return header


    def _build_settings_overlay(self):
        self._settings_overlay = QFrame(self._chat_panel)
        self._settings_overlay.setObjectName("settings-overlay")
        self._settings_overlay.setVisible(False)
        
        state = self.property("modelState") or "idle"
        self._settings_overlay.setProperty("modelState", state)
        
        layout = QVBoxLayout(self._settings_overlay)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        hdr = QLabel("CONTROL CENTER")
        hdr.setObjectName("settings-overlay-header")
        layout.addWidget(hdr)
        
        params_grp = QWidget()
        pl = QVBoxLayout(params_grp)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        
        pl.addWidget(_label("Active Model", "lbl-muted"))
        self._model_combo = QComboBox()
        self._model_combo.setToolTip("Select active model and adapter overlay")
        self._model_combo.currentIndexChanged.connect(self._on_model_selected)
        pl.addWidget(self._model_combo)
        
        pl.addWidget(_label("Temperature", "lbl-muted"))
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.05)
        self._temp_spin.setValue(self._hyperparams["temperature"])
        self._temp_spin.setToolTip("Generation temperature. Lower is deterministic, higher is creative.")
        self._temp_spin.valueChanged.connect(
            lambda v: self._hyperparams.__setitem__("temperature", v)
        )
        pl.addWidget(self._temp_spin)
        
        pl.addWidget(_label("Top-P", "lbl-muted"))
        self._topp_spin = QDoubleSpinBox()
        self._topp_spin.setRange(0.0, 1.0)
        self._topp_spin.setSingleStep(0.05)
        self._topp_spin.setValue(self._hyperparams["top_p"])
        self._topp_spin.setToolTip("Top-p sampling cutoff.")
        self._topp_spin.valueChanged.connect(
            lambda v: self._hyperparams.__setitem__("top_p", v)
        )
        pl.addWidget(self._topp_spin)
        
        pl.addWidget(_label("Max Tokens", "lbl-muted"))
        self._maxtok_spin = QSpinBox()
        self._maxtok_spin.setRange(64, 8192)
        self._maxtok_spin.setSingleStep(64)
        self._maxtok_spin.setValue(self._hyperparams["max_tokens"])
        self._maxtok_spin.setToolTip("Maximum number of tokens to generate.")
        self._maxtok_spin.valueChanged.connect(self._on_max_tokens_changed)
        pl.addWidget(self._maxtok_spin)
        
        layout.addWidget(params_grp)
        layout.addWidget(_hline())
        
        fb_grp = QWidget()
        fbl = QVBoxLayout(fb_grp)
        fbl.setContentsMargins(0, 0, 0, 0)
        fbl.setSpacing(8)
        
        fbl.addWidget(_label("Actions & Feedback", "lbl-muted"))
        
        self._thumb_btn = QPushButton("✓ Good")
        self._thumb_btn.setObjectName("btn-success")
        self._thumb_btn.setEnabled(False)
        self._thumb_btn.setToolTip("Curate this response as a positive training example")
        self._thumb_btn.clicked.connect(self._on_thumb_up)
        self._thumb_btn.setAccessibleName("Rate Good")
        self._thumb_btn.setAccessibleDescription("Curate this generation as a correct example for fine-tuning")
        fbl.addWidget(self._thumb_btn)
        
        self._thumb_down_btn = QPushButton("✗ Bad")
        self._thumb_down_btn.setObjectName("btn-danger")
        self._thumb_down_btn.setEnabled(False)
        self._thumb_down_btn.setToolTip("Flag this response as an incorrect training example")
        self._thumb_down_btn.clicked.connect(self._on_thumb_down)
        self._thumb_down_btn.setAccessibleName("Rate Bad")
        self._thumb_down_btn.setAccessibleDescription("Flag this generation as incorrect to build a rejected pair")
        fbl.addWidget(self._thumb_down_btn)
        
        self._correct_btn = QPushButton("✎ Correct")
        self._correct_btn.setObjectName("btn-warning")
        self._correct_btn.setEnabled(False)
        self._correct_btn.setToolTip("Manually edit response to create corrected pair")
        self._correct_btn.clicked.connect(self._on_correct)
        self._correct_btn.setAccessibleName("Correct Response")
        self._correct_btn.setAccessibleDescription("Open the editor to type a corrected version of the generation")
        fbl.addWidget(self._correct_btn)
        
        self._new_session_btn = QPushButton("+ New Session")
        self._new_session_btn.setObjectName("btn-ghost")
        self._new_session_btn.clicked.connect(self._new_session)
        self._new_session_btn.setAccessibleName("Start New Session")
        self._new_session_btn.setAccessibleDescription("Clear history and begin a fresh conversation session")
        fbl.addWidget(self._new_session_btn)
        
        layout.addWidget(fb_grp)
        layout.addStretch()

    def _toggle_settings_overlay(self):
        if not hasattr(self, "_settings_overlay") or self._settings_overlay is None:
            self._build_settings_overlay()
            
        visible = not self._settings_overlay.isVisible()
        
        if visible:
            self._settings_overlay.show()
            self._settings_overlay.raise_()
            
            parent_width = self._chat_panel.width()
            parent_height = self._chat_panel.height()
            overlay_width = min(300, max(240, parent_width - 24))
            
            start_rect = QRect(parent_width, 0, overlay_width, parent_height)
            end_rect = QRect(parent_width - overlay_width, 0, overlay_width, parent_height)
            
            self._settings_overlay.setGeometry(start_rect)
            
            if not getattr(self.state, "reduced_motion", False):
                self._settings_anim = QPropertyAnimation(self._settings_overlay, b"geometry")
                self._settings_anim.setDuration(250)
                self._settings_anim.setStartValue(start_rect)
                self._settings_anim.setEndValue(end_rect)
                self._settings_anim.start()
            else:
                self._settings_overlay.setGeometry(end_rect)
        else:
            parent_width = self._chat_panel.width()
            parent_height = self._chat_panel.height()
            overlay_width = min(300, max(240, parent_width - 24))
            
            start_rect = self._settings_overlay.geometry()
            end_rect = QRect(parent_width, 0, overlay_width, parent_height)
            
            if not getattr(self.state, "reduced_motion", False):
                self._settings_anim = QPropertyAnimation(self._settings_overlay, b"geometry")
                self._settings_anim.setDuration(200)
                self._settings_anim.setStartValue(start_rect)
                self._settings_anim.setEndValue(end_rect)
                self._settings_anim.finished.connect(self._settings_overlay.hide)
                self._settings_anim.start()
            else:
                self._settings_overlay.setGeometry(end_rect)
                self._settings_overlay.hide()
                
        self._update_hud_btn_styles()

    def _responsive_mode_for_width(self, width: int) -> str:
        if width < 850:
            return "single"
        if width < 1100:
            return "focus"
        if width < 1400:
            return "compact"
        return "full"

    def _set_button_text_width(self, button: QPushButton, text: str, width: int) -> None:
        button.setText(text)
        button.setFixedWidth(width)

    def _apply_responsive_layout(self, width: int) -> None:
        if width <= 0 or not hasattr(self, "_input_container"):
            return

        mode = self._responsive_mode_for_width(width)
        if self._responsive_mode == mode:
            return
        self._responsive_mode = mode

        is_full = mode == "full"
        is_compact = mode == "compact"
        is_focus = mode == "focus"
        is_single = mode == "single"

        self.setProperty("responsiveMode", mode)
        self.style().unpolish(self)
        self.style().polish(self)

        if is_full:
            self._sessions_dock.setMinimumWidth(200)
            self._reasoning_dock.setMinimumWidth(260)
        elif is_compact:
            self._sessions_dock.setMinimumWidth(160)
            self._reasoning_dock.setMinimumWidth(200)
        else:
            self._sessions_dock.hide()
            self._reasoning_dock.hide()

        self._command_header.setVisible(not is_single)
        self._header_reload_model_btn.setVisible(is_full or is_compact)
        self._header_model_status.setVisible(not is_single)
        self._theme_indicator.setVisible(is_full or is_compact)
        self._appearance_btn.setVisible(not is_single)
        self._accent_btn.setVisible(not is_single)

        self._header_model_combo.setMinimumWidth(170 if is_focus else 220 if is_compact else 240)
        self._header_model_combo.setMaximumWidth(360 if is_focus else 460 if is_compact else 620)
        self._header_load_model_btn.setText("Load" if is_focus else "Load Model")
        self._header_agent_combo.setMaximumWidth(130 if is_focus else 160)

        composer_h = 104 if is_single else 112 if is_focus else 118 if is_compact else 124
        input_h = 48 if is_single else 52 if is_focus else 56 if is_compact else 58
        self._input_container.setFixedHeight(composer_h)
        self._input.setFixedHeight(input_h)
        self._token_row.setVisible(not is_single)

        self._workflow_combo.setMaximumWidth(128 if (is_focus or is_single) else 150)
        self._agent_combo.setMaximumWidth(104 if (is_focus or is_single) else 120)
        self._workflow_combo.setVisible(not is_single)
        self._agent_combo.setVisible(not is_single)
        self._rag_check.setVisible(not is_single)
        self._loop_check.setVisible(not is_single)
        self._model_pill.setVisible(False)

        self._set_button_text_width(self._stop_btn, "■" if is_single else "■ stop", 44 if is_single else 70)
        self._set_button_text_width(self._send_btn, "↵" if is_single else "send ↵", 52 if is_single else 82)

        if hasattr(self, "_hud_sessions_btn"):
            self._hud_sessions_btn.setText("Sess" if is_single else "Sessions")
        if hasattr(self, "_hud_reasoning_btn"):
            self._hud_reasoning_btn.setText("Think" if is_single else "Reasoning")
        if hasattr(self, "_hud_context_btn"):
            self._hud_context_btn.setText("Context HUD" if is_full else "Context")
        if hasattr(self, "_hud_master_btn"):
            self._hud_master_btn.setText("HUDs" if is_single else "Show All HUDs")

        self._update_hud_btn_styles()

    def _setup_glow_effects(self):
        self._sessions_shadow = QGraphicsDropShadowEffect(self)
        self._sessions_shadow.setBlurRadius(15)
        self._sessions_shadow.setXOffset(0)
        self._sessions_shadow.setYOffset(0)
        self._sessions_dock.setGraphicsEffect(self._sessions_shadow)

        self._reasoning_shadow = QGraphicsDropShadowEffect(self)
        self._reasoning_shadow.setBlurRadius(15)
        self._reasoning_shadow.setXOffset(0)
        self._reasoning_shadow.setYOffset(0)
        self._reasoning_dock.setGraphicsEffect(self._reasoning_shadow)

        self._chat_shadow = QGraphicsDropShadowEffect(self)
        self._chat_shadow.setBlurRadius(15)
        self._chat_shadow.setXOffset(0)
        self._chat_shadow.setYOffset(0)
        self._chat_panel.setGraphicsEffect(self._chat_shadow)

    def _update_glow_pulse(self):
        if getattr(self.state, "reduced_motion", False):
            self._glow_val = 0.7
        else:
            self._glow_val += 0.05 * self._glow_dir
            if self._glow_val >= 1.0:
                self._glow_val = 1.0
                self._glow_dir = -1
            elif self._glow_val <= 0.3:
                self._glow_val = 0.3
                self._glow_dir = 1

        state = self.property("modelState") or "idle"
        
        if state == "generating":
            r = 255
            g = int(140 * (1.0 - self._glow_val))
            b = int(127 * self._glow_val)
            color = QColor(r, g, b, int(255 * (0.3 + 0.5 * self._glow_val)))
            radius = 15 + int(10 * self._glow_val)
        elif state == "error":
            color = QColor(255, 59, 48, 200)
            radius = 25
        else:
            accent = get_theme_colors(self.state).get("accent", "#00C2FF")
            color = QColor(accent)
            color.setAlphaF(0.4 + 0.2 * self._glow_val)
            radius = 12 + int(6 * self._glow_val)

        for shadow in (getattr(self, "_sessions_shadow", None),
                       getattr(self, "_reasoning_shadow", None),
                       getattr(self, "_chat_shadow", None)):
            if shadow:
                shadow.setColor(color)
                shadow.setBlurRadius(radius)

    def _setup_chat_animations(self):
        original_set_html = self._chat_view.setHtml
        def custom_set_html(html):
            self._fade_in_chat()
            original_set_html(html)
        self._chat_view.setHtml = custom_set_html

    def _fade_in_chat(self):
        if getattr(self.state, "reduced_motion", False):
            return
        self._chat_opacity = QGraphicsOpacityEffect(self._chat_view)
        self._chat_view.setGraphicsEffect(self._chat_opacity)
        
        self._chat_anim = QPropertyAnimation(self._chat_opacity, b"opacity")
        self._chat_anim.setDuration(250)
        self._chat_anim.setStartValue(0.7)
        self._chat_anim.setEndValue(1.0)
        self._chat_anim.start()

    def _populate_hud_toolbar(self):
        tb = self._hud_toolbar
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(10, 4, 10, 4)
        tbl.setSpacing(10)
        
        lbl = QLabel("HUD:")
        lbl.setStyleSheet("font-size: 8pt; font-weight: bold; color: #6A7B95; letter-spacing: 1.5px;")
        tbl.addWidget(lbl)
        
        self._hud_sessions_btn = QPushButton("Sessions")
        self._hud_sessions_btn.setObjectName("hud-btn")
        self._hud_sessions_btn.setCheckable(True)
        self._hud_sessions_btn.setChecked(self._sessions_dock.isVisible())
        self._hud_sessions_btn.clicked.connect(self._toggle_sessions)
        tbl.addWidget(self._hud_sessions_btn)
        
        self._hud_reasoning_btn = QPushButton("Reasoning")
        self._hud_reasoning_btn.setObjectName("hud-btn")
        self._hud_reasoning_btn.setCheckable(True)
        self._hud_reasoning_btn.setChecked(self._reasoning_dock.isVisible())
        self._hud_reasoning_btn.clicked.connect(self._toggle_reasoning)
        tbl.addWidget(self._hud_reasoning_btn)
        
        self._hud_rag_btn = QPushButton("RAG Sources")
        self._hud_rag_btn.setObjectName("hud-btn")
        self._hud_rag_btn.setCheckable(True)
        self._hud_rag_btn.setChecked(self._rag_sources_view.isVisible())
        self._hud_rag_btn.clicked.connect(self._toggle_rag_hud)
        tbl.addWidget(self._hud_rag_btn)
        
        self._hud_context_btn = QPushButton("Context HUD")
        self._hud_context_btn.setObjectName("hud-btn")
        self._hud_context_btn.setCheckable(True)
        self._hud_context_btn.setChecked(self._context_bar.isVisible())
        self._hud_context_btn.clicked.connect(self._toggle_context_hud)
        tbl.addWidget(self._hud_context_btn)
        
        self._hud_settings_btn = QPushButton("Settings")
        self._hud_settings_btn.setObjectName("hud-btn")
        self._hud_settings_btn.setCheckable(True)
        self._hud_settings_btn.setChecked(False)
        self._hud_settings_btn.clicked.connect(self._toggle_settings_overlay)
        tbl.addWidget(self._hud_settings_btn)
        
        tbl.addStretch()
        
        self._hud_master_btn = QPushButton("Hide All HUDs")
        self._hud_master_btn.setObjectName("hud-btn")
        self._hud_master_btn.clicked.connect(self._toggle_all_huds)
        tbl.addWidget(self._hud_master_btn)
        
        self._sessions_dock.visibilityChanged.connect(lambda visible: self._update_hud_btn_styles())
        self._reasoning_dock.visibilityChanged.connect(lambda visible: self._update_hud_btn_styles())
        
        self._update_hud_btn_styles()

    def _toggle_rag_hud(self):
        visible = not self._rag_sources_view.isVisible()
        self._rag_sources_view.setVisible(visible)
        self._update_hud_btn_styles()

    def _toggle_context_hud(self):
        visible = not self._context_bar.isVisible()
        self._context_bar.setVisible(visible)
        if hasattr(self, "_token_row"):
            self._token_row.setVisible(visible)
        self._update_hud_btn_styles()

    def _update_hud_btn_styles(self):
        for btn, val in [
            (getattr(self, "_hud_sessions_btn", None), self._sessions_dock.isVisible()),
            (getattr(self, "_hud_reasoning_btn", None), self._reasoning_dock.isVisible()),
            (getattr(self, "_hud_rag_btn", None), self._rag_sources_view.isVisible()),
            (getattr(self, "_hud_context_btn", None), self._context_bar.isVisible()),
            (getattr(self, "_hud_settings_btn", None), getattr(self, "_settings_overlay", None) is not None and self._settings_overlay.isVisible())
        ]:
            if btn:
                btn.blockSignals(True)
                btn.setChecked(val)
                btn.setProperty("active", "true" if val else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.blockSignals(False)

    def _toggle_all_huds(self):
        any_visible = (
            self._sessions_dock.isVisible() or
            self._reasoning_dock.isVisible() or
            self._rag_sources_view.isVisible() or
            self._context_bar.isVisible()
        )
        target_visible = not any_visible
        
        self._sessions_dock.setVisible(target_visible)
        self._reasoning_dock.setVisible(target_visible)
        self._rag_sources_view.setVisible(target_visible)
        self._context_bar.setVisible(target_visible)
        if hasattr(self, "_token_row"):
            self._token_row.setVisible(target_visible and self._responsive_mode != "single")
            
        self._update_hud_btn_styles()
        
        if self._responsive_mode == "single":
            self._hud_master_btn.setText("HUDs")
        elif target_visible:
            self._hud_master_btn.setText("Hide All HUDs")
        else:
            self._hud_master_btn.setText("Show All HUDs")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout(event.size().width())
        if hasattr(self, "_settings_overlay") and self._settings_overlay and self._settings_overlay.isVisible():
            parent_width = self._chat_panel.width()
            parent_height = self._chat_panel.height()
            overlay_width = min(300, max(240, parent_width - 24))
            self._settings_overlay.setGeometry(parent_width - overlay_width, 0, overlay_width, parent_height)

    def update_model_state(self, state: str):
        self.setProperty("modelState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        
        if hasattr(self, "_settings_overlay") and self._settings_overlay:
            self._settings_overlay.setProperty("modelState", state)
            self._settings_overlay.style().unpolish(self._settings_overlay)
            self._settings_overlay.style().polish(self._settings_overlay)
            
        self._update_glow_pulse()

    def _connect_shortcuts(self):
        sc = QShortcut(QKeySequence("Ctrl+Return"), self)
        sc.activated.connect(self._send)

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_input", None) and event.type() == QEvent.Type.KeyPress:
            if event.matches(QKeySequence.StandardKey.Paste) and self._clipboard_has_image():
                self._attach_clipboard_image()
                return True
        return super().eventFilter(obj, event)

    # ── actions ───────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.toPlainText().strip()
        if not text or self._thread is not None:
            return

        if self._is_correcting:
            self._is_correcting = False
            self._correct_btn.setText("✎ correct")
            self._correct_btn.setEnabled(False)
            self._thumb_btn.setEnabled(False)
            self._thumb_down_btn.setEnabled(False)

            self._input.clear()

            # Update the last assistant message in history
            if self.chat_history:
                self.chat_history.update_current_node_content(text)

            # Update ChatView
            self._chat_view.replace_last_assistant(text)

            # Save corrected example
            prompt = self.chat_history[-2]["content"] if len(self.chat_history) >= 2 else ""
            self.state.curator.save_example(
                prompt=prompt,
                response=text,
                source="corrected",
                system_prompt=self._system_prompt
            )

            # Update trace log
            self.state.logger.update_last_entry_feedback(
                feedback="corrected",
                corrected_response=text
            )

            self._last_response = text
            self._save_current_session()
            return

        self._input.clear()
        self._reasoning_view.clear()
        self._thumb_btn.setEnabled(False)
        self._thumb_down_btn.setEnabled(False)
        self._correct_btn.setEnabled(False)

        attachments = list(self._pending_image_attachments)
        self._pending_image_attachments = []
        prompt_text = self._build_image_prompt_context(text, attachments) if attachments else text
        user_node = self.chat_history.add_message("user", text, attachments=attachments)
        self._update_token_budget()
        self._chat_view.push_user(text, user_node.id, attachments=attachments)
        self._pending_generation_history = list(self.chat_history)
        if self._pending_generation_history:
            self._pending_generation_history[-1] = {
                **self._pending_generation_history[-1],
                "content": prompt_text,
            }

        chunks = []
        if self._rag_check.isChecked():
            top_k = getattr(self.state, "rag_top_k", 3)
            threshold = getattr(self.state, "rag_threshold", 0.0)
            
            retrieved_metadata = []
            rag_mode = getattr(self.state, "rag_mode", "dense")
            if self.state.rag.total_chunks > 0:
                retrieved_metadata.extend(self.state.rag.retrieve_with_metadata(prompt_text, top_k=top_k, threshold=threshold, mode=rag_mode))
                
            if hasattr(self.state, "codex_rag") and self.state.codex_rag.total_chunks > 0:
                retrieved_metadata.extend(self.state.codex_rag.retrieve_with_metadata(prompt_text, top_k=top_k, threshold=threshold, mode=rag_mode))
                
            # Sort combined results by distance (lower distance = closer match)
            retrieved_metadata.sort(key=lambda x: x.get("distance", 999.0))
            # Slice down to requested top_k limit
            retrieved_metadata = retrieved_metadata[:top_k]
            
            if threshold > 0.0:
                retrieved_metadata = [r for r in retrieved_metadata if r["distance"] <= threshold]
            
            if retrieved_metadata:
                self._chat_view.append_rag_sources(retrieved_metadata)
                for r in retrieved_metadata:
                    chunk_text = r["text"]
                    if getattr(self.state.rag, "contextual_headers", False):
                        header = f"[Source: {r['source_file']} | Chunk {r['chunk_id']}]\n"
                        chunk_text = header + chunk_text
                    chunks.append(chunk_text)

        if self._loop_check.isChecked():
            self._start_agentic(chunks)
        else:
            self._start_single(chunks)

    def _clipboard_has_image(self) -> bool:
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        return mime.hasImage()

    def _attach_clipboard_image(self):
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            self._chat_view.append_system_note("clipboard does not contain a readable image")
            return
        try:
            record = self.state.image_store.save_qimage(image, source="clipboard")
        except Exception as exc:
            self._chat_view.append_system_note(f"image paste failed: {exc}")
            return

        attachment = {
            "type": "image",
            "id": record.id,
            "path": record.original_path,
            "thumbnail_path": record.thumbnail_path,
            "label": f"{record.width}x{record.height} clipboard image",
            "ocr_status": "queued",
        }
        self._pending_image_attachments.append(attachment)
        self._chat_view.append_system_note(
            f"image attached and saved: {record.id[:8]} ({record.width}x{record.height}). Ask a question to use it."
        )
        self._start_image_analysis(record.id)

    def attach_existing_image(self, image_id: str):
        try:
            record = self.state.image_store.get(image_id)
        except Exception as exc:
            self._chat_view.append_system_note(f"image attach failed: {exc}")
            return
        attachment = {
            "type": "image",
            "id": record.id,
            "path": record.original_path,
            "thumbnail_path": record.thumbnail_path,
            "label": f"{record.width}x{record.height} saved image",
            "ocr_status": "ready" if record.ocr.text else "pending",
        }
        self._pending_image_attachments.append(attachment)
        self._chat_view.append_system_note(
            f"image attached from Vision Workbench: {record.id[:8]}. Ask a question to use it."
        )

    def _start_image_analysis(self, image_id: str):
        thread = ImageAnalysisThread(self.state.image_store, image_id)
        thread.progress.connect(lambda msg, iid=image_id: self._on_image_analysis_progress(iid, msg))
        thread.ocr_done.connect(self._on_image_ocr_done)
        thread.vision_done.connect(self._on_image_vision_done)
        thread.done.connect(self._on_image_analysis_done)
        thread.error.connect(lambda msg, iid=image_id: self._on_image_analysis_error(iid, msg))
        self._image_threads.add(thread)
        thread.finished.connect(lambda: self._image_threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_image_analysis_progress(self, image_id: str, msg: str):
        for attachment in self._pending_image_attachments:
            if attachment.get("id") == image_id:
                attachment["ocr_status"] = msg
        self._chat_view.append_system_note(f"image {image_id[:8]}: {msg}")

    def _on_image_ocr_done(self, image_id: str, ocr):
        for attachment in self._pending_image_attachments:
            if attachment.get("id") == image_id:
                attachment["ocr_status"] = "ready"
                attachment["ocr_chars"] = len(getattr(ocr, "text", "") or "")
                attachment["ocr_confidence"] = getattr(ocr, "confidence", 0.0)
        chars = len(getattr(ocr, "text", "") or "")
        self._chat_view.append_system_note(
            f"image {image_id[:8]}: OCR ready ({chars} chars, confidence {getattr(ocr, 'confidence', 0.0):.2f})"
        )

    def _on_image_vision_done(self, image_id: str, vision):
        for attachment in self._pending_image_attachments:
            if attachment.get("id") == image_id:
                attachment["analysis_status"] = "ready"
                attachment["vision_engine"] = getattr(vision, "engine", "none")
        caption = (getattr(vision, "caption", "") or "").strip()
        if caption:
            short = caption.replace("\n", " ")[:180]
            self._chat_view.append_system_note(f"image {image_id[:8]}: vision analysis ready - {short}")

    def _on_image_analysis_done(self, image_id: str, _record):
        for attachment in self._pending_image_attachments:
            if attachment.get("id") == image_id:
                attachment["analysis_status"] = "ready"

    def _on_image_analysis_error(self, image_id: str, msg: str):
        for attachment in self._pending_image_attachments:
            if attachment.get("id") == image_id:
                attachment["analysis_status"] = "error"
                attachment["ocr_status"] = "error"
        self._chat_view.append_system_note(f"image {image_id[:8]} analysis error: {msg}")

    def _build_image_prompt_context(self, text: str, attachments: list[dict]) -> str:
        blocks = []
        for attachment in attachments:
            if attachment.get("type") != "image":
                continue
            try:
                record = self.state.image_store.get(attachment["id"])
            except Exception as exc:
                logger.warning("dropping image attachment %s from prompt context: %s",
                               attachment.get("id", "?"), exc)
                continue
            blocks.append(
                "\n".join([
                    "[Attached Image]",
                    f"ID: {record.id}",
                    f"Path: {record.original_path}",
                    f"Size: {record.width}x{record.height}",
                    f"Source: {record.source}",
                    f"Kind: {record.kind}",
                    f"OCR Status: {record.ocr.engine}",
                    f"OCR Confidence: {record.ocr.confidence:.2f}",
                    "OCR Text:",
                    record.ocr.text.strip() or "(pending or unavailable)",
                    f"Vision Engine: {record.vision.engine}",
                    f"Vision Model: {record.vision.model or '(none)'}",
                    f"Detected Code: {record.vision.detected_code}",
                    f"Detected Error: {record.vision.detected_error}",
                    "Vision Summary:",
                    record.vision.caption.strip() or "(pending or unavailable)",
                ])
            )
        if not blocks:
            return text
        return "\n\n".join(blocks + ["[User Question]", text])

    def _current_workflow(self) -> str:
        return self._workflow_combo.currentData() or "general_chat"

    def _current_template(self) -> str:
        from core.workflows import get_workflow
        try:
            return get_workflow(self._current_workflow())["template"]
        except KeyError:
            return "reasoning_minimal"

    def _update_token_budget(self):
        """Update the context window HUD bar."""
        if not hasattr(self, '_context_bar'):
            return
        from app.engine.model_loader import ModelLoader
        budget = ModelLoader.n_ctx()
        used = getattr(self, '_last_context_used', 0)
        rag = getattr(self, '_last_rag_tokens', 0)
        hist = getattr(self, '_last_hist_tokens', 0)
        pct = int((used / max(budget, 1)) * 100)
    
        self._context_bar.setValue(pct)
        if pct >= 92:
            self._context_bar.setStyleSheet("QProgressBar::chunk { background: #FF3366; }")
        elif pct >= 80:
            self._context_bar.setStyleSheet("QProgressBar::chunk { background: #FFB400; }")
        else:
            self._context_bar.setStyleSheet("QProgressBar::chunk { background: #2DD4A0; }")
    
        self._context_bar.setFormat(
            f"{used:,} / {budget:,} tokens  |  RAG: {rag:,}  |  History: {hist:,}"
        )

    def _on_reload_success(self, label: str):
        toast = ToastOverlay(self, f"⟳ {label} reloaded successfully")
        toast.show_toast()

    def _on_reload_failed(self, label: str, tb_str: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Hot-Reload Failed")
        msg.setText(f"Failed to reload <b>{label}</b> due to an error.")
        msg.setInformativeText("Karl will keep using the last stable version of the script.")
        msg.setDetailedText(tb_str)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Style the dialog to match Karl's theme
        colors = get_theme_colors(self.state)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {colors.get('bg_base', '#0D0D16')}; color: {colors.get('text_hi', '#E4E4F0')}; }}
            QLabel {{ color: {colors.get('text_hi', '#E4E4F0')}; }}
            QPushButton {{ 
                background-color: {colors.get('bg_raised', '#1C1C2A')}; 
                color: {colors.get('text_hi', '#E4E4F0')}; 
                border: 1px solid {colors.get('border', '#252535')};
                padding: 4px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {colors.get('bg_surface', '#14141F')}; }}
            QTextEdit {{ background-color: {colors.get('bg_deep', '#07070D')}; color: {colors.get('think_text', '#505080')}; font-family: 'JetBrains Mono', monospace; }}
        """)
        msg.exec()

    def _show_reload_notice(self, module_name: str):
        self._reload_notice.setText(f"⟳ {module_name} reloaded")
        self._reload_notice.setVisible(True)
        self._reload_hide_timer.start(3000)

    def _start_single(self, chunks: list[str]):
        set_correlation_id(f"chat:{new_correlation_id()}")
        self._chat_view.begin_stream()
        self._set_busy(True)
        self._reasoning_stats_lbl.setText("")
        history = self._pending_generation_history or list(self.chat_history)
        self._pending_generation_history = None

        try:
            t = self._inference_service.run_generation(
                prompt="",
                system_prompt=self._active_system_prompt(),
                chat_history=history,
                hyperparams=self._hyperparams,
                on_thought_token_cb=self._on_thought,
                on_token_cb=self._on_chat,
                on_live_stats_cb=self._on_live_stats,
                on_error_cb=self._on_error,
                retrieved_chunks=chunks,
                agentic=False,
                workflow=self._current_workflow(),
                template=self._current_template(),
                adapter_name=self.state.adapter_name,
            )
        except CircuitBreakerOpenException as exc:
            self._on_error(str(exc))
            return
        # UI-specific signals not covered by the standard callback set
        t.generation_finished.connect(self._on_done)
        t.reload_notice.connect(self._show_reload_notice)
        t.context_stats.connect(self._on_context_stats)
        t.rag_context_used.connect(self._on_rag_context_used)
        t.status_update.connect(self.status_changed)
        self._thread = t

    def _start_agentic(self, chunks: list[str]):
        set_correlation_id(f"agentic:{new_correlation_id()}")
        self._set_busy(True)
        self._reasoning_stats_lbl.setText("")
        self._chat_view.append_system_note("— agentic loop started —")
        history = self._pending_generation_history or list(self.chat_history)
        self._pending_generation_history = None

        try:
            t = self._inference_service.run_generation(
                prompt="",
                system_prompt=self._active_system_prompt(),
                chat_history=history,
                hyperparams=self._hyperparams,
                on_thought_token_cb=self._on_thought,
                on_token_cb=self._on_chat,
                on_live_stats_cb=self._on_live_stats,
                on_error_cb=self._on_error,
                retrieved_chunks=chunks,
                agentic=True,
                workflow=self._current_workflow(),
                template=self._current_template(),
                adapter_name=self.state.adapter_name,
            )
        except CircuitBreakerOpenException as exc:
            self._on_error(str(exc))
            return
        # UI-specific signals not covered by the standard callback set
        t.iteration_finished.connect(self._on_iteration)
        t.loop_finished.connect(self._on_loop_done)
        t.reload_notice.connect(self._show_reload_notice)
        t.context_stats.connect(self._on_context_stats)
        t.status_update.connect(self.status_changed)
        self._thread = t

    def _stop(self):
        if self._thread:
            if hasattr(self._thread, "request_stop"):
                self._thread.request_stop()

    def _toggle_reasoning(self):
        visible = self._reasoning_dock.isVisible()
        self._reasoning_dock.setVisible(not visible)

    def _toggle_sessions(self):
        visible = self._sessions_dock.isVisible()
        self._sessions_dock.setVisible(not visible)

    def _toggle_params(self):
        visible = not self._params_drawer.isVisible()
        if visible:
            self._refresh_model_combo()
        self._params_drawer.setVisible(visible)

    def _on_max_tokens_changed(self, value: int):
        self._hyperparams["max_tokens"] = value
        self._update_token_budget()

    def _on_agent_selected(self, *_args):
        self._agent_profile = self._agent_combo.currentData() or "karl"
        if hasattr(self, "_header_agent_combo"):
            idx = self._header_agent_combo.findData(self._agent_profile)
            if idx >= 0 and self._header_agent_combo.currentIndex() != idx:
                self._header_agent_combo.blockSignals(True)
                self._header_agent_combo.setCurrentIndex(idx)
                self._header_agent_combo.blockSignals(False)
        self._update_expert_strip()

    def _on_header_agent_selected(self, *_args):
        self._agent_profile = self._header_agent_combo.currentData() or "karl"
        if hasattr(self, "_agent_combo"):
            idx = self._agent_combo.findData(self._agent_profile)
            if idx >= 0 and self._agent_combo.currentIndex() != idx:
                self._agent_combo.blockSignals(True)
                self._agent_combo.setCurrentIndex(idx)
                self._agent_combo.blockSignals(False)
        self._update_expert_strip()

    def _pick_header_accent(self):
        from app.ui.themes import THEMES
        from PyQt6.QtWidgets import QApplication
        from app.ui.themes import get_theme_stylesheet

        default_color = self.state.custom_accent
        if not default_color:
            theme_name = getattr(self.state, "theme_preset", "Karl Obsidian Core")
            default_color = THEMES.get(theme_name, {}).get("accent", "#00E5FF")
        color = QColorDialog.getColor(QColor(default_color), self, "Select Karl Accent Color")
        if not color.isValid():
            return
        self.state.custom_accent = color.name().upper()
        QApplication.instance().setStyleSheet(get_theme_stylesheet(self.state))
        self.update_theme()
        self.appearance_requested.emit()

    def _active_system_prompt(self) -> str:
        profile = AGENT_PROFILES.get(self._agent_profile, AGENT_PROFILES["karl"])
        profile_prompt = profile.get("prompt", "").strip()
        if not profile_prompt:
            return self._system_prompt
        return f"{self._system_prompt}\n\n{profile_prompt}"

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_model_combo()

    def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool:
        from app.engine import config_store
        return config_store.is_adapter_compatible(model_filename, adapter_name)

    def _refresh_model_combo(self):
        entries = self._model_selection_entries()

        for combo in (getattr(self, "_model_combo", None), getattr(self, "_header_model_combo", None)):
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            for entry in entries:
                label = entry["short_label"] if combo is getattr(self, "_model_combo", None) else entry["label"]
                combo.addItem(label, entry["data"])
                idx = combo.count() - 1
                combo.setItemData(idx, entry["tooltip"], Qt.ItemDataRole.ToolTipRole)
            
        # Select active model and adapter combination
        active_model = self.state.model_name
        active_adapter = self.state.adapter_name
        
        for combo in (getattr(self, "_model_combo", None), getattr(self, "_header_model_combo", None)):
            if combo is None:
                continue
            self._select_model_combo_value(combo, active_model, active_adapter)
            combo.blockSignals(False)

        self._update_model_pill()
        self._update_header_model_status()

    def _select_model_combo_value(self, combo: QComboBox, active_model: str | None, active_adapter: str | None):
        found = False
        for idx in range(combo.count()):
            d = combo.itemData(idx)
            if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") == active_adapter:
                combo.setCurrentIndex(idx)
                found = True
                break
        if not found:
            for idx in range(combo.count()):
                d = combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") is None:
                    combo.setCurrentIndex(idx)
                    found = True
                    break
        if not found and combo.count() > 0:
            combo.setCurrentIndex(0)

    def _model_selection_entries(self) -> list[dict]:
        import os
        from app.engine import config_store

        registry = {}
        for item in config_store.get_model_registry():
            registry[item.get("filename", "")] = item

        adapters_dir = "data/adapters"
        adapters = []
        if os.path.exists(adapters_dir):
            try:
                for d in sorted(os.listdir(adapters_dir)):
                    d_path = os.path.join(adapters_dir, d)
                    if os.path.isdir(d_path):
                        files_in_dir = os.listdir(d_path)
                        if any(f.endswith(".gguf") or f.endswith(".bin") for f in files_in_dir):
                            adapters.append(d)
            except Exception as e:
                logger.warning(f"Error scanning adapters: {e}")

        models_dir = "data/models"
        files = []
        if os.path.exists(models_dir):
            files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]

        entries = []
        for filename in sorted(files):
            meta = registry.get(filename, {})
            size = self._model_file_size_label(filename)
            detail = self._model_registry_detail(filename, meta, size)
            entries.append({
                "short_label": filename,
                "label": detail,
                "tooltip": self._model_tooltip(filename, meta, size, None),
                "data": {"model": filename, "adapter": None, "meta": meta},
            })
            for adapter in adapters:
                compatible = self._is_adapter_compatible(filename, adapter)
                if compatible:
                    entries.append({
                        "short_label": f"{filename} ({adapter})",
                        "label": f"{detail} · adapter {adapter}",
                        "tooltip": self._model_tooltip(filename, meta, size, adapter),
                        "data": {"model": filename, "adapter": adapter, "meta": meta},
                    })
        return entries

    def _model_file_size_label(self, filename: str) -> str:
        import os
        path = os.path.join("data", "models", filename)
        try:
            return f"{os.path.getsize(path) / (1024 ** 3):.2f} GB"
        except Exception:
            return "unknown size"

    def _model_registry_detail(self, filename: str, meta: dict, size: str) -> str:
        tier = meta.get("tier")
        n_ctx = meta.get("n_ctx")
        ram = meta.get("min_ram_gb")
        bits = [filename, size]
        if tier:
            bits.append(f"Tier {tier}")
        if n_ctx:
            bits.append(f"ctx {int(n_ctx):,}")
        if ram:
            bits.append(f"RAM {ram} GB")
        if filename == self.state.model_name:
            bits.append("ACTIVE")
        return " · ".join(bits)

    def _model_tooltip(self, filename: str, meta: dict, size: str, adapter: str | None) -> str:
        lines = [
            f"File: {filename}",
            f"Size: {size}",
            f"Adapter: {adapter or 'none'}",
        ]
        if meta:
            lines.extend([
                f"Registry name: {meta.get('name', filename)}",
                f"Tier: {meta.get('tier', 'unknown')}",
                f"Context: {meta.get('n_ctx', 'unknown')}",
                f"Recommended RAM: {meta.get('min_ram_gb', 'unknown')} GB",
            ])
        return "\n".join(lines)

    def _on_model_selected(self, index: int):
        data = self._model_combo.itemData(index)
        self._load_model_selection(data)

    def _on_header_model_staged(self, *_args):
        self._update_header_model_status(staged=True)

    def _load_header_selected_model(self):
        data = self._header_model_combo.currentData()
        self._load_model_selection(data)

    def _reload_active_model(self):
        if not self.state.model_name:
            self._chat_view.append_system_note("No active model is selected.")
            return
        self._load_model_selection({
            "model": self.state.model_name,
            "adapter": self.state.adapter_name,
            "meta": {},
            "force_reload": True,
        })

    def _load_model_selection(self, data: dict | None):
        if not isinstance(data, dict):
            return
            
        filename = data.get("model")
        adapter_name = data.get("adapter")
        
        if not data.get("force_reload") and filename == self.state.model_name and adapter_name == self.state.adapter_name:
            self._update_header_model_status()
            return
        
        from PyQt6.QtWidgets import QApplication
        import os

        # Disable inputs temporarily during model swap. The model combos are
        # disabled explicitly so a second selection cannot re-enter this
        # method while processEvents pumps the queue mid-load.
        self._set_busy(True)
        swap_controls = [
            c for c in (
                getattr(self, "_model_combo", None),
                getattr(self, "_header_model_combo", None),
                getattr(self, "_header_reload_model_btn", None),
            ) if c is not None
        ]
        for control in swap_controls:
            control.setEnabled(False)
        loading_text = f"Loading {filename} (adapter: {adapter_name})..." if adapter_name else f"Loading {filename}..."
        self.status_changed.emit(loading_text, True)
        QApplication.processEvents()
        
        try:
            from app.engine.model_loader import ModelLoader
            ModelLoader.reset_instance()
            # Force load the new model with adapter
            ModelLoader.get_instance(model_path=os.path.join("data", "models", filename), adapter_name=adapter_name)
            
            # Save the active model to active_model.json
            from app.engine import config_store
            if not config_store.set_active_model(filename, adapter_name):
                self._chat_view.append_system_note(
                    "[Warning] Could not persist data/active_model.json — "
                    "this selection will not survive a restart."
                )

            self.state.model_name = filename
            self.state.adapter_name = adapter_name
            
            self.model_changed.emit(filename)
            self.adapter_changed.emit(adapter_name or "")
            self._update_model_pill()
            self._refresh_model_combo()
            self._update_expert_strip()
            
            note = f"— Active model switched to: {filename} (adapter: {adapter_name or 'none'}) —"
            self._chat_view.append_system_note(note)
        except Exception as e:
            self._chat_view.append_system_note(f"[Error switching model: {str(e)}]")
            self._update_header_model_status(error=str(e))
        finally:
            for control in swap_controls:
                control.setEnabled(True)
            self._set_busy(False)
            self.status_changed.emit("idle", False)

    def _update_model_pill(self):
        model = self.state.model_name or "no model"
        adapter = self.state.adapter_name
        if adapter:
            self._model_pill.setText(f"● {model} ({adapter})")
        else:
            self._model_pill.setText(f"● {model}")
        self._update_header_model_status()

    def _update_header_model_status(self, staged: bool = False, error: str | None = None):
        if not hasattr(self, "_header_model_status"):
            return
        from app.engine.model_loader import ModelLoader
        model = self.state.model_name or "none"
        adapter = self.state.adapter_name or "none"
        n_ctx = ModelLoader.n_ctx() if ModelLoader.is_loaded() else "not loaded"
        if staged and hasattr(self, "_header_model_combo"):
            data = self._header_model_combo.currentData()
            if isinstance(data, dict):
                model = data.get("model") or model
                adapter = data.get("adapter") or "none"
                meta = data.get("meta") or {}
                n_ctx = meta.get("n_ctx", n_ctx)
        accent = get_theme_colors(self.state).get("accent", "#00C2FF")
        if error:
            self._header_model_status.setText(f"Model error: {error}")
            self._header_model_status.setStyleSheet("color: #FF3366;")
            return
        prefix = "Staged" if staged else "Active"
        self._header_model_status.setText(f"{prefix}: {model} · adapter {adapter} · ctx {n_ctx}")
        self._header_model_status.setStyleSheet(f"color: {accent}; font-weight: bold;")

    def _autosave_session(self):
        if not self.chat_history or len(self.chat_history) < 2:
            return
        try:
            path = self.chat_history.save(self._session_id)
            if self._session_id is None:
                import os
                self._session_id = os.path.splitext(os.path.basename(path))[0]
                self._current_session_file = path
            self._refresh_sessions()
        except Exception as e:
            logger.warning(f"Autosave failed: {e}")

    def _load_session(self, path: str):
        try:
            tree, session_id = SessionTree.load(path)
            self.chat_history = tree
            self._session_id = session_id
            self._current_session_file = path
            
            # Rebuild the chat view from the loaded tree
            self._chat_view.clear_display()
            active_path = self.chat_history.get_active_path()
            self._chat_view._messages = [(n.role, n.content, n.id, getattr(n, "attachments", [])) for n in active_path]
            self._chat_view._render_all()
            
            self._populate_branches_tree()
            
            self._is_correcting = False
            self._correct_btn.setText("✎ correct")
            
            last_node = active_path[-1] if active_path else None
            if last_node and last_node.role == "assistant":
                self._last_response = last_node.content
                self._last_thought = last_node.thought or ""
                self._reasoning_view.setPlainText(self._last_thought)
                self._thumb_btn.setEnabled(True)
                self._thumb_down_btn.setEnabled(True)
                self._correct_btn.setEnabled(True)
            else:
                self._last_response = ""
                self._last_thought = ""
                self._reasoning_view.clear()
                self._thumb_btn.setEnabled(False)
                self._thumb_down_btn.setEnabled(False)
                self._correct_btn.setEnabled(False)
                
            self._update_expert_strip()
            self._refresh_sessions()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load session: {e}")

    def _new_session(self):
        self._autosave_session()
        self.chat_history = SessionTree()
        self._session_id = None
        self._current_session_file = None
        self._pending_image_attachments = []
        self._pending_generation_history = None
        self._update_expert_strip()
        self._populate_branches_tree()

        self._chat_view.clear_display()
        self._reasoning_view.clear()
        self._last_response = ""
        self._last_thought = ""
        self._is_correcting = False
        self._correct_btn.setText("✎ correct")
        self._thumb_btn.setText("✓ good")
        self._thumb_down_btn.setText("✗ bad")
        self._thumb_btn.setEnabled(False)
        self._thumb_down_btn.setEnabled(False)
        self._correct_btn.setEnabled(False)
        self._sessions_list.blockSignals(True)
        self._sessions_list.setCurrentItem(None)
        self._sessions_list.blockSignals(False)
        self._update_token_budget()

    def _on_context_stats(self, total: int, hist: int, rag: int, budget: int):
        self._last_context_used = total
        self._last_hist_tokens  = hist
        self._last_rag_tokens   = rag
        self._update_token_budget()
        self.context_stats.emit(total, hist, rag, budget)
    
    def _on_rag_context_used(self, chunks: list):
        if not hasattr(self, '_rag_sources_view'):
            return
        if not chunks:
            self._rag_sources_view.setVisible(False)
            return
        self._rag_sources_view.setVisible(True)
        html_parts = []
        for chunk in chunks[:5]:
            src = chunk.get("source_file", "?")
            dist = chunk.get("distance", 0.0)
            text_preview = chunk.get("text", "")[:120].replace("<", "&lt;")
            html_parts.append(
                f"<div style='margin-bottom:8px; padding:6px; background:#0D0D1E; "
                f"border-left:2px solid #2DD4A0; border-radius:2px;'>"
                f"<span style='color:#2DD4A0; font-size:8pt;'>{src}</span> "
                f"<span style='color:#505068; font-size:7.5pt;'>dist={dist:.3f}</span><br/>"
                f"<span style='color:#9090A8; font-size:8pt;'>{text_preview}…</span>"
                f"</div>"
            )
        self._rag_sources_view.setHtml(
            f"<div style='font-family:monospace; padding:4px;'>{''.join(html_parts)}</div>"
        )

    # ── thread slots ──────────────────────────────────────────────────────────

    def _on_thought(self, token: str):
        cursor = self._reasoning_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self._reasoning_view.setTextCursor(cursor)
        self._reasoning_view.ensureCursorVisible()

    def _on_chat(self, token: str):
        if not self._chat_view._streaming:
            self._chat_view.begin_stream()
        self._chat_view.append_token(token)

    def _on_live_stats(self, count: int, speed: float):
        self._reasoning_stats_lbl.setText(f"({count} tokens · {speed:.1f} t/s)")

    def _on_done(self, thought: str, response: str, truncated: bool, _ended_in_thought: bool, diagnostics: dict | None = None):
        self._reasoning_stats_lbl.setText("")
        node = self.chat_history.add_message("assistant", response)
        node.thought = thought
        self._chat_view.finalize_stream(node.id)
        self._populate_branches_tree()
        self._last_response = response
        self._last_thought = thought
        if truncated:
            self._chat_view.append_system_note("— generation truncated —")

        if diagnostics:
            from app.engine.model_loader import ModelLoader
            model_name = ModelLoader.model_name()
            n_ctx = ModelLoader.n_ctx()
            self._chat_view.append_diagnostics(model_name, n_ctx, diagnostics)

        self._set_busy(False)
        self._is_correcting = False
        self._correct_btn.setText("✎ correct")
        self._thumb_btn.setText("✓ good")
        self._thumb_down_btn.setText("✗ bad")
        self._thumb_btn.setEnabled(True)
        self._thumb_down_btn.setEnabled(True)
        self._correct_btn.setEnabled(True)
        self._thread = None
        self.status_changed.emit("idle", False)
        self._save_current_session()
        self._update_token_budget()

    def _on_iteration(self, index: int, _thought: str, response: str, diagnostics: dict | None = None):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        diag_suffix = ""
        if diagnostics:
            diag_suffix = f" ({diagnostics.get('generation_tokens', 0)} tokens in {diagnostics.get('total_time', 0):.2f}s @ {diagnostics.get('total_tps', 0):.1f} t/s)"
        self._chat_view.append_system_note(f"— iteration {index + 1} complete{diag_suffix} —")
        self._last_response = response
        self._update_token_budget()

    def _on_loop_done(self, total: int):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        if self._thread and hasattr(self._thread, "chat_history"):
            thread_history = self._thread.chat_history
            original_len = len(self.chat_history)
            new_msgs = thread_history[original_len:]
            assistant_msgs = [
                msg for msg in new_msgs
                if msg.get("role") == "assistant" and msg.get("content", "").strip()
            ]
            if assistant_msgs:
                final_msg = assistant_msgs[-1]
                self.chat_history.add_message("assistant", final_msg["content"])
                self._last_response = final_msg["content"]
                self._last_thought = getattr(self, "_last_thought", "")
            
            # Refresh ChatView to ensure all messages have correct node_ids
            self._chat_view.clear_display()
            active_path = self.chat_history.get_active_path()
            self._chat_view._messages = [(n.role, n.content, n.id, getattr(n, "attachments", [])) for n in active_path]
            self._chat_view._render_all()
            self._populate_branches_tree()

        self._chat_view.append_system_note(f"— loop finished ({total} iterations) —")
        self._set_busy(False)
        self._thread = None
        self.status_changed.emit("idle", False)
        self._save_current_session()
        self._update_token_budget()

    def _on_error(self, msg: str):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        self._chat_view.append_system_note(f"error: {msg}")
        self._set_busy(False)
        self._thread = None
        self.status_changed.emit("error", False)
        self.update_model_state("error")

    # ── feedback ──────────────────────────────────────────────────────────────

    def _on_thumb_up(self):
        if self._last_response:
            prompt = self.chat_history[-2]["content"] if len(self.chat_history) >= 2 else ""
            self.state.curator.save_example(
                prompt=prompt,
                response=self._last_response,
                source="thumbs_up",
                system_prompt=self._system_prompt,
            )
            self.state.logger.update_last_entry_feedback(feedback="thumbs_up")
            self._thumb_btn.setText("✓ saved")
            self._thumb_btn.setEnabled(False)
            self._thumb_down_btn.setEnabled(False)

    def _on_thumb_down(self):
        if self._last_response:
            prompt = self.chat_history[-2]["content"] if len(self.chat_history) >= 2 else ""
            self.state.curator.save_example(
                prompt=prompt,
                response=self._last_response,
                source="thumbs_down",
                system_prompt=self._system_prompt,
            )
            self.state.logger.update_last_entry_feedback(feedback="thumbs_down")
            self._thumb_down_btn.setText("✗ saved")
            self._thumb_btn.setEnabled(False)
            self._thumb_down_btn.setEnabled(False)

    def _on_correct(self):
        self._correct_btn.setText("editing...")
        self._correct_btn.setEnabled(False)
        self._is_correcting = True
        self._input.setPlainText(self._last_response)
        self._input.setFocus()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _save_current_session(self):
        if not self.chat_history or len(self.chat_history) < 2:
            return
        try:
            path = self.chat_history.save(self._session_id)
            if self._session_id is None:
                import os
                self._session_id = os.path.splitext(os.path.basename(path))[0]
                self._current_session_file = path
            self._refresh_sessions()
        except Exception as e:
            logger.warning(f"Save failed: {e}")


    def _refresh_sessions(self):
        if not hasattr(self, '_sessions_list'):
            return
        self._sessions_list.blockSignals(True)
        self._sessions_list.clear()
        for meta in SessionTree.list_sessions():
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(meta["preview"] or meta["session_id"])
            item.setToolTip(meta["path"])
            item.setData(Qt.ItemDataRole.UserRole, meta["path"])
            self._sessions_list.addItem(item)
            
        if getattr(self, "_current_session_file", None):
            for idx in range(self._sessions_list.count()):
                item = self._sessions_list.item(idx)
                if item.data(Qt.ItemDataRole.UserRole) == self._current_session_file:
                    self._sessions_list.setCurrentItem(item)
                    break
        self._sessions_list.blockSignals(False)
        if hasattr(self, "_session_search"):
            self._filter_sessions(self._session_search.text())


    def _on_session_clicked(self, current, previous):
        if not current:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if path == getattr(self, "_current_session_file", None):
            return

        self._save_current_session()
        self._load_session(path)

    def on_close(self):
        self._save_current_session()

    def update_theme(self):
        theme_colors = get_theme_colors(self.state)
        self._chat_view.set_theme(theme_colors)
        
        # Update our toggle buttons style
        if hasattr(self, "_params_toggle"):
            self._params_toggle.update_style()
        if hasattr(self, "_sessions_toggle"):
            self._sessions_toggle.update_style()
        if hasattr(self, "_reasoning_toggle"):
            self._reasoning_toggle.update_style()
            
        # Update reasoning panel container accent color
        if hasattr(self, "_reasoning_panel_container"):
            accent = theme_colors.get("accent", "#00C2FF")
            self._reasoning_panel_container.set_accent_color(accent)
            self._reasoning_panel_container.update_style()
        if hasattr(self, "_theme_indicator"):
            accent = self.state.custom_accent or theme_colors.get("accent", "#00E5FF")
            self._theme_indicator.setText(f"Theme: {self.state.theme_preset} · Accent: {accent}")
            self._theme_indicator.setStyleSheet(f"color: {theme_colors.get('accent', '#00E5FF')}; font-weight: bold;")
        if hasattr(self, "_header_model_status"):
            self._update_header_model_status()

    def _set_busy(self, busy: bool):
        self._send_btn.setEnabled(not busy)
        self._stop_btn.setEnabled(busy)
        self._input.setEnabled(not busy)
        state_text = "generating..." if busy else "idle"
        self.status_changed.emit(state_text, busy)
        if hasattr(self, "_reasoning_panel_container"):
            self._reasoning_panel_container.set_active(busy)
        self.update_model_state("generating" if busy else "idle")

    def _on_chat_link_clicked(self, url):
        link = url.toString()
        if link.startswith("branch:"):
            node_id = link.split(":", 1)[1]
            self._branch_from_node(node_id)

    def _branch_from_node(self, node_id):
        if not self.chat_history:
            return
        if not self.chat_history.set_current_node(node_id):
            self._chat_view.append_system_note("branch target no longer exists")
            return
        self._update_expert_strip()

        
        node = self.chat_history.get_node(node_id)
        if node and node.role == "assistant":
            self._last_response = node.content
            self._last_thought = node.thought or ""
            self._reasoning_view.setPlainText(self._last_thought)
            self._thumb_btn.setEnabled(True)
            self._thumb_down_btn.setEnabled(True)
            self._correct_btn.setEnabled(True)
        else:
            self._last_response = ""
            self._last_thought = ""
            self._reasoning_view.clear()
            self._thumb_btn.setEnabled(False)
            self._thumb_down_btn.setEnabled(False)
            self._correct_btn.setEnabled(False)
            
        self._chat_view.clear_display()
        active_path = self.chat_history.get_active_path()
        self._chat_view._messages = [(n.role, n.content, n.id, getattr(n, "attachments", [])) for n in active_path]
        self._chat_view._render_all()
        
        self._populate_branches_tree()
        self._update_token_budget()
        self._input.setFocus()
        self._chat_view.append_system_note("branch cursor moved - write the next prompt to fork from this message")
        self._save_current_session()

    def _populate_branches_tree(self):
        self._branches_tree.blockSignals(True)
        self._branches_tree.clear()
        if not self.chat_history:
            if hasattr(self, "_branch_stats_lbl"):
                self._branch_stats_lbl.setText("Branches: 0 · Depth: 0 · Active: root")
            self._branches_tree.blockSignals(False)
            return

        root_node = self.chat_history.root
        self._tree_items_map = {}
        stats = self.chat_history.stats()
        if hasattr(self, "_branch_stats_lbl"):
            self._branch_stats_lbl.setText(
                f"Branches: {stats.leaf_count} · Messages: {stats.message_nodes} · "
                f"Depth: {self.chat_history.node_depth()} · Active: {self.chat_history.active_branch_label()}"
            )
        
        def _add_node(session_node, parent_item):
            snippet = session_node.content
            import re
            snippet = re.sub(r"<think>.*?</think>", "", snippet, flags=re.DOTALL).strip()
            if len(snippet) > 25:
                snippet = snippet[:22] + "..."
            
            role_label = "User" if session_node.role == "user" else "Karl"
            label = f"[{role_label}] {snippet}"
            
            if parent_item is None:
                item = QTreeWidgetItem(self._branches_tree)
            else:
                item = QTreeWidgetItem(parent_item)
                
            item.setText(0, label)
            item.setData(0, Qt.ItemDataRole.UserRole, session_node.id)
            
            if session_node.id == self.chat_history.current_id:
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                item.setForeground(0, QColor("#00C2FF"))
                self._branches_tree.setCurrentItem(item)
                
            self._tree_items_map[session_node.id] = item
            item.setExpanded(True)
            
            for child in session_node.children:
                _add_node(child, item)

        for child in root_node.children:
            _add_node(child, None)
            
        self._branches_tree.blockSignals(False)

    def _on_branch_clicked(self, item, column):
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_id:
            return
        if node_id == self.chat_history.current_id:
            return
        self._branch_from_node(node_id)

    def _branch_from_selected_tree_item(self):
        item = self._branches_tree.currentItem()
        if not item:
            return
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id:
            self._branch_from_node(node_id)

    # ── Expert Control Strip ──────────────────────────────────────────────────

    def _build_expert_strip(self) -> QWidget:
        strip = QFrame()
        strip.setObjectName("expert-strip")
        strip.setStyleSheet(
            "QFrame#expert-strip { background-color: #0D0D1B; border-bottom: 1px solid #1F1F3D; padding: 6px 12px; }"
            "QLabel { font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: #A0AEC0; }"
        )
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self._strip_session_lbl = QLabel("Session: None")
        self._strip_session_lbl.setStyleSheet("color: #00C2FF; font-weight: bold;")
        layout.addWidget(self._strip_session_lbl)
        
        self._strip_sep1 = _label("|", "lbl-muted")
        layout.addWidget(self._strip_sep1)
        
        self._strip_branch_lbl = QLabel("Branch: root")
        layout.addWidget(self._strip_branch_lbl)
        
        self._strip_sep2 = _label("|", "lbl-muted")
        layout.addWidget(self._strip_sep2)
        
        self._strip_model_lbl = QLabel("Model: None")
        layout.addWidget(self._strip_model_lbl)
        
        self._strip_sep3 = _label("|", "lbl-muted")
        layout.addWidget(self._strip_sep3)
        
        self._strip_rag_lbl = QLabel("RAG: OFF")
        layout.addWidget(self._strip_rag_lbl)
        
        self._strip_sep4 = _label("|", "lbl-muted")
        layout.addWidget(self._strip_sep4)
        
        self._strip_loop_lbl = QLabel("Loop: OFF")
        layout.addWidget(self._strip_loop_lbl)

        self._strip_sep5 = _label("|", "lbl-muted")
        layout.addWidget(self._strip_sep5)

        self._strip_agent_lbl = QLabel("Agent: Karl")
        layout.addWidget(self._strip_agent_lbl)
        
        layout.addStretch()
        
        # Add a small collapse button
        self._collapse_strip_btn = QPushButton("▲ collapse")
        self._collapse_strip_btn.setObjectName("btn-ghost")
        self._collapse_strip_btn.setFixedWidth(80)
        self._collapse_strip_btn.setStyleSheet("font-size: 7.5pt; padding: 2px;")
        self._collapse_strip_btn.clicked.connect(self._toggle_expert_strip)
        layout.addWidget(self._collapse_strip_btn)

        QTimer.singleShot(0, self._toggle_expert_strip)
        
        return strip

    def _toggle_expert_strip(self):
        is_collapsed = self._strip_branch_lbl.isHidden()
        self._strip_branch_lbl.setHidden(not is_collapsed)
        self._strip_model_lbl.setHidden(not is_collapsed)
        self._strip_rag_lbl.setHidden(not is_collapsed)
        self._strip_loop_lbl.setHidden(not is_collapsed)
        self._strip_sep1.setHidden(not is_collapsed)
        self._strip_sep2.setHidden(not is_collapsed)
        self._strip_sep3.setHidden(not is_collapsed)
        self._strip_sep4.setHidden(not is_collapsed)
        self._strip_sep5.setHidden(not is_collapsed)
        self._strip_agent_lbl.setHidden(not is_collapsed)
        
        if not is_collapsed:
            self._collapse_strip_btn.setText("▼ expand")
        else:
            self._collapse_strip_btn.setText("▲ collapse")

    def _update_expert_strip(self):
        # Session
        fname = self._current_session_file or "new_session"
        self._strip_session_lbl.setText(f"Session: {fname}")
        
        # Branch
        curr_branch = "root"
        if self.chat_history and self.chat_history.current_id:
            curr_branch = self.chat_history.current_id[:8]
        self._strip_branch_lbl.setText(f"Branch: {curr_branch}")
        
        # Model & Adapter
        model = self.state.model_name or "None"
        adapter = self.state.adapter_name
        model_text = f"Model: {model}"
        if adapter:
            model_text += f" ({adapter})"
        self._strip_model_lbl.setText(model_text)
        
        # RAG status
        rag_on = self._rag_check.isChecked()
        self._strip_rag_lbl.setText(f"RAG: {'ON' if rag_on else 'OFF'}")
        self._strip_rag_lbl.setStyleSheet(f"color: {'#00C2FF' if rag_on else '#A0AEC0'};")
        
        # Loop status
        loop_on = self._loop_check.isChecked()
        self._strip_loop_lbl.setText(f"Loop: {'ON' if loop_on else 'OFF'}")
        self._strip_loop_lbl.setStyleSheet(f"color: {'#00C2FF' if loop_on else '#A0AEC0'};")

        profile = AGENT_PROFILES.get(self._agent_profile, AGENT_PROFILES["karl"])
        self._strip_agent_lbl.setText(f"Agent: {profile['label']}")
        self._strip_agent_lbl.setToolTip(profile["description"])
        self._strip_agent_lbl.setStyleSheet(
            f"color: {'#00C2FF' if self._agent_profile != 'karl' else '#A0AEC0'};"
        )

    # ── Sessions Upgrades ─────────────────────────────────────────────────────

    def _filter_sessions(self, text):
        query = text.strip().lower()
        for idx in range(self._sessions_list.count()):
            item = self._sessions_list.item(idx)
            item.setHidden(query not in item.text().lower())

    def _show_session_context_menu(self, pos):
        item = self._sessions_list.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #0D0D1B; border: 1px solid #1F1F3D; color: #F0F5FF; font-family: 'JetBrains Mono', monospace; font-size: 9pt; }"
            "QMenu::item:selected { background-color: #00C2FF; color: #020205; }"
        )
        
        rename_action = menu.addAction("Rename Session")
        dup_action = menu.addAction("Duplicate Session")
        del_action = menu.addAction("Delete Session")
        
        action = menu.exec(self._sessions_list.mapToGlobal(pos))
        if not action:
            return
            
        fname = item.text()
        if action == rename_action:
            self._rename_session(fname)
        elif action == dup_action:
            self._duplicate_session(fname)
        elif action == del_action:
            self._delete_session(fname)

    def _rename_session(self, fname):
        import os
        new_name, ok = QInputDialog.getText(
            self, "Rename Session", "Enter new filename (must end in .json):",
            text=fname
        )
        if not ok or not new_name.strip():
            return
            
        if not new_name.endswith(".json"):
            new_name = new_name.strip() + ".json"
            
        old_path = os.path.join(self.state.memory.sessions_dir, fname)
        new_path = os.path.join(self.state.memory.sessions_dir, new_name)
        
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Error", "A session with that name already exists.")
            return
            
        try:
            os.rename(old_path, new_path)
            if self._current_session_file == fname:
                self._current_session_file = new_name
            self._refresh_sessions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename file: {e}")

    def _duplicate_session(self, fname):
        import os
        old_path = os.path.join(self.state.memory.sessions_dir, fname)
        base, ext = os.path.splitext(fname)
        new_name = f"{base}_copy{ext}"
        new_path = os.path.join(self.state.memory.sessions_dir, new_name)
        
        counter = 1
        while os.path.exists(new_path):
            new_name = f"{base}_copy{counter}{ext}"
            new_path = os.path.join(self.state.memory.sessions_dir, new_name)
            counter += 1
            
        try:
            import shutil
            shutil.copy2(old_path, new_path)
            self._refresh_sessions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to duplicate file: {e}")

    def _delete_session(self, fname):
        import os
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete session '{fname}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            path = os.path.join(self.state.memory.sessions_dir, fname)
            try:
                os.remove(path)
                if self._current_session_file == fname:
                    self._current_session_file = None
                    self.chat_history.clear()
                    self._populate_branches_tree()
                    self._chat_view.clear_display()
                    self._reasoning_view.clear()
                    self._last_response = ""
                    self._last_thought = ""
                    self._is_correcting = False
                self._refresh_sessions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")

    # ── public API for main_window ────────────────────────────────────────────

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt

    def set_hyperparams(self, params: dict):
        self._hyperparams.update(params)
        if hasattr(self, "_temp_spin") and "temperature" in params:
            self._temp_spin.blockSignals(True)
            self._temp_spin.setValue(params["temperature"])
            self._temp_spin.blockSignals(False)
        if hasattr(self, "_topp_spin") and "top_p" in params:
            self._topp_spin.blockSignals(True)
            self._topp_spin.setValue(params["top_p"])
            self._topp_spin.blockSignals(False)
        if hasattr(self, "_maxtok_spin") and "max_tokens" in params:
            self._maxtok_spin.blockSignals(True)
            self._maxtok_spin.setValue(params["max_tokens"])
            self._maxtok_spin.blockSignals(False)

    def append_to_input(self, text: str):
        existing = self._input.toPlainText()
        if existing:
            self._input.setPlainText(existing + "\n" + text)
        else:
            self._input.setPlainText(text)
