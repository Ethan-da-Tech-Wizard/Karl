"""
Karl -- Main Window v6
======================
Two-page layout:
  Page 0 -- Chat    : sessions sidebar | reasoning panel | chat display | input
  Page 1 -- Config  : system prompt | theme | RAG | generation | loop controls

Nav bar at top always visible. Click Chat / Configure to switch pages.
"""

import time as _time
import io as _io
import contextlib as _cl

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTextBrowser, QLineEdit, QPushButton, QSplitter,
    QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
    QListWidget, QFileDialog, QMessageBox,
    QFrame, QStatusBar, QApplication, QSizePolicy,
    QDialog, QDialogButtonBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import save_example
from app.ui.themes import THEMES, generate_stylesheet


# ---------------------------------------------------------------------------
# Background threads
# ---------------------------------------------------------------------------

class UpgradeCheckThread(QThread):
    upgrade_available = pyqtSignal(dict, dict)
    no_upgrade        = pyqtSignal()

    def run(self):
        try:
            from app.engine.upgrade_manager import check_for_upgrade
            entry, profile = check_for_upgrade()
            if entry:
                self.upgrade_available.emit(entry, profile)
            else:
                self.no_upgrade.emit()
        except Exception:
            self.no_upgrade.emit()


# ---------------------------------------------------------------------------
# Tiny UI helpers
# ---------------------------------------------------------------------------

def _rule() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid #1E1E22; max-height: 1px;")
    return f


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #35353A; font-size: 7.5pt; font-weight: bold; "
        "letter-spacing: 0.14em; padding: 16px 0 5px 0; background: transparent;"
    )
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #28282D; font-size: 8.5pt; padding-bottom: 5px; background: transparent;")
    return lbl


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    DEFAULT_SYSTEM_PROMPT = (
        "You are Karl, a helpful and knowledgeable AI assistant. "
        "Answer the user's questions clearly, thoroughly, and directly. "
        "When you have access to document context, use it to ground your answer. "
        "Do not repeat yourself unnecessarily. "
        "If you are unsure, say so honestly."
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl")
        self.resize(1480, 920)
        self.setMinimumSize(1050, 680)

        # State
        self.chat_history:        list[dict] = []
        self.memory_manager     = MemoryManager()
        self.rag_pipeline       = RAGPipeline()
        self.current_session    = None
        self.agentic_thread     = None
        self._last_user_msg     = ""
        self._last_response     = ""
        self._last_chunks:      list = []
        self._gen_start         = 0.0
        self._current_theme     = "Midnight"
        self._thinking_visible  = True

        self._build_ui()
        self._build_statusbar()
        self._refresh_sessions()
        self._run_upgrade_check()
        self._apply_theme("Midnight")

    # ==========================================================================
    # Top-level layout
    # ==========================================================================

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vl = QVBoxLayout(root)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        vl.addWidget(self._build_navbar())
        vl.addWidget(_rule())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_chat_page())    # index 0
        self.stack.addWidget(self._build_config_page())  # index 1
        vl.addWidget(self.stack)

    # ==========================================================================
    # Nav bar
    # ==========================================================================

    def _build_navbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setObjectName("navbar")
        bar.setStyleSheet(
            "QWidget#navbar { background-color: #070709; border-bottom: 1px solid #141416; }"
        )
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(0)

        # App name
        logo = QLabel("KARL")
        logo.setStyleSheet(
            "color: #252528; font-size: 12pt; font-weight: bold; "
            "letter-spacing: 0.18em; background: transparent; padding-right: 28px;"
        )
        hl.addWidget(logo)

        # Nav buttons
        self._nav_chat   = self._nav_btn("Chat",      lambda: self._goto(0))
        self._nav_config = self._nav_btn("Configure", lambda: self._goto(1))
        hl.addWidget(self._nav_chat)
        hl.addWidget(self._nav_config)
        hl.addStretch()

        # Quick theme picker in nav bar
        theme_lbl = QLabel("Theme")
        theme_lbl.setStyleSheet("color: #28282D; font-size: 9pt; background: transparent; padding-right: 8px;")
        self.nav_theme = QComboBox()
        self.nav_theme.setFixedHeight(28)
        self.nav_theme.setFixedWidth(150)
        for name in sorted(THEMES.keys()):
            self.nav_theme.addItem(name)
        self.nav_theme.setCurrentText("Midnight")
        self.nav_theme.setToolTip("Switch color theme. 30 palettes available.")
        self.nav_theme.currentTextChanged.connect(self._apply_theme)
        hl.addWidget(theme_lbl)
        hl.addWidget(self.nav_theme)

        self._goto(0)
        return bar

    def _nav_btn(self, label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(50)
        btn.setFixedWidth(110)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "color: #303035; font-size: 10pt; font-weight: 500; }"
            "QPushButton:hover { color: #606065; }"
        )
        btn.clicked.connect(slot)
        return btn

    def _goto(self, index: int):
        self.stack.setCurrentIndex(index)
        active   = "color: #DDDDE0; border-bottom: 2px solid #DDDDE0;"
        inactive = "color: #303035; border-bottom: none;"
        base = (
            "QPushButton { background: transparent; font-size: 10pt; font-weight: 500; "
            "border: none; padding-bottom: 2px; }"
            "QPushButton:hover { color: #606065; }"
        )
        self._nav_chat.setStyleSheet(
            f"QPushButton {{ background: transparent; font-size: 10pt; font-weight: 500; "
            f"{'border-bottom: 2px solid #DDDDE0;' if index == 0 else 'border-bottom: none;'} "
            f"color: {'#DDDDE0' if index == 0 else '#303035'}; padding-bottom: 2px; }}"
            "QPushButton:hover { color: #DDDDE0; }"
        )
        self._nav_config.setStyleSheet(
            f"QPushButton {{ background: transparent; font-size: 10pt; font-weight: 500; "
            f"{'border-bottom: 2px solid #DDDDE0;' if index == 1 else 'border-bottom: none;'} "
            f"color: {'#DDDDE0' if index == 1 else '#303035'}; padding-bottom: 2px; }}"
            "QPushButton:hover { color: #DDDDE0; }"
        )

    # ==========================================================================
    # Page 0 -- Chat
    # ==========================================================================

    def _build_chat_page(self) -> QWidget:
        page = QWidget()
        hl = QHBoxLayout(page)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        hl.addWidget(splitter)

        splitter.addWidget(self._build_sessions_panel())
        splitter.addWidget(self._build_main_chat())
        splitter.setSizes([220, 1260])
        return page

    # ── Sessions sidebar ──────────────────────────────────────────────────────

    def _build_sessions_panel(self) -> QWidget:
        p = QWidget()
        p.setFixedWidth(220)
        p.setObjectName("sidebar")
        p.setStyleSheet("QWidget#sidebar { background-color: #07070A; border-right: 1px solid #141416; }")
        l = QVBoxLayout(p)
        l.setContentsMargins(14, 18, 14, 16)
        l.setSpacing(4)

        l.addWidget(_section("Sessions"))
        self.session_list = QListWidget()
        self.session_list.setToolTip("Saved conversations.\nDouble-click to restore.")
        self.session_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.session_list.itemDoubleClicked.connect(self._load_session)
        l.addWidget(self.session_list)

        row = QHBoxLayout()
        row.setSpacing(6)
        b_new = QPushButton("New")
        b_new.setToolTip("Start a fresh conversation.")
        b_new.clicked.connect(self._new_session)
        b_save = QPushButton("Save")
        b_save.setToolTip("Save the current conversation.")
        b_save.clicked.connect(self._save_session)
        row.addWidget(b_new)
        row.addWidget(b_save)
        l.addLayout(row)

        l.addSpacing(10)
        l.addWidget(_rule())
        l.addWidget(_section("Knowledge Base"))
        l.addWidget(_hint("Add files so Karl can reference them in answers."))

        self.kb_list = QListWidget()
        self.kb_list.setMaximumHeight(120)
        self.kb_list.setToolTip("Ingested documents.\nContent is injected automatically when relevant.")
        l.addWidget(self.kb_list)

        b_add = QPushButton("Add File")
        b_add.setToolTip("Ingest a file into the knowledge base.\nSupported: PDF, DOCX, TXT, PY, MD, CSV.")
        b_add.clicked.connect(self._ingest_doc)
        l.addWidget(b_add)

        return p

    # ── Main chat area ────────────────────────────────────────────────────────

    def _build_main_chat(self) -> QWidget:
        p = QWidget()
        vl = QVBoxLayout(p)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        vs = QSplitter(Qt.Orientation.Vertical)
        vs.setChildrenCollapsible(True)
        vl.addWidget(vs)

        vs.addWidget(self._build_reasoning_panel())
        vs.addWidget(self._build_response_panel())
        vs.setSizes([240, 640])
        return p

    def _build_reasoning_panel(self) -> QWidget:
        c = QWidget()
        c.setObjectName("reasoning_panel")
        c.setStyleSheet(
            "QWidget#reasoning_panel { background-color: #060910; border-bottom: 1px solid #0E1220; }"
        )
        vl = QVBoxLayout(c)
        vl.setContentsMargins(22, 12, 22, 10)
        vl.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("REASONING")
        lbl.setStyleSheet(
            "color: #182848; font-size: 7.5pt; font-weight: bold; "
            "letter-spacing: 0.14em; background: transparent;"
        )
        lbl.setToolTip(
            "Karl's internal chain of thought.\n"
            "Streams live while the model is thinking.\n"
            "Drag the divider or click Hide to collapse."
        )
        self.think_toggle = QPushButton("Hide")
        self.think_toggle.setFixedSize(52, 22)
        self.think_toggle.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #182848; "
            "border-radius: 3px; color: #182848; font-size: 8pt; }"
            "QPushButton:hover { color: #263e6e; border-color: #263e6e; }"
        )
        self.think_toggle.clicked.connect(self._toggle_thinking)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self.think_toggle)
        vl.addLayout(hdr)

        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #040710; color: #1a2f5a; "
            "font-family: 'Cascadia Code', Consolas, monospace; font-size: 9.5pt; "
            "border: 1px solid #0a1228; border-radius: 4px; padding: 10px 14px;"
        )
        vl.addWidget(self.thought_display)
        return c

    def _build_response_panel(self) -> QWidget:
        c = QWidget()
        vl = QVBoxLayout(c)
        vl.setContentsMargins(22, 14, 22, 16)
        vl.setSpacing(10)

        # Header row
        hdr = QHBoxLayout()
        resp_lbl = QLabel("RESPONSE")
        resp_lbl.setStyleSheet(
            "color: #35353A; font-size: 7.5pt; font-weight: bold; "
            "letter-spacing: 0.14em; background: transparent;"
        )
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setObjectName("btn_accept")
        self.accept_btn.setFixedHeight(28)
        self.accept_btn.setToolTip("Mark this response as good and save it as a training example.")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self._accept)

        self.correct_btn = QPushButton("Correct")
        self.correct_btn.setObjectName("btn_correct")
        self.correct_btn.setFixedHeight(28)
        self.correct_btn.setToolTip("Edit the response to save the ideal version for training.")
        self.correct_btn.setEnabled(False)
        self.correct_btn.clicked.connect(self._correct)

        hdr.addWidget(resp_lbl)
        hdr.addStretch()
        hdr.addWidget(self.accept_btn)
        hdr.addWidget(self.correct_btn)
        vl.addLayout(hdr)

        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet(
            "background-color: #0C0C0F; color: #DDDDE0; "
            "font-family: 'Segoe UI', sans-serif; font-size: 12pt; "
            "border: 1px solid #1A1A1E; border-radius: 4px; padding: 18px 22px;"
        )
        vl.addWidget(self.chat_display)

        # Input row
        inp = QHBoxLayout()
        inp.setSpacing(10)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ask Karl anything...")
        self.user_input.setMinimumHeight(44)
        self.user_input.setStyleSheet("QLineEdit { font-size: 12pt; padding: 10px 16px; }")
        self.user_input.returnPressed.connect(self._send)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("btn_generate")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setFixedWidth(90)
        self.send_btn.setToolTip("Send your message. (Enter also works.)")
        self.send_btn.clicked.connect(self._send)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("btn_stop")
        self.stop_btn.setFixedHeight(44)
        self.stop_btn.setFixedWidth(72)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Stop the current generation immediately.")
        self.stop_btn.clicked.connect(self._stop_gen)

        inp.addWidget(self.user_input)
        inp.addWidget(self.send_btn)
        inp.addWidget(self.stop_btn)
        vl.addLayout(inp)
        return c

    # ==========================================================================
    # Page 1 -- Configure
    # ==========================================================================

    def _build_config_page(self) -> QWidget:
        # Outer page
        page = QWidget()
        page.setObjectName("config_page")
        page.setStyleSheet("QWidget#config_page { background-color: #09090C; }")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("config_content")
        content.setStyleSheet("QWidget#config_content { background: transparent; }")
        scroll.setWidget(content)

        # Three-column grid
        hl = QHBoxLayout(content)
        hl.setContentsMargins(30, 22, 30, 30)
        hl.setSpacing(28)
        hl.setAlignment(Qt.AlignmentFlag.AlignTop)

        col1 = self._config_col()
        col2 = self._config_col()
        col3 = self._config_col()

        hl.addLayout(col1)
        hl.addLayout(col2)
        hl.addLayout(col3)

        # ── Column 1: Identity ──
        col1.addWidget(self._config_header("Identity"))
        col1.addWidget(_section("System Prompt"))
        col1.addWidget(_hint(
            "This is injected as the opening instruction on every generation. "
            "Keep it concise -- Karl's reasoning model handles the rest internally."
        ))
        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlainText(self.DEFAULT_SYSTEM_PROMPT)
        self.sys_prompt_input.setMinimumHeight(200)
        self.sys_prompt_input.setToolTip(
            "Defines Karl's persona and behavior.\n"
            "Changes take effect on the next message sent."
        )
        col1.addWidget(self.sys_prompt_input)

        col1.addWidget(_section("Appearance"))
        col1.addWidget(_hint("30 color palettes. Change takes effect instantly."))
        self.config_theme = QComboBox()
        for name in sorted(THEMES.keys()):
            self.config_theme.addItem(name)
        self.config_theme.setCurrentText("Midnight")
        self.config_theme.setToolTip("Select a color theme.")
        self.config_theme.currentTextChanged.connect(self._apply_theme_and_sync)
        col1.addWidget(self.config_theme)
        col1.addStretch()

        # ── Column 2: Retrieval + Generation ──
        col2.addWidget(self._config_header("Retrieval & Generation"))
        col2.addWidget(_section("Context Retrieval (RAG)"))
        col2.addWidget(_hint(
            "When a file is ingested via the Chat page, Karl retrieves the most "
            "relevant chunks and includes them with each message. "
            "Set Chunks to 0 to disable."
        ))

        rag_row = QHBoxLayout()
        rag_lbl = QLabel("Chunks (top-k)")
        rag_lbl.setStyleSheet("color: #505058; font-size: 10pt; background: transparent;")
        self.rag_spin = QSpinBox()
        self.rag_spin.setRange(0, 10)
        self.rag_spin.setValue(3)
        self.rag_spin.setFixedWidth(70)
        self.rag_spin.setToolTip(
            "How many document chunks are retrieved per message.\n"
            "0 = retrieval disabled.\n"
            "3-5 is a good balance for most documents."
        )
        rag_row.addWidget(rag_lbl)
        rag_row.addStretch()
        rag_row.addWidget(self.rag_spin)
        col2.addLayout(rag_row)

        col2.addSpacing(16)
        col2.addWidget(_section("Generation"))
        col2.addWidget(_hint(
            "Controls how Karl samples text. "
            "Lower temperature = more predictable. "
            "Top-P limits the token pool. "
            "Max Tokens caps the response length -- Karl auto-continues if truncated."
        ))

        for label, attr, lo, hi, step, val, tip in [
            ("Temperature",  "temp_spin",   0.0, 2.0, 0.05, 0.7,
             "0.0 = deterministic.\n0.7 = balanced.\n1.2+ = creative and varied."),
            ("Top-P",        "top_p_spin",  0.0, 1.0, 0.05, 0.95,
             "Nucleus sampling threshold.\n0.95 is recommended for most tasks."),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #505058; font-size: 10pt; background: transparent;")
            lbl.setToolTip(tip)
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(step)
            spin.setValue(val)
            spin.setFixedWidth(85)
            spin.setToolTip(tip)
            setattr(self, attr, spin)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(spin)
            col2.addLayout(row)

        tok_row = QHBoxLayout()
        tok_lbl = QLabel("Max Tokens")
        tok_lbl.setStyleSheet("color: #505058; font-size: 10pt; background: transparent;")
        tok_lbl.setToolTip(
            "Maximum number of tokens per generation pass.\n"
            "2048 is recommended. Karl will chain continuations automatically."
        )
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(128, 4096)
        self.tokens_spin.setValue(2048)
        self.tokens_spin.setFixedWidth(85)
        self.tokens_spin.setToolTip(tok_lbl.toolTip())
        tok_row.addWidget(tok_lbl)
        tok_row.addStretch()
        tok_row.addWidget(self.tokens_spin)
        col2.addLayout(tok_row)
        col2.addStretch()

        # ── Column 3: Autonomous Loop ──
        col3.addWidget(self._config_header("Autonomous Loop"))
        col3.addWidget(_section("Self-Iteration"))
        col3.addWidget(_hint(
            "The loop lets Karl generate a response, reflect on it, and refine it "
            "across multiple passes -- up to 20 iterations -- or until it writes "
            "'FINAL ANSWER:'. Send a message first on the Chat page to seed the loop."
        ))

        self.loop_btn = QPushButton("Run Loop")
        self.loop_btn.setObjectName("btn_agentic")
        self.loop_btn.setFixedHeight(38)
        self.loop_btn.setToolTip(
            "Starts the autonomous self-iteration loop.\n"
            "Karl refines its answer up to 20 times.\n\n"
            "Edit core/agentic_loop.py to customize stop conditions."
        )
        self.loop_btn.clicked.connect(self._start_loop)
        col3.addWidget(self.loop_btn)

        self.stop_loop_btn = QPushButton("Stop Loop")
        self.stop_loop_btn.setObjectName("btn_stop")
        self.stop_loop_btn.setFixedHeight(38)
        self.stop_loop_btn.setEnabled(False)
        self.stop_loop_btn.setToolTip("Halt the loop after the current iteration completes.")
        self.stop_loop_btn.clicked.connect(self._stop_loop)
        col3.addWidget(self.stop_loop_btn)

        self.loop_status = QLabel("Idle")
        self.loop_status.setStyleSheet("color: #28282D; font-size: 10pt; padding-top: 6px; background: transparent;")
        col3.addWidget(self.loop_status)

        col3.addSpacing(20)
        col3.addWidget(_rule())
        col3.addWidget(_section("Model Upgrade"))
        col3.addWidget(_hint("Karl checks at startup whether a better model is available for your hardware."))

        self.upgrade_lbl = QLabel("")
        self.upgrade_lbl.setWordWrap(True)
        self.upgrade_lbl.setStyleSheet("color: #93C5FD; font-size: 9pt; background: transparent;")
        self.upgrade_lbl.setVisible(False)
        col3.addWidget(self.upgrade_lbl)

        self.upgrade_btn = QPushButton("Upgrade Model")
        self.upgrade_btn.setVisible(False)
        self.upgrade_btn.clicked.connect(self._confirm_upgrade)
        col3.addWidget(self.upgrade_btn)

        col3.addStretch()
        return page

    def _config_col(self) -> QVBoxLayout:
        l = QVBoxLayout()
        l.setSpacing(4)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)
        return l

    def _config_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #505058; font-size: 13pt; font-weight: bold; "
            "padding-bottom: 6px; background: transparent;"
        )
        return lbl

    # ==========================================================================
    # Status bar
    # ==========================================================================

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #303035; font-size: 9pt;")
        sb.addWidget(self._status_lbl)
        self._latency_lbl = QLabel("")
        self._latency_lbl.setStyleSheet("color: #222226; font-size: 9pt;")
        sb.addPermanentWidget(self._latency_lbl)

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    # ==========================================================================
    # Theme
    # ==========================================================================

    def _apply_theme(self, name: str):
        self._current_theme = name
        QApplication.instance().setStyleSheet(generate_stylesheet(name))

    def _apply_theme_and_sync(self, name: str):
        """Config page theme picker -- also syncs nav bar picker."""
        self._apply_theme(name)
        if self.nav_theme.currentText() != name:
            self.nav_theme.blockSignals(True)
            self.nav_theme.setCurrentText(name)
            self.nav_theme.blockSignals(False)

    # ==========================================================================
    # Reasoning panel toggle
    # ==========================================================================

    def _toggle_thinking(self):
        self._thinking_visible = not self._thinking_visible
        self.thought_display.setVisible(self._thinking_visible)
        self.think_toggle.setText("Hide" if self._thinking_visible else "Show")

    # ==========================================================================
    # Session management
    # ==========================================================================

    def _refresh_sessions(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def _new_session(self):
        self.chat_history     = []
        self.current_session  = None
        self.chat_display.clear()
        self.thought_display.clear()
        self._set_status("New session")

    def _save_session(self):
        if not self.chat_history:
            return
        self.current_session = self.memory_manager.save_session(
            self.chat_history,
            self.sys_prompt_input.toPlainText(),
            self.current_session
        )
        self._refresh_sessions()
        self._set_status(f"Saved: {self.current_session}")

    def _load_session(self, item):
        sys_prompt, history = self.memory_manager.load_session(item.text())
        self.sys_prompt_input.setPlainText(sys_prompt)
        self.chat_history    = history
        self.current_session = item.text()
        self.chat_display.clear()
        self.thought_display.clear()
        for msg in history:
            role, content = msg.get("role"), msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>You:</b>  {content}\n")
            elif role == "assistant":
                clean = content.split("</think>", 1)[1].strip() if "</think>" in content else content
                self.chat_display.append(f"<b>Karl:</b>  {clean}\n")
        self._set_status(f"Loaded: {item.text()}")

    # ==========================================================================
    # Knowledge Base
    # ==========================================================================

    def _ingest_doc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select file to ingest", "",
            "Supported (*.pdf *.docx *.txt *.py *.md *.csv);;All (*.*)"
        )
        if not path:
            return
        self._set_status("Ingesting...")
        chunks = self.rag_pipeline.ingest_file(path)
        name   = path.replace("\\", "/").split("/")[-1]
        if chunks > 0:
            self.kb_list.addItem(f"{name}  ({chunks})")
            self._set_status(f"Ingested {name} -- {chunks} chunks")
        else:
            self._set_status(f"Ingest failed: {name}")

    # ==========================================================================
    # Controls
    # ==========================================================================

    def _set_controls(self, enabled: bool):
        self.user_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.loop_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)

    def _hyperparams(self) -> dict:
        return {
            "temperature": self.temp_spin.value(),
            "top_p":       self.top_p_spin.value(),
            "max_tokens":  self.tokens_spin.value(),
        }

    # ==========================================================================
    # Generation
    # ==========================================================================

    def _send(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._last_user_msg  = text
        self.accept_btn.setEnabled(False)
        self.correct_btn.setEnabled(False)
        self.accept_btn.setText("Accept")
        self.correct_btn.setText("Correct")
        self._set_controls(False)

        self.chat_display.append(f"<b>You:</b>  {text}\n")
        self.chat_display.append("<b>Karl:</b>  ")
        self.thought_display.append(f"\n--- {text[:60]} ---\n")

        self.chat_history.append({"role": "user", "content": text})

        # Retrieve context
        top_k     = self.rag_spin.value()
        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        self._last_chunks = retrieved

        # Build system prompt + optional RAG injection
        sys_prompt = self.sys_prompt_input.toPlainText().strip() or self.DEFAULT_SYSTEM_PROMPT
        if retrieved:
            sys_prompt += (
                "\n\n---\nRELEVANT CONTEXT FROM KNOWLEDGE BASE:\n"
                + "\n\n".join(retrieved)
                + "\n---"
            )

        self._gen_start = _time.time()
        self._set_status("Thinking...")

        self.thread = LLMThread(sys_prompt, self.chat_history, self._hyperparams(), retrieved)
        self.thread.new_thought_token.connect(self._on_thought)
        self.thread.new_chat_token.connect(self._on_chat)
        self.thread.new_raw_token.connect(lambda _: None)
        self.thread.generation_finished.connect(self._on_done)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _stop_gen(self):
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.terminate()
        self._set_controls(True)
        self._set_status("Stopped")

    def _on_thought(self, token: str):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.thought_display.setTextCursor(c)
        self.thought_display.ensureCursorVisible()

    def _on_chat(self, token: str):
        c = self.chat_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.chat_display.setTextCursor(c)
        self.chat_display.ensureCursorVisible()

    def _on_done(self, thought, response, truncated=False, ended_in_thought=False):
        self.chat_history.append({"role": "assistant", "content": response})
        self._last_response = response

        self.chat_display.append("\n")
        self.accept_btn.setEnabled(True)
        self.correct_btn.setEnabled(True)

        latency  = _time.time() - self._gen_start
        rag_note = f"  |  {len(self._last_chunks)} chunk(s)" if self._last_chunks else ""
        self._set_status(f"Done -- {latency:.1f}s{rag_note}")
        self._latency_lbl.setText(f"Last: {latency:.1f}s")

        self._set_controls(True)
        self.stop_btn.setEnabled(False)
        self.user_input.setFocus()

    def _on_error(self, msg: str):
        self.chat_display.append(f"\n<font color='#EF4444'><b>Error:</b> {msg}</font>\n")
        self._set_controls(True)
        self.stop_btn.setEnabled(False)
        self.loop_status.setText("Error")
        self._set_status(f"Error: {msg[:80]}")

    # ==========================================================================
    # Agentic Loop
    # ==========================================================================

    def _start_loop(self):
        if not self.chat_history:
            QMessageBox.information(
                self, "No seed",
                "Go to the Chat page and send a message first to seed the loop."
            )
            return
        self._set_controls(False)
        self.stop_loop_btn.setEnabled(True)
        self.loop_status.setText("Running")
        self.loop_status.setStyleSheet(
            "color: #22C55E; font-size: 10pt; padding-top: 6px; background: transparent;"
        )
        self.thought_display.append("\n" + "=" * 50 + "\nAUTONOMOUS LOOP STARTED\n" + "=" * 50)
        self._set_status("Loop running...")

        sys_prompt = self.sys_prompt_input.toPlainText().strip() or self.DEFAULT_SYSTEM_PROMPT
        self.agentic_thread = AgenticThread(sys_prompt, self.chat_history, self._hyperparams())
        self.agentic_thread.new_thought_token.connect(self._on_thought)
        self.agentic_thread.new_chat_token.connect(self._on_chat)
        self.agentic_thread.new_raw_token.connect(lambda _: None)
        self.agentic_thread.iteration_finished.connect(
            lambda i, t, r: self.chat_history.append({"role": "assistant", "content": r})
        )
        self.agentic_thread.loop_finished.connect(self._on_loop_done)
        self.agentic_thread.error_occurred.connect(self._on_error)
        self.agentic_thread.start()

    def _stop_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText("Stopping...")
        self.loop_status.setStyleSheet(
            "color: #F59E0B; font-size: 10pt; padding-top: 6px; background: transparent;"
        )

    def _on_loop_done(self, total: int):
        self._set_controls(True)
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText(f"Done ({total} iterations)")
        self.loop_status.setStyleSheet(
            "color: #28282D; font-size: 10pt; padding-top: 6px; background: transparent;"
        )
        self.chat_display.append(
            f"\n<i><font color='#22C55E'>Loop finished -- {total} iteration(s).</font></i>\n"
        )
        self.user_input.setFocus()
        self._set_status(f"Loop done -- {total} iteration(s)")

    # ==========================================================================
    # Training Curator
    # ==========================================================================

    def _accept(self):
        if not self._last_user_msg or not self._last_response:
            return
        save_example(
            system_prompt=self.sys_prompt_input.toPlainText(),
            user_msg=self._last_user_msg,
            good_response=self._last_response,
            source="thumbs_up"
        )
        self.accept_btn.setEnabled(False)
        self.correct_btn.setEnabled(False)
        self.accept_btn.setText("Saved")
        self._set_status("Training example saved")

    def _correct(self):
        if not self._last_user_msg:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Correct this response")
        dlg.resize(660, 340)
        dl = QVBoxLayout(dlg)
        dl.setContentsMargins(22, 22, 22, 16)
        dl.setSpacing(10)
        dl.addWidget(QLabel(f"<b>Prompt:</b> {self._last_user_msg[:120]}"))
        dl.addWidget(QLabel("<b>Ideal response:</b>"))
        editor = QTextEdit()
        editor.setPlainText(self._last_response)
        dl.addWidget(editor)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dl.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            corrected = editor.toPlainText().strip()
            if corrected:
                save_example(
                    system_prompt=self.sys_prompt_input.toPlainText(),
                    user_msg=self._last_user_msg,
                    good_response=corrected,
                    source="corrected"
                )
                self.correct_btn.setText("Saved")
                self.accept_btn.setEnabled(False)
                self.correct_btn.setEnabled(False)

    # ==========================================================================
    # Upgrade
    # ==========================================================================

    def _run_upgrade_check(self):
        self._upg_thread = UpgradeCheckThread()
        self._upg_thread.upgrade_available.connect(self._on_upgrade_avail)
        self._upg_thread.no_upgrade.connect(lambda: self._set_status("Ready"))
        self._upg_thread.start()

    def _on_upgrade_avail(self, entry, profile):
        self._pending_entry = entry
        self.upgrade_lbl.setText(
            f"Upgrade available: {entry['name']}\nRAM required: {profile['ram_gb']} GB"
        )
        self.upgrade_lbl.setVisible(True)
        self.upgrade_btn.setVisible(True)

    def _confirm_upgrade(self):
        reply = QMessageBox.question(
            self, "Upgrade Karl",
            f"Download {self._pending_entry['name']}?\nThis will replace the current model.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.upgrade_btn.setEnabled(False)
            from app.engine.upgrade_manager import perform_upgrade
            try:
                perform_upgrade(self._pending_entry)
                self.upgrade_lbl.setText("Upgraded. Restart Karl to load the new model.")
                self.upgrade_btn.setVisible(False)
            except Exception as e:
                self.upgrade_lbl.setText(f"Upgrade failed: {e}")
                self.upgrade_btn.setEnabled(True)
