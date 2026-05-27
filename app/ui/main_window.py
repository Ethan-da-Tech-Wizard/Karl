"""
Karl -- Main Window v6
======================
Two-page layout:
  Page 0 -- Chat    : sessions sidebar | reasoning panel | chat display | input
  Page 1 -- Config  : system prompt | theme | RAG | generation | loop controls

Nav bar at top always visible. Click Chat / Configure to switch pages.
"""

import time as _time
import os
import json

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTextBrowser, QLineEdit, QPushButton, QSplitter,
    QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
    QListWidget, QFileDialog, QMessageBox,
    QFrame, QStatusBar, QApplication, QSizePolicy,
    QDialog, QDialogButtonBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

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
    return f


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("lbl_section")
    lbl.setStyleSheet(
        "font-size: 7.5pt; font-weight: bold; "
        "letter-spacing: 0.14em; padding: 16px 0 5px 0; background: transparent;"
    )
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setObjectName("lbl_hint")
    lbl.setStyleSheet("font-size: 8.5pt; padding-bottom: 5px; background: transparent;")
    return lbl


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    DEFAULT_SYSTEM_PROMPT = (
        "You are Karl, a helpful and knowledgeable AI assistant. "
        "Answer the user's questions clearly, thoroughly, and directly in English. "
        "Your final response (everything outside the <think></think> tags) MUST be in English. "
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
        self._current_theme     = self._load_saved_theme()
        self._thinking_visible  = True

        self._build_ui()
        self._build_statusbar()
        self._refresh_sessions()
        self._run_upgrade_check()
        self._apply_theme(self._current_theme)

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
        self.stack.addWidget(self._build_tuning_page())  # index 2
        vl.addWidget(self.stack)

        self._goto(0)

    # ==========================================================================
    # Nav bar
    # ==========================================================================

    def _build_navbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(60)
        bar.setObjectName("navbar")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(0)

        # App name
        logo = QLabel("karl")
        logo.setStyleSheet(
            "font-size: 13pt; font-weight: 800; "
            "letter-spacing: 0.2em; background: transparent; padding-right: 28px;"
        )
        hl.addWidget(logo)

        # Nav buttons
        self._nav_chat   = self._nav_btn("chat",      lambda: self._goto(0))
        self._nav_config = self._nav_btn("configure", lambda: self._goto(1))
        self._nav_tuning = self._nav_btn("tuning",    lambda: self._goto(2))
        hl.addWidget(self._nav_chat)
        hl.addWidget(self._nav_config)
        hl.addWidget(self._nav_tuning)
        hl.addStretch()

        # Quick theme picker in nav bar
        theme_lbl = QLabel("theme")
        theme_lbl.setStyleSheet("font-size: 9pt; background: transparent; padding-right: 8px;")
        self.nav_theme = QComboBox()
        self.nav_theme.setFixedHeight(32)
        self.nav_theme.setFixedWidth(150)
        for name in sorted(THEMES.keys()):
            self.nav_theme.addItem(name)
        self.nav_theme.setCurrentText(self._current_theme)
        self.nav_theme.setToolTip("Switch color theme. 30 palettes available.")
        self.nav_theme.currentTextChanged.connect(self._apply_theme_from_navbar)
        hl.addWidget(theme_lbl)
        hl.addWidget(self.nav_theme)

        # Set default active state on startup
        self._nav_chat.setProperty("active", "true")
        self._nav_config.setProperty("active", "false")
        self._nav_tuning.setProperty("active", "false")

        return bar

    def _nav_btn(self, label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("btn_nav")
        btn.setFixedHeight(60)
        btn.setFixedWidth(140)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    def _goto(self, index: int):
        self.stack.setCurrentIndex(index)
        self._nav_chat.setProperty("active", "true" if index == 0 else "false")
        self._nav_config.setProperty("active", "true" if index == 1 else "false")
        self._nav_tuning.setProperty("active", "true" if index == 2 else "false")
        # Force stylesheet refresh
        for btn in [self._nav_chat, self._nav_config, self._nav_tuning]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

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
        p.setFixedWidth(260)
        p.setObjectName("sidebar")
        l = QVBoxLayout(p)  # noqa: E741
        l.setContentsMargins(24, 24, 24, 24)
        l.setSpacing(12)

        l.addWidget(_section("sessions"))
        self.session_list = QListWidget()
        self.session_list.setToolTip("Saved conversations.\nDouble-click to restore.")
        self.session_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.session_list.itemDoubleClicked.connect(self._load_session)
        l.addWidget(self.session_list)

        row = QHBoxLayout()
        row.setSpacing(8)
        b_new = QPushButton("new thread")
        b_new.setToolTip("Start a fresh conversation.")
        b_new.clicked.connect(self._new_session)
        b_save = QPushButton("save session")
        b_save.setToolTip("Save the current conversation.")
        b_save.clicked.connect(self._save_session)
        row.addWidget(b_new)
        row.addWidget(b_save)
        l.addLayout(row)

        l.addSpacing(12)
        l.addWidget(_rule())
        l.addWidget(_section("knowledge base"))
        l.addWidget(_hint("Add files so Karl can reference them in answers."))

        self.kb_list = QListWidget()
        self.kb_list.setMaximumHeight(150)
        self.kb_list.setToolTip("Ingested documents.\nContent is injected automatically when relevant.")
        l.addWidget(self.kb_list)

        b_add = QPushButton("ingest context")
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
        vs.setSizes([200, 680])
        return p

    def _build_reasoning_panel(self) -> QWidget:
        c = QWidget()
        c.setObjectName("reasoning_panel")
        vl = QVBoxLayout(c)
        vl.setContentsMargins(28, 20, 28, 16)
        vl.setSpacing(12)

        hdr = QHBoxLayout()
        lbl = QLabel("reasoning")
        lbl.setObjectName("lbl_section")
        lbl.setStyleSheet(
            "font-size: 8pt; font-weight: bold; "
            "letter-spacing: 0.14em; background: transparent;"
        )
        lbl.setToolTip(
            "Karl's internal chain of thought.\n"
            "Streams live while the model is thinking.\n"
            "Drag the divider or click hide to collapse."
        )
        self.think_toggle = QPushButton("hide")
        self.think_toggle.setObjectName("btn_think_toggle")
        self.think_toggle.setFixedSize(52, 22)
        self.think_toggle.clicked.connect(self._toggle_thinking)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self.think_toggle)
        vl.addLayout(hdr)

        self.thought_display = QTextBrowser()
        self.thought_display.setObjectName("thought_display")
        self.thought_display.document().setDefaultStyleSheet(
            "p, div, span { line-height: 160%; margin-bottom: 8px; }"
        )
        vl.addWidget(self.thought_display)
        return c

    def _build_response_panel(self) -> QWidget:
        c = QWidget()
        vl = QVBoxLayout(c)
        vl.setContentsMargins(28, 20, 28, 24)
        vl.setSpacing(16)

        # Header row
        hdr = QHBoxLayout()
        resp_lbl = QLabel("response")
        resp_lbl.setObjectName("lbl_section")
        resp_lbl.setStyleSheet(
            "font-size: 8pt; font-weight: bold; "
            "letter-spacing: 0.14em; background: transparent;"
        )
        self.accept_btn = QPushButton("approve")
        self.accept_btn.setObjectName("btn_accept")
        self.accept_btn.setFixedHeight(32)
        self.accept_btn.setToolTip("Mark this response as good and save it as a training example.")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self._accept)

        self.correct_btn = QPushButton("teach")
        self.correct_btn.setObjectName("btn_correct")
        self.correct_btn.setFixedHeight(32)
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
        self.chat_display.document().setDefaultStyleSheet(
            "p, div, span { line-height: 160%; margin-bottom: 10px; }"
        )
        vl.addWidget(self.chat_display)

        # Input row
        inp = QHBoxLayout()
        inp.setContentsMargins(0, 8, 0, 8)
        inp.setSpacing(0)

        self.input_container = QWidget()
        self.input_container.setObjectName("input_container")
        self.input_container.setFixedHeight(54)

        container_layout = QHBoxLayout(self.input_container)
        container_layout.setContentsMargins(18, 4, 10, 4)
        container_layout.setSpacing(10)

        self.user_input = QLineEdit()
        self.user_input.setObjectName("user_input")
        self.user_input.setPlaceholderText("Ask Karl anything...")
        self.user_input.returnPressed.connect(self._send)

        self.stop_btn = QPushButton("■")
        self.stop_btn.setObjectName("btn_stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Stop the current generation immediately.")
        self.stop_btn.clicked.connect(self._stop_gen)

        self.send_btn = QPushButton("✦")
        self.send_btn.setObjectName("btn_generate")
        self.send_btn.setToolTip("Send your message. (Enter also works.)")
        self.send_btn.clicked.connect(self._send)

        container_layout.addWidget(self.user_input)
        container_layout.addWidget(self.stop_btn)
        container_layout.addWidget(self.send_btn)

        inp.addWidget(self.input_container)
        vl.addLayout(inp)
        return c

    # ==========================================================================
    # Page 1 -- Configure
    # ==========================================================================

    def _build_config_page(self) -> QWidget:
        # Outer page
        page = QWidget()
        page.setObjectName("config_page")
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

        # Three-column grid containing cards
        hl = QHBoxLayout(content)
        hl.setContentsMargins(32, 32, 32, 32)
        hl.setSpacing(28)
        hl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Card 1: Identity Settings & Steering
        card1 = QFrame()
        card1.setObjectName("config_card")
        card1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col1 = QVBoxLayout(card1)
        col1.setContentsMargins(24, 24, 24, 24)
        col1.setSpacing(16)
        col1.setAlignment(Qt.AlignmentFlag.AlignTop)

        col1.addWidget(self._config_header("identity & steering"))
        
        col1.addWidget(_section("workflow mode"))
        col1.addWidget(_hint(
            "Select a preconfigured workflow template. This sets the default "
            "system prompt, retrieval strategy, and evaluation behavior. "
            "Select 'custom prompt' to write your own."
        ))
        self.workflow_combo = QComboBox()
        self.workflow_combo.addItem("custom prompt", None)
        from core.workflows import list_workflows
        for name, label in list_workflows():
            self.workflow_combo.addItem(label, name)
        self.workflow_combo.setToolTip("Choose a workflow to steer the model's behavior.")
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        col1.addWidget(self.workflow_combo)

        col1.addWidget(_section("system prompt"))
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
        self.sys_prompt_input.textChanged.connect(self._on_sys_prompt_edited)
        col1.addWidget(self.sys_prompt_input)

        col1.addWidget(_section("appearance"))
        col1.addWidget(_hint("30 color palettes. Change takes effect instantly."))
        self.config_theme = QComboBox()
        for name in sorted(THEMES.keys()):
            self.config_theme.addItem(name)
        self.config_theme.setCurrentText(self._current_theme)
        self.config_theme.setToolTip("Select a color theme.")
        self.config_theme.currentTextChanged.connect(self._apply_theme_from_config)
        col1.addWidget(self.config_theme)

        # Card 2: Retrieval & Generation Settings
        card2 = QFrame()
        card2.setObjectName("config_card")
        card2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col2 = QVBoxLayout(card2)
        col2.setContentsMargins(24, 24, 24, 24)
        col2.setSpacing(16)
        col2.setAlignment(Qt.AlignmentFlag.AlignTop)

        col2.addWidget(self._config_header("retrieval & generation"))
        col2.addWidget(_section("context retrieval"))
        col2.addWidget(_hint(
            "When a file is ingested via the Chat page, Karl retrieves the most "
            "relevant chunks and includes them with each message. "
            "Set Chunks to 0 to disable."
        ))

        rag_row = QHBoxLayout()
        rag_lbl = QLabel("chunks (top-k)")
        rag_lbl.setObjectName("control_label")
        rag_lbl.setStyleSheet("font-size: 10pt; background: transparent;")
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

        col2.addWidget(_section("generation"))
        col2.addWidget(_hint(
            "Controls how Karl samples text. "
            "Lower temperature = more predictable. "
            "Top-P limits the token pool. "
            "Max Tokens caps the response length -- Karl auto-continues if truncated."
        ))

        for label_text, attr, lo, hi, step, val, tip in [
            ("temperature",  "temp_spin",   0.0, 2.0, 0.05, 0.6,
             "0.0 = deterministic.\n0.6 = recommended / balanced.\n1.2+ = creative and varied."),
            ("top-p",        "top_p_spin",  0.0, 1.0, 0.05, 0.95,
             "Nucleus sampling threshold.\n0.95 is recommended for most tasks."),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setObjectName("control_label")
            lbl.setStyleSheet("font-size: 10pt; background: transparent;")
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
        tok_lbl = QLabel("max tokens")
        tok_lbl.setObjectName("control_label")
        tok_lbl.setStyleSheet("font-size: 10pt; background: transparent;")
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

        # Card 3: Autonomous Loop Settings
        card3 = QFrame()
        card3.setObjectName("config_card")
        card3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col3 = QVBoxLayout(card3)
        col3.setContentsMargins(24, 24, 24, 24)
        col3.setSpacing(16)
        col3.setAlignment(Qt.AlignmentFlag.AlignTop)

        col3.addWidget(self._config_header("autonomous loop"))
        col3.addWidget(_section("self-iteration"))
        col3.addWidget(_hint(
            "The loop lets Karl generate a response, reflect on it, and refine it "
            "across multiple passes -- up to 20 iterations -- or until it writes "
            "'FINAL ANSWER:'. Send a message first on the Chat page to seed the loop."
        ))

        self.loop_btn = QPushButton("reflect")
        self.loop_btn.setObjectName("btn_agentic")
        self.loop_btn.setFixedHeight(38)
        self.loop_btn.setToolTip(
            "Starts the autonomous self-iteration loop.\n"
            "Karl refines its answer up to 20 times.\n\n"
            "Edit core/agentic_loop.py to customize stop conditions."
        )
        self.loop_btn.clicked.connect(self._start_loop)
        col3.addWidget(self.loop_btn)

        self.stop_loop_btn = QPushButton("halt loop")
        self.stop_loop_btn.setObjectName("btn_stop")
        self.stop_loop_btn.setFixedHeight(38)
        self.stop_loop_btn.setEnabled(False)
        self.stop_loop_btn.setToolTip("Halt the loop after the current iteration completes.")
        self.stop_loop_btn.clicked.connect(self._stop_loop)
        col3.addWidget(self.stop_loop_btn)

        self.loop_status = QLabel("Idle")
        self.loop_status.setObjectName("status_label")
        self.loop_status.setStyleSheet("font-size: 10pt; padding-top: 6px; background: transparent;")
        col3.addWidget(self.loop_status)

        col3.addSpacing(12)
        col3.addWidget(_rule())
        col3.addWidget(_section("model upgrade"))
        col3.addWidget(_hint("Karl checks at startup whether a better model is available for your hardware."))

        self.upgrade_lbl = QLabel("")
        self.upgrade_lbl.setWordWrap(True)
        self.upgrade_lbl.setObjectName("upgrade_label")
        self.upgrade_lbl.setStyleSheet("font-size: 9pt; background: transparent;")
        self.upgrade_lbl.setVisible(False)
        col3.addWidget(self.upgrade_lbl)

        self.upgrade_btn = QPushButton("upgrade model")
        self.upgrade_btn.setVisible(False)
        self.upgrade_btn.clicked.connect(self._confirm_upgrade)
        col3.addWidget(self.upgrade_btn)

        hl.addWidget(card1)
        hl.addWidget(card2)
        hl.addWidget(card3)

        return page

    def _build_tuning_page(self) -> QWidget:
        # Outer page
        page = QWidget()
        page.setObjectName("config_page")
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

        # Two-column layout for tuning guide
        hl = QHBoxLayout(content)
        hl.setContentsMargins(32, 32, 32, 32)
        hl.setSpacing(28)
        hl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Card 1: Data Curation & Validation
        card1 = QFrame()
        card1.setObjectName("config_card")
        card1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col1 = QVBoxLayout(card1)
        col1.setContentsMargins(28, 28, 28, 28)
        col1.setSpacing(16)
        col1.setAlignment(Qt.AlignmentFlag.AlignTop)

        col1.addWidget(self._config_header("data curation & validation"))

        # Live stats bar
        self.dataset_stats_lbl = QLabel("dataset: 0 examples")
        self.dataset_stats_lbl.setObjectName("lbl_hint")
        self.dataset_stats_lbl.setStyleSheet("font-size: 9.5pt; padding-bottom: 4px; background: transparent;")
        col1.addWidget(self.dataset_stats_lbl)

        # Export button
        export_btn = QPushButton("export dataset (ShareGPT)")
        export_btn.setToolTip(
            "Export all curated examples to data/training/export_unsloth.jsonl\n"
            "Ready-to-use with Unsloth / TRL fine-tuning libraries."
        )
        export_btn.setFixedHeight(34)
        export_btn.clicked.connect(self._export_dataset)
        col1.addWidget(export_btn)

        self.tuning_doc1 = QTextBrowser()
        self.tuning_doc1.setFrameShape(QFrame.Shape.NoFrame)
        self.tuning_doc1.setStyleSheet("QTextBrowser { background: transparent; border: none; padding: 0; }")
        self.tuning_doc1.setOpenExternalLinks(True)
        col1.addWidget(self.tuning_doc1)

        # Card 2: QLoRA Fine-Tuning & Export
        card2 = QFrame()
        card2.setObjectName("config_card")
        card2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col2 = QVBoxLayout(card2)
        col2.setContentsMargins(28, 28, 28, 28)
        col2.setSpacing(16)
        col2.setAlignment(Qt.AlignmentFlag.AlignTop)

        col2.addWidget(self._config_header("qlora tuning & conversion"))
        
        self.tuning_doc2 = QTextBrowser()
        self.tuning_doc2.setFrameShape(QFrame.Shape.NoFrame)
        self.tuning_doc2.setStyleSheet("QTextBrowser { background: transparent; border: none; padding: 0; }")
        self.tuning_doc2.setOpenExternalLinks(True)
        col2.addWidget(self.tuning_doc2)

        # Card 3: Hackable Extension Points
        card3 = QFrame()
        card3.setObjectName("config_card")
        card3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col3 = QVBoxLayout(card3)
        col3.setContentsMargins(28, 28, 28, 28)
        col3.setSpacing(16)
        col3.setAlignment(Qt.AlignmentFlag.AlignTop)

        col3.addWidget(self._config_header("hackable python loops"))
        
        self.tuning_doc3 = QTextBrowser()
        self.tuning_doc3.setFrameShape(QFrame.Shape.NoFrame)
        self.tuning_doc3.setStyleSheet("QTextBrowser { background: transparent; border: none; padding: 0; }")
        self.tuning_doc3.setOpenExternalLinks(True)
        col3.addWidget(self.tuning_doc3)

        hl.addWidget(card1)
        hl.addWidget(card2)
        hl.addWidget(card3)

        # Populate HTML and stats initially
        self._update_tuning_docs()
        self._refresh_dataset_stats()

        return page

    def _update_tuning_docs(self):
        c = self._chat_colors()
        html1 = f"""
        <div style="line-height: 160%; font-size: 10.5pt; color: {c['text']};">
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">1. Local SFT Curator</b><br>
            Karl gathers Supervised Fine-Tuning (SFT) training data locally as you chat:</p>
            <ul style="margin-left: 16px; margin-bottom: 16px;">
                <li style="margin-bottom: 6px;"><b>approve:</b> Saves the current user prompt and Karl's response to <code>data/training/curated.jsonl</code> as an approved training example.</li>
                <li style="margin-bottom: 6px;"><b>teach:</b> Opens an editor dialog to write the ideal response Karl should have given. Saves it as a corrected training example.</li>
            </ul>
            
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">2. Exporting Dataset</b><br>
            Use the built-in exporter to format the curated dataset into the standard HuggingFace ShareGPT format:</p>
            <pre style="background-color: {c['bg_deep']}; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 9.5pt; color: {c['text']}; border: 1px solid {c['border']};">python -c "from app.utils.training_curator import export_unsloth; export_unsloth()"</pre>
            <p style="margin-top: 6px; margin-bottom: 16px;">This writes the formatted data to <code>data/training/export_unsloth.jsonl</code>.</p>

            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">3. Validation Heuristics</b><br>
            Before tuning, run the validation tool to analyze training health:</p>
            <pre style="background-color: {c['bg_deep']}; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 9.5pt; color: {c['text']}; border: 1px solid {c['border']};">python training/validate_dataset.py</pre>
            <ul style="margin-left: 16px; margin-top: 12px;">
                <li style="margin-bottom: 6px;"><b>count:</b> Requires &ge; 20 examples, recommends 50+ for stable local fine-tuning.</li>
                <li style="margin-bottom: 6px;"><b>balance:</b> Requires corrected examples to make up &ge; 20% of the dataset to avoid bias.</li>
                <li style="margin-bottom: 6px;"><b>token limits:</b> Warns if examples exceed 512 tokens to prevent sequence truncations.</li>
            </ul>
        </div>
        """
        self.tuning_doc1.setHtml(html1)

        html2 = f"""
        <div style="line-height: 160%; font-size: 10.5pt; color: {c['text']};">
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">1. QLoRA Adapter Configuration</b><br>
            Karl includes a template config in <code>training/qlora_config_template.yaml</code> optimized for low-resource local tuning:</p>
            <ul style="margin-left: 16px; margin-bottom: 16px;">
                <li style="margin-bottom: 6px;"><b>4-bit quantization:</b> NF4 quantization and bfloat16 datatypes fit the model in low VRAM.</li>
                <li style="margin-bottom: 6px;"><b>adapter weights:</b> Targets attention projection modules (q_proj, k_proj, v_proj, o_proj) with Rank (16) and Alpha (32).</li>
            </ul>

            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">2. Adapter Merging</b><br>
            After training is complete, merge your PEFT adapter back into the base model weights:</p>
            <pre style="background-color: {c['bg_deep']}; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 9.5pt; color: {c['text']}; border: 1px solid {c['border']};">from peft import PeftModel
from transformers import AutoModelForCausalLM

base = AutoModelForCausalLM.from_pretrained(model_name)
model = PeftModel.from_pretrained(base, "data/training/adapters/")
model = model.merge_and_unload()
model.save_pretrained("data/training/merged_model/")</pre>

            <p style="margin-top: 16px; margin-bottom: 12px;"><b style="color: {c['accent']};">3. Quantizing to GGUF</b><br>
            Convert your merged model directory to GGUF format using <code>llama.cpp</code>:</p>
            <pre style="background-color: {c['bg_deep']}; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 9.5pt; color: {c['text']}; border: 1px solid {c['border']};">python convert.py data/training/merged_model/ --outtype q4_K_M</pre>
            <p style="margin-top: 8px;">Copy the resulting <code>ggml-model-q4_K_M.gguf</code> to <code>data/models/</code> to hot-reload your custom fine-tuned model in Karl.</p>
        </div>
        """
        self.tuning_doc2.setHtml(html2)

        html3 = f"""
        <div style="line-height: 160%; font-size: 10.5pt; color: {c['text']};">
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">1. Hot-Reloadable Extension Points</b><br>
            Karl features an import-reloading loop that reloads core scripts before every generation turn. You can modify these files directly to customize how Karl behaves:</p>
            <ul style="margin-left: 16px; margin-bottom: 16px;">
                <li style="margin-bottom: 8px;"><b><a href="file:///{os.path.abspath('core/interaction_loop.py').replace('\\\\', '/').replace('\\', '/')}" style="color: {c['accent']}; text-decoration: none;">core/interaction_loop.py</a></b><br>
                Controls prompt construction. Customize ChatML wrappers or pre-seeded tokens.</li>
                <li style="margin-bottom: 8px;"><b><a href="file:///{os.path.abspath('core/prompt_templates.py').replace('\\\\', '/').replace('\\', '/')}" style="color: {c['accent']}; text-decoration: none;">core/prompt_templates.py</a></b><br>
                Define new system message templates with variable placeholders.</li>
                <li style="margin-bottom: 8px;"><b><a href="file:///{os.path.abspath('core/workflows.py').replace('\\\\', '/').replace('\\', '/')}" style="color: {c['accent']}; text-decoration: none;">core/workflows.py</a></b><br>
                Group templates, default RAG behavior, output schemas, and evaluation metrics.</li>
                <li style="margin-bottom: 8px;"><b><a href="file:///{os.path.abspath('core/agentic_loop.py').replace('\\\\', '/').replace('\\', '/')}" style="color: {c['accent']}; text-decoration: none;">core/agentic_loop.py</a></b><br>
                Customize stop conditions and dynamic next-prompt instructions for autonomous loops.</li>
            </ul>
            
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">2. Interactive Testing</b><br>
            Modify any of the files above, click generate, and Karl will hot-reload your code changes instantly. No application restart required!</p>
            <p style="margin-bottom: 12px;"><b style="color: {c['accent']};">3. Evaluation Framework</b><br>
            Test your prompt engineering or model performance against local test suites:</p>
            <pre style="background-color: {c['bg_deep']}; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 9.5pt; color: {c['text']}; border: 1px solid {c['border']};">python eval/run_eval.py</pre>
        </div>
        """
        self.tuning_doc3.setHtml(html3)

    def _config_col(self) -> QVBoxLayout:
        l = QVBoxLayout()  # noqa: E741
        l.setSpacing(4)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)
        return l

    def _config_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        c = self._chat_colors() if hasattr(self, '_current_theme') else {"accent": "#3B82F6"}
        lbl.setStyleSheet(
            f"color: {c.get('accent', '#3B82F6')}; font-size: 13pt; font-weight: bold; "
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
        self._status_lbl.setStyleSheet("font-size: 9pt; background: transparent;")
        sb.addWidget(self._status_lbl)
        self._latency_lbl = QLabel("")
        self._latency_lbl.setStyleSheet("font-size: 9pt; background: transparent;")
        sb.addPermanentWidget(self._latency_lbl)

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    # ==========================================================================
    # Theme
    # ==========================================================================

    def _load_saved_theme(self) -> str:
        path = os.path.join("data", "active_theme.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    theme = data.get("theme", "Midnight")
                    if theme in THEMES:
                        return theme
            except Exception:
                pass
        return "Midnight"

    def _save_saved_theme(self, theme: str):
        path = os.path.join("data", "active_theme.json")
        try:
            os.makedirs("data", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"theme": theme}, f, indent=2)
        except Exception as e:
            print(f"[Theme] Error saving theme: {e}")

    def _apply_theme(self, name: str):
        self._current_theme = name
        QApplication.instance().setStyleSheet(generate_stylesheet(name))
        self._save_saved_theme(name)
        if hasattr(self, "tuning_doc1") and hasattr(self, "tuning_doc2"):
            self._update_tuning_docs()

    def _apply_theme_from_navbar(self, name: str):
        self._apply_theme(name)
        if hasattr(self, "config_theme") and self.config_theme.currentText() != name:
            self.config_theme.blockSignals(True)
            self.config_theme.setCurrentText(name)
            self.config_theme.blockSignals(False)

    def _apply_theme_from_config(self, name: str):
        self._apply_theme(name)
        if hasattr(self, "nav_theme") and self.nav_theme.currentText() != name:
            self.nav_theme.blockSignals(True)
            self.nav_theme.setCurrentText(name)
            self.nav_theme.blockSignals(False)

    def _on_workflow_changed(self, index: int):
        data = self.workflow_combo.itemData(index)
        if data is None:
            return
        from core.workflows import get_workflow
        try:
            wf = get_workflow(data)
            from core.prompt_templates import TEMPLATES
            raw_template = TEMPLATES.get(wf["template"], "")
            self.sys_prompt_input.blockSignals(True)
            self.sys_prompt_input.setPlainText(raw_template)
            self.sys_prompt_input.blockSignals(False)
            if "rag_top_k" in wf:
                self.rag_spin.setValue(wf["rag_top_k"])
            self._set_status(f"steered to: {wf['label']}")
        except Exception as e:
            self._set_status(f"error loading workflow: {e}")

    def _on_sys_prompt_edited(self):
        self.workflow_combo.blockSignals(True)
        self.workflow_combo.setCurrentIndex(0)
        self.workflow_combo.blockSignals(False)

    # ==========================================================================
    # Reasoning panel toggle
    # ==========================================================================

    def _toggle_thinking(self):
        self._thinking_visible = not self._thinking_visible
        self.thought_display.setVisible(self._thinking_visible)
        self.think_toggle.setText("hide" if self._thinking_visible else "show")

    # ==========================================================================
    # Session management
    # ==========================================================================

    def _refresh_sessions(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def _new_session(self):
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.terminate()
        if hasattr(self, "agentic_thread") and self.agentic_thread.isRunning():
            self.agentic_thread.request_stop()
            self.agentic_thread.wait()
        self.chat_history     = []
        self.current_session  = None
        self.chat_display.clear()
        self.thought_display.clear()
        self._set_status("new session")
        self._set_controls(True)
        self.stop_btn.setEnabled(False)
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText("idle")

    def _save_session(self):
        if not self.chat_history:
            return
        self.current_session = self.memory_manager.save_session(
            self.chat_history,
            self.sys_prompt_input.toPlainText(),
            self.current_session
        )
        self._refresh_sessions()
        self._set_status(f"saved: {self.current_session}")

    def _load_session(self, item):
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.terminate()
        if hasattr(self, "agentic_thread") and self.agentic_thread.isRunning():
            self.agentic_thread.request_stop()
            self.agentic_thread.wait()
        sys_prompt, history = self.memory_manager.load_session(item.text())
        self.sys_prompt_input.setPlainText(sys_prompt)
        self.chat_history    = history
        self.current_session = item.text()
        self.chat_display.clear()
        self.thought_display.clear()
        for msg in history:
            role, content = msg.get("role"), msg.get("content", "")
            if role == "user":
                if "Good start. Continue your reasoning" in content or "[Iteration" in content or "Reflection Loop" in content:
                    # Clean up prefix for reflection prompts if any
                    clean_p = content
                    self._append_loop_prompt(clean_p, 0)
                else:
                    self._append_user_msg(content)
            elif role == "assistant":
                clean = content.split("</think>", 1)[1].strip() if "</think>" in content else content
                self._append_assistant_header()
                self.chat_display.append(clean)
        self._set_status(f"loaded: {item.text()}")

    # ==========================================================================
    # Knowledge Base
    # ==========================================================================

    def _ingest_doc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select file to ingest", "",
            "Supported (*.pdf *.docx *.txt *.py *.md *.csv *.xlsx *.xls);;All (*.*)"
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

    def _current_workflow_meta(self) -> tuple[str, str]:
        workflow_name = self.workflow_combo.currentData() if hasattr(self, "workflow_combo") else None
        if workflow_name is None:
            return "general_chat", "custom_prompt"

        from core.workflows import get_workflow
        workflow = get_workflow(workflow_name)
        return workflow_name, workflow["template"]

    def _render_system_prompt(self, retrieved: list[str], user_text: str) -> tuple[str, str, str]:
        workflow_name = self.workflow_combo.currentData()
        custom_prompt = self.sys_prompt_input.toPlainText().strip() or self.DEFAULT_SYSTEM_PROMPT

        if workflow_name is None:
            if not retrieved:
                return custom_prompt, "general_chat", "custom_prompt"

            rag_context = self._format_rag_context(retrieved)
            return (
                custom_prompt
                + "\n\n---\nRELEVANT CONTEXT FROM KNOWLEDGE BASE:\n"
                + rag_context
                + "\n---",
                "general_chat",
                "custom_prompt",
            )

        from core.prompt_templates import get_template
        from core.workflows import get_workflow

        workflow = get_workflow(workflow_name)
        template_name = workflow["template"]
        rag_context = self._format_rag_context(retrieved) if retrieved else "(No context retrieved.)"
        schema = json.dumps(workflow.get("output_schema"), indent=2) if workflow.get("output_schema") else "(No schema specified.)"

        return (
            get_template(template_name, rag_context=rag_context, schema=schema, code=user_text),
            workflow_name,
            template_name,
        )

    def _format_rag_context(self, retrieved: list[str]) -> str:
        # Each chunk averages roughly 1.35 tokens/char. Reserve about 1500
        # tokens for RAG while leaving room for history and generation.
        rag_char_budget = 4500
        rag_lines = []
        running_chars = 0
        for chunk in retrieved:
            if running_chars + len(chunk) > rag_char_budget:
                remaining = rag_char_budget - running_chars
                if remaining > 120:
                    rag_lines.append(chunk[:remaining] + " [...]")
                break
            rag_lines.append(chunk)
            running_chars += len(chunk)
        return "\n\n".join(rag_lines)

    # ==========================================================================
    # Generation
    # ==========================================================================

    def _chat_colors(self) -> dict:
        t = THEMES.get(self._current_theme, THEMES["Midnight"])
        return {
            "accent": t.get("accent", "#3B82F6"),
            "secondary": t.get("text_secondary", "#71717A"),
            "text": t.get("text_primary", "#DDDDE0"),
            "bg_deep": t.get("bg_deep", "#07070A"),
            "border": t.get("border", "#252528"),
            "text_muted": t.get("text_muted", "#3F3F46"),
            "thought_text": t.get("thought_text", "#2D4A8A"),
        }

    def _append_user_msg(self, text: str):
        c = self._chat_colors()
        self.chat_display.append(
            f"<div style='margin-top: 24px; margin-bottom: 8px; border-bottom: 1px solid {c['border']}; padding-bottom: 6px;'>"
            f"<span style='color: {c['accent']}; font-family: monospace; font-size: 9.5pt; font-weight: bold; letter-spacing: 0.08em;'>[user]</span>"
            f"</div>"
            f"<div style='line-height: 160%; color: {c['text']};'>{text}</div>"
        )

    def _append_assistant_header(self, label: str = "✦ Karl"):
        c = self._chat_colors()
        display_label = label.replace("✦ ", "").replace("Karl", "karl").lower()
        self.chat_display.append(
            f"<div style='margin-top: 28px; margin-bottom: 8px; border-bottom: 1px solid {c['border']}; padding-bottom: 6px;'>"
            f"<span style='color: #10B981; font-family: monospace; font-size: 9.5pt; font-weight: bold; letter-spacing: 0.08em;'>[{display_label}]</span>"
            f"</div>"
        )

    def _append_loop_prompt(self, text: str, iteration: int):
        c = self._chat_colors()
        self.chat_display.append(
            f"<div style='margin-top: 24px; margin-bottom: 8px; border-bottom: 1px solid {c['border']}; padding-bottom: 6px;'>"
            f"<span style='color: #F59E0B; font-family: monospace; font-size: 9.5pt; font-weight: bold; letter-spacing: 0.08em;'>[reflection pass {iteration}]</span>"
            f"</div>"
            f"<div style='line-height: 160%; color: {c['text_muted']}; font-style: italic;'>{text}</div>"
        )

    def _send(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._last_user_msg  = text
        self.accept_btn.setEnabled(False)
        self.correct_btn.setEnabled(False)
        self.accept_btn.setText("approve")
        self.correct_btn.setText("teach")
        self._set_controls(False)

        self._append_user_msg(text)
        self._append_assistant_header()
        self.thought_display.append(f"\n/* --- {text[:60]} --- */\n")

        self.chat_history.append({"role": "user", "content": text})

        # Retrieve context
        top_k     = self.rag_spin.value()
        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        self._last_chunks = retrieved

        sys_prompt, workflow_name, template_name = self._render_system_prompt(retrieved, text)

        self._gen_start = _time.time()
        self._set_status("Thinking...")

        self.thread = LLMThread(
            sys_prompt,
            self.chat_history,
            self._hyperparams(),
            retrieved,
            workflow=workflow_name,
            template=template_name,
        )
        self.thread.new_thought_token.connect(self._on_thought)
        self.thread.new_chat_token.connect(self._on_chat)
        self.thread.new_raw_token.connect(lambda _: None)
        self.thread.generation_finished.connect(self._on_done)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _stop_gen(self):
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.terminate()
        if hasattr(self, "agentic_thread") and self.agentic_thread.isRunning():
            self.agentic_thread.request_stop()
        self._set_controls(True)
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText("stopped")
        self._set_status("stopped")

    def _on_thought(self, token: str):
        if "[AGENTIC LOOP" in token:
            import re
            m = re.search(r"Iteration\s+(\d+)", token)
            iter_num = m.group(1) if m else "Next"
            self.thought_display.append(f"\n/* reflection loop -- pass {iter_num} */\n")
            return

        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.thought_display.setTextCursor(c)
        self.thought_display.ensureCursorVisible()

    def _on_chat(self, token: str):
        if "[Iteration " in token:
            import re
            m = re.search(r"Iteration\s+(\d+)", token)
            iter_num = m.group(1) if m else "Next"
            self._append_assistant_header(f"karl [pass {iter_num}]")
            return

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
        self._set_status(f"done — {latency:.1f}s{rag_note}")
        self._latency_lbl.setText(f"last: {latency:.1f}s")

        self._set_controls(True)
        self.stop_btn.setEnabled(False)
        self.user_input.setFocus()

    def _on_error(self, msg: str):
        self.chat_display.append(
            f"<div style='margin-top: 18px; margin-bottom: 4px;'>"
            f"<span style='color: #EF4444; font-weight: bold; font-family: monospace; font-size: 9.5pt;'>[error: {msg}]</span>"
            f"</div>"
        )
        self._set_controls(True)
        self.stop_btn.setEnabled(False)
        self.loop_status.setText("error")
        self._set_status(f"error: {msg[:80]}")

    # ==========================================================================
    # Agentic Loop
    # ==========================================================================

    def _start_loop(self, auto=False):
        if not self.chat_history:
            QMessageBox.information(
                self, "No seed",
                "Go to the Chat page and send a message first to seed the loop."
            )
            return

        import core.agentic_loop
        import importlib
        importlib.reload(core.agentic_loop)

        # If not automatic start, and last message is assistant, build and inject first loop prompt
        if not auto:
            if self.chat_history[-1]["role"] == "assistant":
                last_resp = self.chat_history[-1]["content"]
                next_prompt = core.agentic_loop.build_next_prompt(last_resp, 0)
                self.chat_history.append({"role": "user", "content": next_prompt})
                self._append_loop_prompt(next_prompt, 1)
        else:
            # For automatic start, we know the last message is the assistant response from LLMThread,
            # so we inject the first loop prompt
            last_resp = self.chat_history[-1]["content"]
            next_prompt = core.agentic_loop.build_next_prompt(last_resp, 0)
            self.chat_history.append({"role": "user", "content": next_prompt})
            self._append_loop_prompt(next_prompt, 1)

        self._set_controls(False)
        self.stop_loop_btn.setEnabled(True)
        self.loop_status.setText("running")
        self.loop_status.setStyleSheet(
            "color: #22C55E; font-size: 10pt; padding-top: 6px; background: transparent;"
        )
        self.thought_display.append("\n/* autonomous loop mode active */\n")
        self._set_status("loop running...")

        sys_prompt, workflow_name, template_name = self._render_system_prompt([], self._last_user_msg)
        self.agentic_thread = AgenticThread(
            sys_prompt,
            self.chat_history,
            self._hyperparams(),
            workflow=workflow_name,
            template=template_name,
        )
        self.agentic_thread.new_thought_token.connect(self._on_thought)
        self.agentic_thread.new_chat_token.connect(self._on_chat)
        self.agentic_thread.new_raw_token.connect(lambda _: None)
        self.agentic_thread.iteration_finished.connect(self._on_iteration_finished)
        self.agentic_thread.loop_finished.connect(self._on_loop_done)
        self.agentic_thread.error_occurred.connect(self._on_error)
        self.agentic_thread.start()

    def _on_iteration_finished(self, iter_idx, thought, response):
        self.chat_history.append({"role": "assistant", "content": response})
        self._last_response = response

        import core.agentic_loop
        import importlib
        importlib.reload(core.agentic_loop)

        # AgenticThread increments iteration after emitting, so the next iteration is iter_idx + 1
        next_iter = iter_idx + 1
        if core.agentic_loop.should_continue(next_iter, response):
            next_prompt = core.agentic_loop.build_next_prompt(response, next_iter)
            self.chat_history.append({"role": "user", "content": next_prompt})
            self._append_loop_prompt(next_prompt, next_iter + 1)

    def _stop_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText("stopping...")
        self.loop_status.setStyleSheet(
            "color: #F59E0B; font-size: 10pt; padding-top: 6px; background: transparent;"
        )

    def _on_loop_done(self, total: int):
        self._set_controls(True)
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText(f"done ({total} iterations)")
        c = self._chat_colors()
        self.loop_status.setStyleSheet(
            f"color: {c['secondary']}; font-size: 10pt; padding-top: 6px; background: transparent;"
        )
        self.chat_display.append(
            f"<div style='margin-top: 18px; margin-bottom: 4px;'>"
            f"<span style='color: #10B981; font-weight: bold; font-family: monospace; font-size: 9.5pt;'>[loop finished -- {total} iterations completed]</span>"
            f"</div>"
        )
        self.user_input.setFocus()
        self._set_status(f"loop done -- {total} iterations")

    # ==========================================================================
    # Training Curator
    # ==========================================================================

    def _refresh_dataset_stats(self):
        """Update the live dataset stats label on the Tuning page."""
        if not hasattr(self, 'dataset_stats_lbl'):
            return
        try:
            from app.utils.training_curator import get_stats
            s = get_stats()
            self.dataset_stats_lbl.setText(
                f"{s['total']} examples total  ·  "
                f"{s['approved']} approved  ·  "
                f"{s['corrected']} corrected"
            )
        except Exception:
            self.dataset_stats_lbl.setText("dataset: 0 examples")

    def _export_dataset(self):
        """Export curated dataset and show result in status bar."""
        try:
            from app.utils.training_curator import export_unsloth, get_stats
            s = get_stats()
            if s['total'] == 0:
                self._set_status("no examples to export yet — approve or teach some responses first")
                return
            out_path, count = export_unsloth()
            self._set_status(f"exported {count} examples → {out_path}")
        except Exception as e:
            self._set_status(f"export failed: {e}")

    def _accept(self):
        if not self._last_user_msg or not self._last_response:
            return
        save_example(
            system_prompt=self.sys_prompt_input.toPlainText(),
            user_msg=self._last_user_msg,
            good_response=self._last_response,
            source="approved"
        )
        self.accept_btn.setEnabled(False)
        self.correct_btn.setEnabled(False)
        self.accept_btn.setText("saved ✓")
        self._set_status("training example approved and saved")
        self._refresh_dataset_stats()

    def _correct(self):
        if not self._last_user_msg:
            return
        c = self._chat_colors()
        dlg = QDialog(self)
        dlg.setWindowTitle("Teach Karl")
        dlg.resize(720, 380)
        dlg.setStyleSheet(
            f"QDialog {{ background: {c['bg_deep']}; color: {c['text']}; }}"
            f"QLabel {{ color: {c['text']}; background: transparent; font-size: 10pt; }}"
            f"QTextEdit {{ background: {c['bg_deep']}; color: {c['text']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; padding: 8px; font-size: 10pt; }}"
            f"QPushButton {{ background: {c['accent']}; color: white; border: none; "
            "border-radius: 6px; padding: 8px 18px; font-size: 10pt; font-weight: bold; }"
            "QPushButton:hover { opacity: 0.9; }"
        )
        dl = QVBoxLayout(dlg)
        dl.setContentsMargins(24, 24, 24, 18)
        dl.setSpacing(12)
        prompt_lbl = QLabel(f"Prompt:  {self._last_user_msg[:120]}")
        prompt_lbl.setWordWrap(True)
        dl.addWidget(prompt_lbl)
        ideal_lbl = QLabel("Write the ideal response Karl should have given:")
        dl.addWidget(ideal_lbl)
        editor = QTextEdit()
        editor.setPlainText(self._last_response)
        editor.setMinimumHeight(180)
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
                self.correct_btn.setText("saved ✓")
                self.accept_btn.setEnabled(False)
                self.correct_btn.setEnabled(False)
                self._set_status("correction saved as training example")
                self._refresh_dataset_stats()

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
