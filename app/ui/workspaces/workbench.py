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

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QTextEdit, QComboBox,
    QLabel, QSizePolicy, QFrame, QCheckBox,
    QDoubleSpinBox, QSpinBox, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QMainWindow, QDockWidget,
    QTabWidget, QLineEdit, QMenu, QInputDialog, QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QUrl
from PyQt6.QtGui import QTextCursor, QKeySequence, QShortcut, QColor


from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.engine.image_analysis_thread import ImageAnalysisThread
from core.workflows import list_workflows
from app.utils.session_tree import SessionTree
from app.ui.widgets.tracing_panel import TracingPanel
from app.ui.themes import get_theme_colors
from app.ui.widgets.symbolic_icon import IconBtn, GearIcon, HamburgerIcon, BrainIcon, ThumbsUpIcon, ThumbsDownIcon


# ── helpers ──────────────────────────────────────────────────────────────────

def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _label(text: str, obj: str = "") -> QLabel:
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    return l


# ── chat display ─────────────────────────────────────────────────────────────

class ChatView(QTextBrowser):
    """Scrollable conversation display with streaming support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        self._messages: list[tuple[str, str, str]] = []   # (role, text, node_id)
        self._streaming_buf = ""
        self._streaming = False
        self._streaming_node_id = ""
        # Default fallback theme colors
        self.theme_colors = {
            "text_lo": "#505068",
            "accent": "#00C2FF",
            "bg_raised": "#1C1C2A",
            "border_hi": "#383850",
            "text_hi": "#E4E4F0",
            "bg_surface": "#14141F",
            "border": "#252535",
            "yellow": "#F0B030",
        }

    def set_theme(self, theme_colors: dict):
        self.theme_colors = theme_colors
        self._render_all()

    # public API ──────────────────────────────────────────────────────────────

    def push_user(self, text: str, node_id: str, attachments: list[dict] | None = None):
        self._finalize_stream()
        self._messages.append(("user", text, node_id, attachments or []))
        self._render_all()

    def _get_karl_hdr(self, node_id: str) -> str:
        text_lo = self.theme_colors.get("text_lo", "#505068")
        accent = self.theme_colors.get("accent", "#00C2FF")
        bg_surface = self.theme_colors.get("bg_surface", "#14141F")
        border = self.theme_colors.get("border", "#252535")
        text_hi = self.theme_colors.get("text_hi", "#E4E4F0")
        return (
            f'<div style="margin:16px 80px 4px 0px;">'
            f'<div style="color:{text_lo};font-size:7.5pt;font-weight:bold;margin-bottom:4px;letter-spacing:1.5px;">'
            f'KARL &nbsp;|&nbsp; <a href="branch:{node_id}" style="color:{accent};text-decoration:none;font-weight:bold;">↳ branch</a></div>'
            f'<div style="background:{bg_surface};border:1px solid {border};border-radius:6px;'
            f'padding:12px 16px;color:{text_hi};font-size:10pt;'
            f'line-height:1.4;white-space:pre-wrap;min-height:1em;">'
        )

    def _get_user_html(self, text: str, node_id: str, attachments: list[dict] | None = None) -> str:
        text_lo = self.theme_colors.get("text_lo", "#505068")
        accent = self.theme_colors.get("accent", "#00C2FF")
        bg_raised = self.theme_colors.get("bg_raised", "#1C1C2A")
        border_hi = self.theme_colors.get("border_hi", "#383850")
        text_hi = self.theme_colors.get("text_hi", "#E4E4F0")
        safe_text = _escape(text)
        return (
            f'<div style="margin:16px 0px 4px 80px; text-align:right;">'
            f'<div style="color:{text_lo};font-size:7.5pt;font-weight:bold;margin-bottom:4px;letter-spacing:1.5px;">'
            f'YOU &nbsp;|&nbsp; <a href="branch:{node_id}" style="color:{accent};text-decoration:none;font-weight:bold;">↳ branch</a></div>'
            f'<div style="background:{bg_raised};border:1px solid {border_hi};border-radius:6px;'
            f'padding:12px 16px;color:{text_hi};font-size:10pt;'
            f'line-height:1.4;white-space:pre-wrap;display:inline-block;text-align:left;">{safe_text}'
            f'{self._attachments_html(attachments or [])}</div>'
            f'</div>'
        )

    def _attachments_html(self, attachments: list[dict]) -> str:
        if not attachments:
            return ""
        accent = self.theme_colors.get("accent", "#00C2FF")
        text_lo = self.theme_colors.get("text_lo", "#505068")
        border = self.theme_colors.get("border", "#252535")
        parts = []
        for attachment in attachments:
            if attachment.get("type") != "image":
                continue
            path = attachment.get("thumbnail_path") or attachment.get("path") or ""
            image_id = attachment.get("id", "")
            label = attachment.get("label") or image_id[:8] or "image"
            uri = ""
            try:
                if path:
                    uri = QUrl.fromLocalFile(str(Path(path).resolve())).toString()
            except Exception:
                uri = ""
            image_html = f'<img src="{uri}" style="max-width:260px;max-height:180px;border-radius:4px;margin-top:6px;">' if uri else ""
            parts.append(
                f'<div style="margin-top:10px;padding:8px;border:1px solid {border};border-radius:5px;">'
                f'<div style="color:{accent};font-size:8pt;font-weight:bold;">IMAGE ATTACHMENT</div>'
                f'<div style="color:{text_lo};font-size:8pt;">{_escape(label)}</div>'
                f'{image_html}'
                f'</div>'
            )
        return "".join(parts)


    def begin_stream(self, node_id: str = ""):
        self._streaming = True
        self._streaming_buf = ""
        self._streaming_node_id = node_id
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertHtml(self._get_karl_hdr(node_id))

    def append_token(self, token: str):
        if not self._streaming:
            return
        self._streaming_buf += token
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def finalize_stream(self, node_id: str = ""):
        if not self._streaming:
            return
        final_node_id = node_id or self._streaming_node_id
        self._messages.append(("assistant", self._streaming_buf, final_node_id, []))
        self._streaming_buf = ""
        self._streaming = False
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.insertHtml('</div></div>')
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self._render_all()

    def clear_display(self):
        self._messages.clear()
        self._streaming_buf = ""
        self._streaming = False
        self.clear()

    def replace_last_assistant(self, text: str):
        if self._messages and self._messages[-1][0] == "assistant":
            self._messages[-1] = ("assistant", text, self._messages[-1][2], self._messages[-1][3] if len(self._messages[-1]) > 3 else [])
            self._render_all()

    def append_system_note(self, text: str):
        self._finalize_stream()
        safe = _escape(text)
        text_lo = self.theme_colors.get("text_lo", "#505068")
        html = (
            f'<div style="margin:6px 0;color:{text_lo};font-size:8pt;'
            f'text-align:center;">{safe}</div>'
        )
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        self.ensureCursorVisible()

    def append_diagnostics(self, model: str, n_ctx: int, diag: dict):
        self._finalize_stream()
        bg_raised = self.theme_colors.get("bg_raised", "#1C1C2A")
        border = self.theme_colors.get("border", "#252535")
        text_hi = self.theme_colors.get("text_hi", "#E4E4F0")
        text_lo = self.theme_colors.get("text_lo", "#505068")
        accent = self.theme_colors.get("accent", "#00C2FF")
        yellow = self.theme_colors.get("yellow", "#F0B030")

        html_str = (
            f'<div style="margin: 8px 80px 8px 0px; padding: 10px 14px; '
            f'background: {bg_raised}; border: 1px solid {border}; border-radius: 4px; '
            f'font-family: \'JetBrains Mono\', monospace; font-size: 8.5pt;">'
            f'<div style="color: {accent}; font-weight: bold; margin-bottom: 6px; letter-spacing: 1.5px;">📊 GENERATION DIAGNOSTICS</div>'
            f'<div style="color: {text_hi}; margin-bottom: 4px;"><b>Model:</b> {model} (n_ctx={n_ctx})</div>'
            f'<div style="color: {text_hi}; margin-bottom: 4px;">'
            f'<b>Prompt:</b> {diag.get("prompt_tokens", 0)} tokens '
            f'<span style="color: {text_lo};">(prefill: {diag.get("prefill_time", 0):.2f}s @ {diag.get("prefill_tps", 0):.1f} t/s)</span>'
            f'</div>'
            f'<div style="color: {text_hi}; margin-bottom: 4px;">'
            f'<b>Generation:</b> {diag.get("generation_tokens", 0)} tokens '
            f'<span style="color: {text_lo};">(generated: {diag.get("generation_time", 0):.2f}s @ {diag.get("generation_tps", 0):.1f} t/s)</span>'
            f'</div>'
            f'<div style="color: {yellow}; font-weight: bold; margin-top: 6px; letter-spacing: 0.5px;">'
            f'Total Time: {diag.get("total_time", 0):.2f}s @ {diag.get("total_tps", 0):.1f} t/s'
            f'</div>'
            f'</div>'
        )
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html_str)
        self.ensureCursorVisible()

    def append_rag_sources(self, results: list[dict]):
        self._finalize_stream()
        if not results:
            return
        bg_raised = self.theme_colors.get("bg_raised", "#1C1C2A")
        border_hi = self.theme_colors.get("border_hi", "#383850")
        accent = self.theme_colors.get("accent", "#00C2FF")
        text_hi = self.theme_colors.get("text_hi", "#E4E4F0")
        yellow = self.theme_colors.get("yellow", "#F0B030")
        
        lines = []
        lines.append(
            f'<div style="margin:8px 60px 8px 10px; padding:10px 12px; '
            f'background:{bg_raised}; border:1px solid {border_hi}; border-radius:4px; '
            f'font-family: \'JetBrains Mono\', monospace; font-size:8.5pt;">'
        )
        lines.append(f'<div style="color:{accent}; font-weight:bold; margin-bottom:6px;">🔍 Injected RAG Context:</div>')
        for r in results:
            lines.append(
                f'<div style="color:{text_hi}; margin-bottom:4px;">'
                f'• <b>{_escape(r["source_file"])}</b> (Chunk {r["chunk_id"]}, distance: '
                f'<span style="color:{yellow};">{r["distance"]:.4f}</span>)'
                f'</div>'
            )
        lines.append('</div>')
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml("".join(lines))
        self.ensureCursorVisible()

    # internals ───────────────────────────────────────────────────────────────

    def _finalize_stream(self):
        if self._streaming:
            self.finalize_stream()

    def _render_all(self):
        parts = []
        for raw in self._messages:
            if len(raw) == 3:
                role, text, node_id = raw
                attachments = []
            else:
                role, text, node_id, attachments = raw
            if role == "user":
                parts.append(self._get_user_html(text, node_id, attachments))
            else:
                parts.append(self._get_karl_hdr(node_id) + _escape(text) + '</div></div>')
        self.setHtml(
            '<html><body style="background:transparent;margin:8px;">'
            + "".join(parts)
            + "</body></html>"
        )
        self.moveCursor(QTextCursor.MoveOperation.End)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
    )


# ── workbench workspace ───────────────────────────────────────────────────────

class WorkbenchWorkspace(QMainWindow):
    status_changed = pyqtSignal(str, bool)   # (text, active)
    model_changed = pyqtSignal(str)          # (model_name)
    adapter_changed = pyqtSignal(str)        # (adapter_name)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")

        self.chat_history = SessionTree()
        self._thread: LLMThread | AgenticThread | None = None
        self._active_threads = set()
        self._last_response = ""
        self._last_thought = ""
        self._hyperparams = {
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 2048,
        }
        self._system_prompt = (
            "You are Karl, a precise and thoughtful AI assistant. "
            "Always respond in English. "
            "Analyze and break down problems step-by-step. "
            "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
            "Double-check your derivations and arithmetic before writing the final answer."
        )
        self._current_session_file: str | None = None
        self._is_correcting = False
        self._pending_image_attachments: list[dict] = []
        self._pending_generation_history: list[dict] | None = None
        self._image_threads = set()

        self._build_ui()
        
        # Initialize dynamic chat bubble colors from theme config
        from app.ui.themes import get_theme_colors
        self._chat_view.set_theme(get_theme_colors(self.state))

        self._connect_shortcuts()
        self._refresh_sessions()
        self._refresh_model_combo()
        self._update_expert_strip()


    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
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

        # chat display
        self._chat_view = ChatView(w)
        self._chat_view.anchorClicked.connect(self._on_chat_link_clicked)
        layout.addWidget(self._chat_view, 1)

        layout.addWidget(_hline())

        # feedback row (shown after each generation)
        feedback_row = QWidget()
        feedback_row.setFixedHeight(32)
        fb_layout = QHBoxLayout(feedback_row)
        fb_layout.setContentsMargins(10, 2, 10, 2)
        fb_layout.setSpacing(8)
        fb_layout.addStretch()

        self._thumb_btn = QPushButton("✓ good")
        self._thumb_btn.setObjectName("btn-success")
        self._thumb_btn.setEnabled(False)
        self._thumb_btn.setToolTip("Curate this response as a positive training example")
        self._thumb_btn.clicked.connect(self._on_thumb_up)

        self._thumb_down_btn = QPushButton("✗ bad")
        self._thumb_down_btn.setObjectName("btn-danger")
        self._thumb_down_btn.setEnabled(False)
        self._thumb_down_btn.setToolTip("Flag this response as an incorrect/negative training example")
        self._thumb_down_btn.clicked.connect(self._on_thumb_down)

        self._correct_btn = QPushButton("✎ correct")
        self._correct_btn.setObjectName("btn-warning")
        self._correct_btn.setEnabled(False)
        self._correct_btn.setToolTip("Manually edit the response to create a corrected training pair")
        self._correct_btn.clicked.connect(self._on_correct)

        self._new_session_btn = QPushButton("+ new session")
        self._new_session_btn.setObjectName("btn-ghost")
        self._new_session_btn.setToolTip("Clear chat history and start a fresh session")
        self._new_session_btn.clicked.connect(self._new_session)

        for b in (self._thumb_btn, self._thumb_down_btn, self._correct_btn, self._new_session_btn):
            fb_layout.addWidget(b)

        layout.addWidget(feedback_row)
        layout.addWidget(_hline())

        # params drawer (collapsed by default)
        self._params_drawer = self._build_params_drawer()
        self._params_drawer.setVisible(False)
        layout.addWidget(self._params_drawer)
        layout.addWidget(_hline())


        # input area
        input_container = QWidget()
        input_container.setFixedHeight(120)
        ic_layout = QVBoxLayout(input_container)
        ic_layout.setContentsMargins(8, 6, 8, 6)
        ic_layout.setSpacing(6)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Ask Karl...")
        self._input.setFixedHeight(72)
        self._input.installEventFilter(self)
        ic_layout.addWidget(self._input)

        # controls
        ctrl = QWidget()
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        self._workflow_combo = QComboBox()
        self._workflow_combo.setFixedWidth(160)
        self._workflow_combo.setToolTip("Active prompt generation workflow template")
        for name, label in list_workflows():
            self._workflow_combo.addItem(label, name)
        # Select "general_chat" by default (rather than alphabetically first "code_review")
        default_idx = self._workflow_combo.findData("general_chat")
        if default_idx >= 0:
            self._workflow_combo.setCurrentIndex(default_idx)
        ctrl_layout.addWidget(self._workflow_combo)

        self._rag_check = QCheckBox("RAG")
        self._rag_check.setToolTip("Inject relevant knowledge base context into prompt")
        self._rag_check.toggled.connect(self._update_expert_strip)
        ctrl_layout.addWidget(self._rag_check)

        self._loop_check = QCheckBox("Loop")
        self._loop_check.setToolTip("Run generation in an autonomous iterative agentic loop")
        self._loop_check.toggled.connect(self._update_expert_strip)
        ctrl_layout.addWidget(self._loop_check)


        self._params_toggle = IconBtn(GearIcon, self.state, tooltip="Toggle generation parameters")
        self._params_toggle.clicked.connect(self._toggle_params)
        ctrl_layout.addWidget(self._params_toggle)

        self._sessions_toggle = IconBtn(HamburgerIcon, self.state, tooltip="Toggle Sessions panel")
        self._sessions_toggle.clicked.connect(self._toggle_sessions)
        ctrl_layout.addWidget(self._sessions_toggle)

        self._reasoning_toggle = IconBtn(BrainIcon, self.state, tooltip="Toggle Reasoning panel")
        self._reasoning_toggle.clicked.connect(self._toggle_reasoning)
        ctrl_layout.addWidget(self._reasoning_toggle)

        ctrl_layout.addStretch()

        self._model_pill = QLabel("● no model")
        self._model_pill.setObjectName("model-pill")
        self._model_pill.setToolTip("Active base model and adapter overlay")
        ctrl_layout.addWidget(self._model_pill)

        self._stop_btn = QPushButton("■ stop")
        self._stop_btn.setObjectName("btn-danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setToolTip("Interrupt the active generation thread")
        self._stop_btn.clicked.connect(self._stop)
        ctrl_layout.addWidget(self._stop_btn)

        self._send_btn = QPushButton("send ↵")
        self._send_btn.setObjectName("btn-primary")
        self._send_btn.setToolTip("Send prompt to Karl (Ctrl+Enter)")
        self._send_btn.clicked.connect(self._send)
        ctrl_layout.addWidget(self._send_btn)

        ic_layout.addWidget(ctrl)
        layout.addWidget(input_container)

        return w


    def _build_params_drawer(self) -> QWidget:
        drawer = QWidget()
        drawer.setFixedHeight(40)
        dl = QHBoxLayout(drawer)
        dl.setContentsMargins(10, 4, 10, 4)
        dl.setSpacing(12)

        # Model Selector
        dl.addWidget(_label("model", "lbl-muted"))
        self._model_combo = QComboBox()
        self._model_combo.setFixedWidth(180)
        self._model_combo.setToolTip("Select active model and adapter overlay")
        self._model_combo.currentIndexChanged.connect(self._on_model_selected)
        dl.addWidget(self._model_combo)

        # Temperature
        dl.addWidget(_label("temp", "lbl-muted"))
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.05)
        self._temp_spin.setValue(self._hyperparams["temperature"])
        self._temp_spin.setFixedWidth(70)
        self._temp_spin.setToolTip("Generation temperature. Lower is more deterministic, higher is more creative.")
        self._temp_spin.valueChanged.connect(
            lambda v: self._hyperparams.__setitem__("temperature", v)
        )
        dl.addWidget(self._temp_spin)

        # Top-p
        dl.addWidget(_label("top-p", "lbl-muted"))
        self._topp_spin = QDoubleSpinBox()
        self._topp_spin.setRange(0.0, 1.0)
        self._topp_spin.setSingleStep(0.05)
        self._topp_spin.setValue(self._hyperparams["top_p"])
        self._topp_spin.setFixedWidth(70)
        self._topp_spin.setToolTip("Top-p sampling cutoff. Keeps only tokens within this cumulative probability mass.")
        self._topp_spin.valueChanged.connect(
            lambda v: self._hyperparams.__setitem__("top_p", v)
        )
        dl.addWidget(self._topp_spin)

        # Max tokens
        dl.addWidget(_label("max tok", "lbl-muted"))
        self._maxtok_spin = QSpinBox()
        self._maxtok_spin.setRange(64, 8192)
        self._maxtok_spin.setSingleStep(64)
        self._maxtok_spin.setValue(self._hyperparams["max_tokens"])
        self._maxtok_spin.setFixedWidth(80)
        self._maxtok_spin.setToolTip("Maximum number of tokens to generate.")
        self._maxtok_spin.valueChanged.connect(
            lambda v: self._hyperparams.__setitem__("max_tokens", v)
        )
        dl.addWidget(self._maxtok_spin)

        dl.addStretch()
        return drawer

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
            if self.state.rag.total_chunks > 0:
                retrieved_metadata.extend(self.state.rag.retrieve_with_metadata(prompt_text, top_k=top_k))
                
            if hasattr(self.state, "codex_rag") and self.state.codex_rag.total_chunks > 0:
                retrieved_metadata.extend(self.state.codex_rag.retrieve_with_metadata(prompt_text, top_k=top_k))
                
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
            except Exception:
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

    def _start_single(self, chunks: list[str]):
        self._chat_view.begin_stream()
        self._set_busy(True)
        self._reasoning_stats_lbl.setText("")
        history = self._pending_generation_history or list(self.chat_history)
        self._pending_generation_history = None
        t = LLMThread(
            system_prompt=self._system_prompt,
            chat_history=history,
            hyperparams=self._hyperparams,
            retrieved_chunks=chunks,
            workflow=self._current_workflow(),
            template=self._current_template(),
            adapter_name=self.state.adapter_name,
        )
        t.new_thought_token.connect(self._on_thought)
        t.new_chat_token.connect(self._on_chat)
        t.live_stats.connect(self._on_live_stats)
        t.generation_finished.connect(self._on_done)
        t.error_occurred.connect(self._on_error)
        
        # Keep thread alive in active set to prevent early garbage collection (fixes core dumps)
        self._active_threads.add(t)
        t.finished.connect(lambda: self._active_threads.discard(t))
        t.finished.connect(t.deleteLater)
        
        self._thread = t
        t.start()

    def _start_agentic(self, chunks: list[str]):
        self._set_busy(True)
        self._reasoning_stats_lbl.setText("")
        self._chat_view.append_system_note("— agentic loop started —")
        history = self._pending_generation_history or list(self.chat_history)
        self._pending_generation_history = None
        t = AgenticThread(
            system_prompt=self._system_prompt,
            initial_history=history,
            hyperparams=self._hyperparams,
            retrieved_chunks=chunks,
            workflow=self._current_workflow(),
            template=self._current_template(),
            adapter_name=self.state.adapter_name,
        )
        t.new_thought_token.connect(self._on_thought)
        t.new_chat_token.connect(self._on_chat)
        t.live_stats.connect(self._on_live_stats)
        t.iteration_finished.connect(self._on_iteration)
        t.loop_finished.connect(self._on_loop_done)
        t.error_occurred.connect(self._on_error)
        
        # Keep thread alive in active set to prevent early garbage collection (fixes core dumps)
        self._active_threads.add(t)
        t.finished.connect(lambda: self._active_threads.discard(t))
        t.finished.connect(t.deleteLater)
        
        self._thread = t
        t.start()

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

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_model_combo()

    def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool:
        import json
        import os
        config_path = os.path.join("data", "adapters", adapter_name, "adapter_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                base_model = config.get("base_model_name_or_path", "").lower()
                model_fn = model_filename.lower()
                if "1.5b" in model_fn and "1.5b" in base_model:
                    return True
                if "8b" in model_fn and "8b" in base_model:
                    return True
            except Exception:
                pass
        # Fallback to simple sub-string matching on name
        if "1.5b" in model_filename.lower() and "1.5b" in adapter_name.lower():
            return True
        if "8b" in model_filename.lower() and "8b" in adapter_name.lower():
            return True
        return False

    def _refresh_model_combo(self):
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        
        import os
        adapters_dir = "data/adapters"
        adapters = []
        if os.path.exists(adapters_dir):
            try:
                for d in sorted(os.listdir(adapters_dir)):
                    d_path = os.path.join(adapters_dir, d)
                    if os.path.isdir(d_path):
                        # check for gguf/bin files
                        files_in_dir = os.listdir(d_path)
                        if any(f.endswith(".gguf") or f.endswith(".bin") for f in files_in_dir):
                            adapters.append(d)
            except Exception as e:
                print(f"[Workbench] Error scanning adapters: {e}")

        models_dir = "data/models"
        files = []
        if os.path.exists(models_dir):
            files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
            
        for f in sorted(files):
            # Base model
            self._model_combo.addItem(f, {"model": f, "adapter": None})
            # List compatible adapters
            for adapter in adapters:
                if self._is_adapter_compatible(f, adapter):
                    self._model_combo.addItem(f"{f} ({adapter})", {"model": f, "adapter": adapter})
            
        # Select active model and adapter combination
        active_model = self.state.model_name
        active_adapter = self.state.adapter_name
        
        found = False
        for idx in range(self._model_combo.count()):
            d = self._model_combo.itemData(idx)
            if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") == active_adapter:
                self._model_combo.setCurrentIndex(idx)
                found = True
                break
                
        if not found:
            for idx in range(self._model_combo.count()):
                d = self._model_combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") is None:
                    self._model_combo.setCurrentIndex(idx)
                    found = True
                    break
                    
        if not found and self._model_combo.count() > 0:
            self._model_combo.setCurrentIndex(0)
                
        self._update_model_pill()
        self._model_combo.blockSignals(False)

    def _on_model_selected(self, index: int):
        data = self._model_combo.itemData(index)
        if not isinstance(data, dict):
            return
            
        filename = data.get("model")
        adapter_name = data.get("adapter")
        
        if filename == self.state.model_name and adapter_name == self.state.adapter_name:
            return
        
        from PyQt6.QtWidgets import QApplication
        import json
        import os
        
        # Disable inputs temporarily during model swap
        self._set_busy(True)
        loading_text = f"Loading {filename} (adapter: {adapter_name})..." if adapter_name else f"Loading {filename}..."
        self.status_changed.emit(loading_text, True)
        QApplication.processEvents()
        
        try:
            from app.engine.model_loader import ModelLoader
            ModelLoader.reset_instance()
            # Force load the new model with adapter
            ModelLoader.get_instance(model_path=os.path.join("data", "models", filename), adapter_name=adapter_name)
            
            # Save the active model to active_model.json
            active = {
                "filename": filename,
                "adapter": adapter_name
            }
            os.makedirs("data", exist_ok=True)
            with open("data/active_model.json", "w") as f:
                json.dump(active, f)
                
            self.state.model_name = filename
            self.state.adapter_name = adapter_name
            
            self.model_changed.emit(filename)
            self.adapter_changed.emit(adapter_name or "")
            self._update_model_pill()
            
            note = f"— Active model switched to: {filename} (adapter: {adapter_name or 'none'}) —"
            self._chat_view.append_system_note(note)
        except Exception as e:
            self._chat_view.append_system_note(f"[Error switching model: {str(e)}]")
        finally:
            self._set_busy(False)
            self.status_changed.emit("idle", False)

    def _update_model_pill(self):
        model = self.state.model_name or "no model"
        adapter = self.state.adapter_name
        if adapter:
            self._model_pill.setText(f"● {model} ({adapter})")
        else:
            self._model_pill.setText(f"● {model}")

    def _new_session(self):
        self._save_current_session()
        self._current_session_file = None
        self.chat_history.clear()
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

    def _on_iteration(self, index: int, _thought: str, response: str, diagnostics: dict | None = None):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        diag_suffix = ""
        if diagnostics:
            diag_suffix = f" ({diagnostics.get('generation_tokens', 0)} tokens in {diagnostics.get('total_time', 0):.2f}s @ {diagnostics.get('total_tps', 0):.1f} t/s)"
        self._chat_view.append_system_note(f"— iteration {index + 1} complete{diag_suffix} —")
        self._last_response = response

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

    def _on_error(self, msg: str):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        self._chat_view.append_system_note(f"error: {msg}")
        self._set_busy(False)
        self._thread = None
        self.status_changed.emit("error", False)

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
        if not self.chat_history:
            return
        from app.engine.model_loader import ModelLoader
        # Calculate message count on the active path
        msg_count = len(self.chat_history) if not hasattr(self.chat_history, "get_active_path") else len(self.chat_history.get_active_path())
        self._current_session_file = self.state.memory.save_session(
            chat_history=self.chat_history,
            system_prompt=self._system_prompt,
            filename=self._current_session_file,
            last_model=ModelLoader.model_name() if ModelLoader.is_loaded() else "unknown",
            adapter_name=self.state.adapter_name,
            message_count=msg_count
        )
        self._refresh_sessions()


    def _refresh_sessions(self):
        self._sessions_list.blockSignals(True)
        self._sessions_list.clear()
        sessions = self.state.memory.list_sessions_with_metadata()
        for s in sessions:
            fname = s["filename"]
            msg_count = s["message_count"]
            model = s["last_model"]
            adapter = s["adapter_name"]
            
            item = QListWidgetItem(fname)
            tooltip = f"File: {fname}\nUpdated: {s['updated_time']}\nMessages: {msg_count}\nModel: {model}"
            if adapter:
                tooltip += f"\nAdapter: {adapter}"
            item.setToolTip(tooltip)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self._sessions_list.addItem(item)
            
        if getattr(self, "_current_session_file", None):
            items = self._sessions_list.findItems(self._current_session_file, Qt.MatchFlag.MatchFixedString)
            if items:
                self._sessions_list.setCurrentItem(items[0])
        self._sessions_list.blockSignals(False)
        if hasattr(self, "_session_search"):
            self._filter_sessions(self._session_search.text())


    def _on_session_clicked(self, current, previous):
        if not current:
            return
        filename = current.text()
        if filename == getattr(self, "_current_session_file", None):
            return

        self._save_current_session()

        sys_prompt, history = self.state.memory.load_session(filename)
        self._current_session_file = filename
        self._system_prompt = sys_prompt
        self.chat_history = history
        self._update_expert_strip()


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
            self._thumb_btn.setText("✓ good")
            self._thumb_down_btn.setText("✗ bad")
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

    def _set_busy(self, busy: bool):
        self._send_btn.setEnabled(not busy)
        self._stop_btn.setEnabled(busy)
        self._input.setEnabled(not busy)
        state_text = "generating..." if busy else "idle"
        self.status_changed.emit(state_text, busy)
        if hasattr(self, "_reasoning_panel_container"):
            self._reasoning_panel_container.set_active(busy)

    def _on_chat_link_clicked(self, url):
        link = url.toString()
        if link.startswith("branch:"):
            node_id = link.split(":", 1)[1]
            self._branch_from_node(node_id)

    def _branch_from_node(self, node_id):
        if not self.chat_history:
            return
        self.chat_history.set_current_node(node_id)
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
        self._save_current_session()

    def _populate_branches_tree(self):
        self._branches_tree.blockSignals(True)
        self._branches_tree.clear()
        if not self.chat_history:
            self._branches_tree.blockSignals(False)
            return

        root_node = self.chat_history.root
        self._tree_items_map = {}
        
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
        
        layout.addStretch()
        
        # Add a small collapse button
        self._collapse_strip_btn = QPushButton("▲ collapse")
        self._collapse_strip_btn.setObjectName("btn-ghost")
        self._collapse_strip_btn.setFixedWidth(80)
        self._collapse_strip_btn.setStyleSheet("font-size: 7.5pt; padding: 2px;")
        self._collapse_strip_btn.clicked.connect(self._toggle_expert_strip)
        layout.addWidget(self._collapse_strip_btn)
        
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
