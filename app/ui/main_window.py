"""
Karl -- Main Window v4
======================
Two-page layout:
  Page 1 (Chat):      Sessions sidebar + Diagnostic Lane + Final Response + Input + Agentic
  Page 2 (Configure): System Prompt + Workflow + RAG + Generation + Training Curator

Navigation bar at top. 30 color themes selectable from nav bar.
No emojis. Professional. Calm. Sharp.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QSplitter,
    QTextEdit, QLabel, QDoubleSpinBox, QSpinBox,
    QListWidget, QFileDialog, QCheckBox, QMessageBox, QDialog,
    QDialogButtonBox, QComboBox, QFrame, QStatusBar,
    QScrollArea, QStackedWidget, QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import save_example, get_stats, export_unsloth
from app.ui.themes import THEMES, generate_stylesheet
from core.workflows import list_workflows, get_workflow
from core.prompt_templates import get_template, list_templates


# ---------------------------------------------------------------------------
# Background upgrade threads
# ---------------------------------------------------------------------------

class UpgradeCheckThread(QThread):
    upgrade_available = pyqtSignal(dict, dict)
    no_upgrade = pyqtSignal()

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


class UpgradeDownloadThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, entry):
        super().__init__()
        self.entry = entry

    def run(self):
        try:
            from app.engine.upgrade_manager import perform_upgrade
            path = perform_upgrade(
                self.entry,
                progress_callback=lambda n, t: self.progress.emit(n, t)
            )
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------

def _rule(theme_border: str = "#222225") -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(
        f"border: none; border-top: 1px solid {theme_border}; "
        "max-height: 1px; background: transparent;"
    )
    return f


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #505055; font-size: 8.5pt; font-weight: bold; "
        "letter-spacing: 0.10em; padding: 16px 0 6px 0; background: transparent;"
    )
    return lbl


def _field_row(label_text: str, widget: QWidget, tip: str = "") -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setStyleSheet("color: #8B8B8F; font-size: 10.5pt; background: transparent;")
    lbl.setMinimumWidth(100)
    if tip:
        lbl.setToolTip(tip)
        widget.setToolTip(tip)
    row.addWidget(lbl)
    row.addWidget(widget)
    row.addStretch()
    return row


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl")
        self.resize(1540, 940)
        self.setMinimumSize(1200, 720)

        # State
        self.chat_history: list[dict] = []
        self.memory_manager = MemoryManager()
        self.rag_pipeline = RAGPipeline()
        self.current_session_file = None
        self.agentic_thread = None
        self._pending_upgrade_entry = None
        self._last_user_msg = ""
        self._last_response = ""
        self._last_workflow = "general_chat"
        self._last_template = "reasoning_minimal"
        self._last_latency = 0.0
        self._last_chunks_used: list = []
        self._gen_start_time = 0.0
        self._current_theme = "Midnight"

        self._build_ui()
        self._build_status_bar()
        self.refresh_session_list()
        self._run_upgrade_check()
        self._refresh_curator_stats()
        self._apply_theme("Midnight")

    # ==========================================================================
    # Top-level UI
    # ==========================================================================

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Nav bar
        root_layout.addWidget(self._build_nav_bar())

        # Page stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_chat_page())    # index 0
        self.stack.addWidget(self._build_config_page())  # index 1
        root_layout.addWidget(self.stack)

    def _build_nav_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setObjectName("nav_bar")
        bar.setStyleSheet(
            "QWidget#nav_bar { background-color: #08080B; "
            "border-bottom: 1px solid #1A1A1C; }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # App name
        app_lbl = QLabel("KARL")
        app_lbl.setStyleSheet(
            "color: #3F3F46; font-size: 9pt; font-weight: bold; "
            "letter-spacing: 0.20em; padding-right: 24px; background: transparent;"
        )
        layout.addWidget(app_lbl)

        # Nav buttons
        self.nav_chat_btn = QPushButton("Chat")
        self.nav_chat_btn.setObjectName("btn_nav")
        self.nav_chat_btn.setProperty("active", "true")
        self.nav_chat_btn.clicked.connect(lambda: self._switch_page(0))
        self.nav_chat_btn.setToolTip(
            "<b>Chat</b><br>"
            "The main interaction view.<br>"
            "Contains the Diagnostic Lane (model reasoning), Final Response, "
            "input bar, and agentic loop controls."
        )

        self.nav_config_btn = QPushButton("Configure")
        self.nav_config_btn.setObjectName("btn_nav")
        self.nav_config_btn.setProperty("active", "false")
        self.nav_config_btn.clicked.connect(lambda: self._switch_page(1))
        self.nav_config_btn.setToolTip(
            "<b>Configure</b><br>"
            "System prompt, workflow mode, prompt template, RAG settings, "
            "generation hyperparameters, and training data curator."
        )

        layout.addWidget(self.nav_chat_btn)
        layout.addWidget(self.nav_config_btn)
        layout.addStretch()

        # Theme selector
        theme_lbl = QLabel("Theme")
        theme_lbl.setStyleSheet(
            "color: #3F3F46; font-size: 9.5pt; padding-right: 8px; background: transparent;"
        )
        layout.addWidget(theme_lbl)

        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(150)
        self.theme_combo.setFixedHeight(30)
        self.theme_combo.setStyleSheet(
            "QComboBox { background-color: #111113; border: 1px solid #252528; "
            "border-radius: 4px; padding: 4px 10px; color: #A1A1AA; font-size: 9.5pt; }"
            "QComboBox:hover { border-color: #3F3F46; color: #DDDDE0; }"
            "QComboBox QAbstractItemView { background-color: #111113; border: 1px solid #252528; "
            "color: #DDDDE0; selection-background-color: #1D4ED8; font-size: 9.5pt; }"
        )
        for name in sorted(THEMES.keys()):
            self.theme_combo.addItem(name)
        self.theme_combo.setCurrentText("Midnight")
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        self.theme_combo.setToolTip(
            "<b>Color Theme</b><br>"
            "30 hand-crafted dark palettes.<br>"
            "The entire UI re-renders immediately on selection."
        )
        layout.addWidget(self.theme_combo)

        return bar

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        # Update nav button active state
        self.nav_chat_btn.setProperty("active", "true" if index == 0 else "false")
        self.nav_config_btn.setProperty("active", "true" if index == 1 else "false")
        # Force style re-polish
        self.nav_chat_btn.style().unpolish(self.nav_chat_btn)
        self.nav_chat_btn.style().polish(self.nav_chat_btn)
        self.nav_config_btn.style().unpolish(self.nav_config_btn)
        self.nav_config_btn.style().polish(self.nav_config_btn)

    def _apply_theme(self, theme_name: str):
        self._current_theme = theme_name
        qss = generate_stylesheet(theme_name)
        QApplication.instance().setStyleSheet(qss)

    # ==========================================================================
    # PAGE 1 -- Chat
    # ==========================================================================

    def _build_chat_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        splitter.addWidget(self._build_sessions_sidebar())
        splitter.addWidget(self._build_main_chat())
        splitter.setSizes([240, 1300])

        return page

    # -- Sessions sidebar --

    def _build_sessions_sidebar(self) -> QWidget:
        p = QWidget()
        p.setFixedWidth(240)
        p.setObjectName("sidebar")
        p.setStyleSheet("QWidget#sidebar { background-color: #08080B; border-right: 1px solid #1A1A1C; }")
        l = QVBoxLayout(p)
        l.setContentsMargins(14, 16, 14, 16)
        l.setSpacing(6)

        l.addWidget(_section_label("Sessions"))

        self.session_list = QListWidget()
        self.session_list.setToolTip(
            "<b>Saved Sessions</b><br>"
            "Each session stores your full conversation history and system prompt.<br>"
            "Double-click to reload."
        )
        self.session_list.itemDoubleClicked.connect(self.load_session)
        self.session_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        l.addWidget(self.session_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip(
            "<b>New Session</b><br>Clears the conversation and starts fresh."
        )
        self.btn_new.clicked.connect(self.new_session)
        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip(
            "<b>Save Session</b><br>Saves the current conversation to data/sessions/."
        )
        self.btn_save.clicked.connect(self.save_session)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_save)
        l.addLayout(btn_row)

        return p

    # -- Main chat area --

    def _build_main_chat(self) -> QWidget:
        p = QWidget()
        l = QVBoxLayout(p)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        # Vertical splitter: Diagnostic Lane | Final Response
        vs = QSplitter(Qt.Orientation.Vertical)
        vs.setChildrenCollapsible(False)
        l.addWidget(vs)

        vs.addWidget(self._build_diagnostic_lane())
        vs.addWidget(self._build_response_area())
        vs.setSizes([320, 580])

        return p

    def _build_diagnostic_lane(self) -> QWidget:
        c = QWidget()
        c.setObjectName("diagnostic_container")
        c.setStyleSheet(
            "QWidget#diagnostic_container { background-color: #09090C; border-bottom: 1px solid #1A1A1C; }"
        )
        l = QVBoxLayout(c)
        l.setContentsMargins(20, 16, 20, 12)
        l.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("DIAGNOSTIC LANE")
        title.setStyleSheet(
            "color: #1E2C50; font-size: 8.5pt; font-weight: bold; letter-spacing: 0.12em; background: transparent;"
        )
        title.setToolTip(
            "<b>Diagnostic Lane -- Reasoning Trace</b><br>"
            "Streams the model's internal chain-of-thought in real time.<br>"
            "DeepSeek-R1 wraps reasoning inside &lt;think&gt; tags.<br>"
            "Karl intercepts those tokens and routes them here -- before the final answer.<br><br>"
            "This is where you see HOW the model arrives at its answer.<br>"
            "Edit core/cognitive_parser.py to change the parsing rules."
        )
        sub = QLabel("  model internal reasoning -- live")
        sub.setStyleSheet("color: #141830; font-size: 8.5pt; background: transparent;")
        hdr.addWidget(title)
        hdr.addWidget(sub)
        hdr.addStretch()
        l.addLayout(hdr)

        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #07080F; color: #2A3E7A; "
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 9.5pt; "
            "border: 1px solid #0F1828; border-radius: 4px; padding: 10px 14px;"
        )
        l.addWidget(self.thought_display)

        return c

    def _build_response_area(self) -> QWidget:
        c = QWidget()
        l = QVBoxLayout(c)
        l.setContentsMargins(20, 14, 20, 16)
        l.setSpacing(10)

        # Header row with rating buttons
        resp_hdr = QHBoxLayout()
        resp_title = QLabel("FINAL RESPONSE")
        resp_title.setStyleSheet(
            "color: #3A3A3F; font-size: 8.5pt; font-weight: bold; letter-spacing: 0.12em; background: transparent;"
        )
        resp_title.setToolTip(
            "<b>Final Response</b><br>"
            "The model's cleaned answer -- everything after the &lt;/think&gt; tag.<br>"
            "Stored in conversation history. The raw reasoning block is stripped<br>"
            "before entering history to keep context lean."
        )
        resp_hdr.addWidget(resp_title)
        resp_hdr.addStretch()

        self.thumbs_up_btn = QPushButton("Accept")
        self.thumbs_up_btn.setObjectName("btn_accept")
        self.thumbs_up_btn.setFixedHeight(28)
        self.thumbs_up_btn.setToolTip(
            "<b>Accept</b><br>"
            "Saves the (prompt, response) pair as a positive training example."
        )
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_up_btn.clicked.connect(self._rate_thumbs_up)

        self.thumbs_down_btn = QPushButton("Correct")
        self.thumbs_down_btn.setObjectName("btn_correct")
        self.thumbs_down_btn.setFixedHeight(28)
        self.thumbs_down_btn.setToolTip(
            "<b>Correct</b><br>"
            "Opens an editor to write the ideal response.<br>"
            "The corrected pair is saved for fine-tuning."
        )
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_down_btn.clicked.connect(self._rate_thumbs_down)

        resp_hdr.addWidget(self.thumbs_up_btn)
        resp_hdr.addWidget(self.thumbs_down_btn)
        l.addLayout(resp_hdr)

        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet(
            "background-color: #111113; color: #DDDDE0; "
            "font-family: 'Segoe UI', sans-serif; font-size: 11.5pt; "
            "border: 1px solid #1E1E21; border-radius: 4px; padding: 14px 18px;"
        )
        l.addWidget(self.chat_display)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter your prompt...")
        self.user_input.setMinimumHeight(40)
        self.user_input.setToolTip(
            "<b>Prompt Input</b><br>"
            "Type your message and press Enter or click Generate."
        )
        self.user_input.returnPressed.connect(self.send_message)

        self.force_thought_button = QPushButton("Inject Thought")
        self.force_thought_button.setObjectName("btn_force_thought")
        self.force_thought_button.setFixedHeight(40)
        self.force_thought_button.setToolTip(
            "<b>Inject Thought</b><br>"
            "Takes the text in the input box and injects it as a fake &lt;think&gt; block<br>"
            "attributed to the assistant -- planting a seeded reasoning premise."
        )
        self.force_thought_button.clicked.connect(self.force_thought)

        self.send_button = QPushButton("Generate")
        self.send_button.setObjectName("btn_generate")
        self.send_button.setFixedHeight(40)
        self.send_button.setToolTip(
            "<b>Generate</b><br>"
            "Sends your prompt and streams the response.<br>"
            "Diagnostic Lane receives reasoning tokens; Final Response gets the cleaned answer."
        )
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.user_input)
        input_row.addWidget(self.force_thought_button)
        input_row.addWidget(self.send_button)
        l.addLayout(input_row)

        # Report bar
        self.report_display = QTextBrowser()
        self.report_display.setFixedHeight(38)
        self.report_display.setStyleSheet(
            "background-color: #07070A; color: #22C55E; "
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 8.5pt; "
            "border: 1px solid #052E16; border-radius: 4px; padding: 6px 12px;"
        )
        self.report_display.setPlaceholderText("Generation report appears here.")
        l.addWidget(self.report_display)

        # Agentic controls row
        l.addWidget(_rule())
        ag_row = QHBoxLayout()
        ag_row.setSpacing(10)

        self.auto_loop_toggle = QCheckBox("Auto-Loop")
        self.auto_loop_toggle.setToolTip(
            "<b>Auto-Loop</b><br>"
            "Each completed generation automatically feeds into the Agentic Loop.<br>"
            "Runs until the stop condition in core/agentic_loop.py returns False."
        )
        self.auto_loop_toggle.stateChanged.connect(self._on_auto_loop_toggled)

        self.agentic_button = QPushButton("Run Autonomous Loop")
        self.agentic_button.setObjectName("btn_agentic")
        self.agentic_button.setToolTip(
            "<b>Run Autonomous Loop</b><br>"
            "Starts the self-iteration loop. Karl generates, evaluates its own output,<br>"
            "injects a follow-up, and repeats -- driven by core/agentic_loop.py.<br><br>"
            "The loop runs up to 20 iterations or until the model writes 'FINAL ANSWER:'.<br>"
            "Edit core/agentic_loop.py to change stop conditions and prompts -- no restart needed."
        )
        self.agentic_button.clicked.connect(self.start_agentic_loop)

        self.stop_agentic_button = QPushButton("Stop")
        self.stop_agentic_button.setObjectName("btn_stop")
        self.stop_agentic_button.setEnabled(False)
        self.stop_agentic_button.setToolTip(
            "<b>Stop</b><br>"
            "Signals the loop to stop after the current generation completes."
        )
        self.stop_agentic_button.clicked.connect(self.stop_agentic_loop)

        self.agentic_status = QLabel("Idle")
        self.agentic_status.setStyleSheet(
            "color: #363639; font-size: 10pt; padding-left: 4px; background: transparent;"
        )

        ag_row.addWidget(self.auto_loop_toggle)
        ag_row.addWidget(self.agentic_button)
        ag_row.addWidget(self.stop_agentic_button)
        ag_row.addWidget(self.agentic_status)
        ag_row.addStretch()
        l.addLayout(ag_row)

        return c

    # ==========================================================================
    # PAGE 2 -- Configure
    # ==========================================================================

    def _build_config_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 40)
        content_layout.setSpacing(40)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Three columns
        content_layout.addWidget(self._build_config_col_left(), 2)
        content_layout.addWidget(self._build_config_col_mid(), 2)
        content_layout.addWidget(self._build_config_col_right(), 2)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        return page

    def _build_config_col_left(self) -> QWidget:
        """System Prompt + Knowledge Base"""
        col = QWidget()
        l = QVBoxLayout(col)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)

        # System Prompt
        l.addWidget(_section_label("System Prompt"))
        sp_hint = QLabel(
            "Defines the model's persona and rules for every generation. "
            "Changes take effect on the next Generate click -- no restart needed."
        )
        sp_hint.setWordWrap(True)
        sp_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(sp_hint)

        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlainText(
            "You are a precise, analytical AI assistant.\n"
            "When reasoning inside <think> blocks: be direct, avoid filler phrases, "
            "and do not re-state conclusions you have already reached.\n"
            "Your final answer after </think> should be clean and concise."
        )
        self.system_prompt_input.setMinimumHeight(200)
        self.system_prompt_input.setToolTip(
            "<b>System Prompt</b><br>"
            "Prepended to every generation as the &lt;|im_start|&gt;system turn.<br>"
            "For DeepSeek-R1: keep it concise -- the &lt;think&gt; block handles detail.<br>"
            "When a Workflow mode is active, the template overrides this field."
        )
        l.addWidget(self.system_prompt_input)

        # Knowledge Base
        l.addSpacing(12)
        l.addWidget(_section_label("Knowledge Base"))
        kb_hint = QLabel(
            "Ingest documents to give Karl context it retrieves automatically. "
            "Supported: PDF, DOCX, TXT, PY, MD, CSV."
        )
        kb_hint.setWordWrap(True)
        kb_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(kb_hint)

        self.kb_list = QListWidget()
        self.kb_list.setMinimumHeight(140)
        self.kb_list.setToolTip(
            "<b>Ingested Documents</b><br>"
            "Files here have been chunked, embedded, and stored in a local FAISS index.<br>"
            "The index persists across restarts in data/vector_db/."
        )
        l.addWidget(self.kb_list)

        self.btn_ingest = QPushButton("Ingest Document")
        self.btn_ingest.setToolTip(
            "<b>Ingest Document</b><br>"
            "Splits the file into 200-word chunks, embeds with all-MiniLM-L6-v2,<br>"
            "and adds to the local FAISS flat index."
        )
        self.btn_ingest.clicked.connect(self.ingest_document)
        l.addWidget(self.btn_ingest)

        l.addStretch()
        return col

    def _build_config_col_mid(self) -> QWidget:
        """Workflow + Template + RAG"""
        col = QWidget()
        l = QVBoxLayout(col)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Workflow
        l.addWidget(_section_label("Workflow Mode"))
        wf_hint = QLabel(
            "Workflows bundle a prompt template, RAG settings, and output schema "
            "into a single named mode. Changing workflow auto-selects template and RAG top-k."
        )
        wf_hint.setWordWrap(True)
        wf_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(wf_hint)

        self.workflow_combo = QComboBox()
        for wf_name, wf_label in list_workflows():
            self.workflow_combo.addItem(wf_label, wf_name)
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        self.workflow_combo.setToolTip(
            "<b>Workflow Mode</b><br>"
            "General Chat -- open conversation<br>"
            "Document Extractor -- structured JSON from ingested docs<br>"
            "Grounded Answer -- refuses to answer without evidence in context<br>"
            "Code Review -- JSON array of code findings"
        )
        l.addLayout(_field_row("Workflow", self.workflow_combo))

        # Template
        self.template_combo = QComboBox()
        for tpl in list_templates():
            self.template_combo.addItem(tpl)
        self.template_combo.setToolTip(
            "<b>Prompt Template</b><br>"
            "Named system-prompt templates from core/prompt_templates.py.<br>"
            "Hot-reloaded on every generation -- add your own and they appear here."
        )
        l.addLayout(_field_row("Template", self.template_combo,
                               "Prompt template applied during generation. Hot-reloaded on every click."))

        # RAG
        l.addSpacing(12)
        l.addWidget(_section_label("RAG Settings"))
        rag_hint = QLabel(
            "Retrieval-augmented generation. Documents ingested in the Knowledge Base "
            "are searched and injected into the prompt automatically."
        )
        rag_hint.setWordWrap(True)
        rag_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(rag_hint)

        self.rag_topk_spin = QSpinBox()
        self.rag_topk_spin.setRange(0, 10)
        self.rag_topk_spin.setValue(3)
        l.addLayout(_field_row("Top-K Chunks", self.rag_topk_spin,
            "<b>RAG Top-K</b><br>"
            "Number of KB chunks retrieved per generation.<br>"
            "0 disables retrieval. 3-5 is recommended."))

        self.ctx_headers_check = QCheckBox("Contextual chunk headers")
        self.ctx_headers_check.setToolTip(
            "<b>Contextual Chunk Headers</b><br>"
            "Prefixes each chunk: [Source: filename | Chunk N]<br>"
            "Helps the model cite which document a fact came from."
        )
        self.ctx_headers_check.stateChanged.connect(self._on_headers_toggled)
        l.addWidget(self.ctx_headers_check)

        # Upgrade area
        self.upgrade_label = QLabel("")
        self.upgrade_label.setWordWrap(True)
        self.upgrade_label.setStyleSheet("color: #93C5FD; font-size: 9.5pt; padding: 10px 0; background: transparent;")
        self.upgrade_label.setVisible(False)
        l.addWidget(self.upgrade_label)

        self.upgrade_button = QPushButton("Upgrade Model")
        self.upgrade_button.setToolTip(
            "<b>Upgrade Model</b><br>"
            "Downloads a larger model matched to your hardware tier,<br>"
            "updates active_model.json, and pushes to GitHub. Restart Karl after."
        )
        self.upgrade_button.setVisible(False)
        self.upgrade_button.clicked.connect(self._confirm_upgrade)
        l.addWidget(self.upgrade_button)

        l.addStretch()
        return col

    def _build_config_col_right(self) -> QWidget:
        """Generation hyperparameters + Training Curator"""
        col = QWidget()
        l = QVBoxLayout(col)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Generation
        l.addWidget(_section_label("Generation"))
        gen_hint = QLabel(
            "Controls how the model generates text. "
            "Changes apply on the next Generate click."
        )
        gen_hint.setWordWrap(True)
        gen_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(gen_hint)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setValue(0.7)
        l.addLayout(_field_row("Temperature", self.temp_spin,
            "<b>Temperature</b><br>"
            "0.0 = deterministic. 0.7 = balanced (recommended). 1.5+ = creative/chaotic.<br>"
            "For DeepSeek-R1, 0.5-0.8 works best."))

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        l.addLayout(_field_row("Top-P", self.top_p_spin,
            "<b>Top-P (Nucleus Sampling)</b><br>"
            "Only considers tokens whose cumulative probability reaches P.<br>"
            "0.95 trims improbable tokens. Lower = more focused."))

        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(64, 4096)
        self.tokens_spin.setValue(2048)
        l.addLayout(_field_row("Max Tokens", self.tokens_spin,
            "<b>Max New Tokens</b><br>"
            "Hard cap on tokens generated per turn.<br>"
            "2048 default handles long-form answers.<br>"
            "If hit, Karl chains a continuation automatically."))

        # Training Curator
        l.addSpacing(12)
        l.addWidget(_section_label("Training Curator"))
        cur_hint = QLabel(
            "Rate responses using Accept / Correct in the Chat view "
            "to build a supervised fine-tuning dataset."
        )
        cur_hint.setWordWrap(True)
        cur_hint.setStyleSheet("color: #3F3F46; font-size: 9.5pt; padding-bottom: 8px; background: transparent;")
        l.addWidget(cur_hint)

        self.curator_stats_label = QLabel("Examples: 0  (Accepted: 0  Corrected: 0)")
        self.curator_stats_label.setStyleSheet(
            "font-size: 10.5pt; color: #505055; padding-bottom: 4px; background: transparent;"
        )
        self.curator_stats_label.setToolTip(
            "<b>Curator Statistics</b><br>Data stored in data/training/curated.jsonl."
        )
        l.addWidget(self.curator_stats_label)

        export_btn = QPushButton("Export for Unsloth")
        export_btn.setToolTip(
            "<b>Export Training Data</b><br>"
            "Writes all curated pairs to a JSONL file formatted for Unsloth QLoRA.<br>"
            "See training/qlora_config_template.yaml for the training config."
        )
        export_btn.clicked.connect(self._export_training_data)
        l.addWidget(export_btn)

        # Hackable core reference
        l.addSpacing(20)
        hint_box = QLabel(
            "HACKABLE CORE -- hot-reloaded on every generation\n"
            "\n"
            "  interaction_loop.py    prompt builder\n"
            "  agentic_loop.py        loop stop condition\n"
            "  prompt_templates.py    add templates\n"
            "  workflows.py           add modes"
        )
        hint_box.setStyleSheet(
            "color: #2A2A2E; font-size: 8.5pt; font-family: 'Cascadia Code', 'Consolas', monospace; "
            "padding: 14px 16px; background-color: #09090C; border-radius: 4px; "
            "border: 1px solid #141416; line-height: 1.8;"
        )
        hint_box.setToolTip(
            "<b>Hackable Core</b><br>"
            "Karl reloads these files via importlib.reload() before every generation.<br>"
            "Save the file and click Generate -- no restart needed."
        )
        l.addWidget(hint_box)

        l.addStretch()
        return col

    # ==========================================================================
    # Status bar
    # ==========================================================================

    def _build_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #505055; font-size: 9pt;")
        self._status_bar.addWidget(self._status_lbl)
        self._latency_lbl = QLabel("")
        self._latency_lbl.setStyleSheet("color: #2A2A2E; font-size: 9pt;")
        self._status_bar.addPermanentWidget(self._latency_lbl)

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    # ==========================================================================
    # Upgrade
    # ==========================================================================

    def _run_upgrade_check(self):
        self._upgrade_check_thread = UpgradeCheckThread()
        self._upgrade_check_thread.upgrade_available.connect(self._on_upgrade_available)
        self._upgrade_check_thread.no_upgrade.connect(lambda: self._set_status("Ready"))
        self._upgrade_check_thread.start()

    def _on_upgrade_available(self, entry, profile):
        self._pending_upgrade_entry = entry
        self.upgrade_label.setText(
            f"Upgrade available -- RAM: {profile['ram_gb']} GB | VRAM: {profile['vram_gb']} GB\n"
            f"-> {entry['name']} (Tier {entry['tier']})"
        )
        self.upgrade_label.setVisible(True)
        self.upgrade_button.setVisible(True)
        self._set_status("Model upgrade available")

    def _confirm_upgrade(self):
        if not self._pending_upgrade_entry:
            return
        reply = QMessageBox.question(
            self, "Upgrade Karl",
            f"Download and switch to:\n{self._pending_upgrade_entry['name']}\n\n"
            "This will be committed to GitHub. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.upgrade_button.setEnabled(False)
            self.upgrade_label.setText("Downloading... this may take several minutes.")
            self._dl_thread = UpgradeDownloadThread(self._pending_upgrade_entry)
            self._dl_thread.finished.connect(self._on_upgrade_complete)
            self._dl_thread.error.connect(self._on_upgrade_error)
            self._dl_thread.start()

    def _on_upgrade_complete(self, path):
        self.upgrade_label.setText(f"Upgraded. Restart Karl to load the new model.\n({path})")
        self.upgrade_button.setVisible(False)

    def _on_upgrade_error(self, msg):
        self.upgrade_label.setText(f"Upgrade failed: {msg}")
        self.upgrade_button.setEnabled(True)

    # ==========================================================================
    # Workflow / Template
    # ==========================================================================

    def _on_workflow_changed(self, index):
        wf_name = self.workflow_combo.itemData(index)
        try:
            wf_cfg = get_workflow(wf_name)
            tpl = wf_cfg.get("template", "reasoning_minimal")
            for i in range(self.template_combo.count()):
                if self.template_combo.itemText(i) == tpl:
                    self.template_combo.setCurrentIndex(i)
                    break
            self.rag_topk_spin.setValue(wf_cfg.get("rag_top_k", 3))
        except KeyError:
            pass

    def _on_headers_toggled(self, state):
        self.rag_pipeline.contextual_headers = bool(state)

    def _on_auto_loop_toggled(self, state):
        self.send_button.setText("Generate + Loop" if state else "Generate")

    def _get_workflow(self) -> str:
        return self.workflow_combo.itemData(self.workflow_combo.currentIndex()) or "general_chat"

    def _get_template(self) -> str:
        return self.template_combo.currentText() or "reasoning_minimal"

    def _get_hyperparams(self) -> dict:
        return {
            "temperature": self.temp_spin.value(),
            "top_p": self.top_p_spin.value(),
            "max_tokens": self.tokens_spin.value(),
        }

    def _update_report(self, workflow, template, chunks, latency):
        n = len(chunks)
        msg = (
            f"workflow={workflow}  template={template}  "
            f"rag_chunks={n}  latency={latency:.1f}s"
        )
        self.report_display.setPlainText(msg)
        self._latency_lbl.setText(f"Last: {latency:.1f}s")

    # ==========================================================================
    # Sessions
    # ==========================================================================

    def refresh_session_list(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def new_session(self):
        self.chat_history = []
        self.current_session_file = None
        self.chat_display.clear()
        self.thought_display.clear()
        self.chat_display.append("<i>New session started.</i>")
        self._set_status("New session")

    def save_session(self):
        if not self.chat_history:
            return
        self.current_session_file = self.memory_manager.save_session(
            self.chat_history, self.system_prompt_input.toPlainText(), self.current_session_file
        )
        self.refresh_session_list()
        self._set_status(f"Saved: {self.current_session_file}")

    def load_session(self, item):
        filename = item.text()
        sys_prompt, history = self.memory_manager.load_session(filename)
        self.system_prompt_input.setPlainText(sys_prompt)
        self.chat_history = history
        self.current_session_file = filename
        self.chat_display.clear()
        self.thought_display.clear()
        self.chat_display.append(f"<i>Loaded: {filename}</i>")
        for msg in history:
            role, content = msg.get("role", ""), msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>You:</b> {content}")
            elif role == "assistant":
                if "<think>" in content and "</think>" in content:
                    thought = content.split("</think>")[0].replace("<think>", "").strip()
                    resp = content.split("</think>")[1].strip()
                    self.thought_display.append(f"<b>[Past]</b>\n{thought}\n")
                    self.chat_display.append(f"<b>Karl:</b> {resp}\n")
                else:
                    self.chat_display.append(f"<b>Karl:</b> {content}\n")
        self._set_status(f"Loaded: {filename}")

    def ingest_document(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "",
            "Supported (*.pdf *.docx *.txt *.py *.md *.csv);;All (*.*)"
        )
        if not filepath:
            return
        self._set_status("Ingesting...")
        chunks = self.rag_pipeline.ingest_file(filepath)
        filename = filepath.replace("\\", "/").split("/")[-1]
        if chunks > 0:
            self.kb_list.addItem(f"{filename} ({chunks} chunks)")
            self._set_status(f"Ingested {filename} ({chunks} chunks)")
        else:
            self._set_status(f"Failed to ingest {filename}")

    # ==========================================================================
    # Controls enabled/disabled
    # ==========================================================================

    def _set_controls(self, enabled: bool):
        self.user_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.force_thought_button.setEnabled(enabled)
        self.agentic_button.setEnabled(enabled)
        self.auto_loop_toggle.setEnabled(enabled)

    # ==========================================================================
    # Generation
    # ==========================================================================

    def force_thought(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self.thought_display.append(f"\n[INJECTED THOUGHT]\n{text}")
        self.chat_history.append({"role": "assistant", "content": f"<think>\n{text}\n</think>"})
        self._set_status("Thought injected into context")

    def send_message(self):
        import time as _t
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._last_user_msg = text
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_up_btn.setText("Accept")
        self.thumbs_down_btn.setText("Correct")
        self._set_controls(False)
        self.stop_agentic_button.setEnabled(self.auto_loop_toggle.isChecked())

        self.chat_display.append(f"<b>You:</b> {text}")
        self.chat_display.append("<b>Karl:</b> ")
        self.thought_display.append(f"\n--- {text[:60]} ---")
        self.chat_history.append({"role": "user", "content": text})

        wf = self._get_workflow()
        tpl = self._get_template()
        top_k = self.rag_topk_spin.value()
        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        rag_ctx = "\n\n".join(retrieved)

        if wf != "general_chat":
            sys_prompt = get_template(tpl, rag_context=rag_ctx)
        else:
            sys_prompt = self.system_prompt_input.toPlainText()
            if retrieved:
                sys_prompt += "\n\n# RELEVANT KNOWLEDGE:\n" + "".join(f"- {c}\n" for c in retrieved)

        self._last_workflow = wf
        self._last_template = tpl
        self._last_chunks_used = retrieved
        self._gen_start_time = _t.time()
        self._set_status("Generating...")

        self.thread = LLMThread(sys_prompt, self.chat_history, self._get_hyperparams(), retrieved)
        self.thread.new_thought_token.connect(self._on_thought_token)
        self.thread.new_chat_token.connect(self._on_chat_token)
        self.thread.new_raw_token.connect(lambda _: None)
        self.thread.generation_finished.connect(self._on_gen_done)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _on_thought_token(self, token):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.thought_display.setTextCursor(c)
        self.thought_display.ensureCursorVisible()

    def _on_chat_token(self, token):
        c = self.chat_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.chat_display.setTextCursor(c)
        self.chat_display.ensureCursorVisible()

    def _fire_generation(self, history_override=None, start_in_thought=False):
        sys_prompt = self.system_prompt_input.toPlainText()
        history = history_override if history_override is not None else self.chat_history
        self.thread = LLMThread(sys_prompt, history, self._get_hyperparams(),
                                start_in_thought=start_in_thought)
        self.thread.new_thought_token.connect(self._on_thought_token)
        self.thread.new_chat_token.connect(self._on_chat_token)
        self.thread.new_raw_token.connect(lambda _: None)
        self.thread.generation_finished.connect(self._on_gen_done)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _on_gen_done(self, final_thought, final_response, truncated=False, ended_in_thought=False):
        import time as _t
        self.chat_history.append({"role": "assistant", "content": final_response})
        self._last_response = final_response

        if truncated:
            self._on_thought_token("\n[continuing...]\n")
            cont = list(self.chat_history) + [{"role": "user", "content": "Continue."}]
            self._fire_generation(history_override=cont, start_in_thought=ended_in_thought)
            return

        self.chat_display.append("\n")
        self.thumbs_up_btn.setEnabled(bool(self._last_user_msg))
        self.thumbs_down_btn.setEnabled(bool(self._last_user_msg))

        latency = _t.time() - self._gen_start_time
        self._last_latency = latency
        self._update_report(self._last_workflow, self._last_template, self._last_chunks_used, latency)
        self._set_status(f"Done -- {latency:.1f}s")

        if self.auto_loop_toggle.isChecked():
            self.start_agentic_loop()
        else:
            self._set_controls(True)
            self.stop_agentic_button.setEnabled(False)
            self.user_input.setFocus()

    def _on_error(self, msg):
        self.chat_display.append(f"<br><font color='#EF4444'><b>Error:</b> {msg}</font><br>")
        self._set_controls(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText("Error")
        self.agentic_status.setStyleSheet("color: #EF4444; font-size: 10pt; background: transparent;")
        self._set_status(f"Error: {msg[:80]}")

    # ==========================================================================
    # Agentic Loop
    # ==========================================================================

    def start_agentic_loop(self):
        if not self.chat_history:
            self.chat_display.append(
                "<font color='#F59E0B'><i>Send a message first to seed the loop.</i></font>"
            )
            return
        self._set_controls(False)
        self.stop_agentic_button.setEnabled(True)
        self.agentic_status.setText("Running")
        self.agentic_status.setStyleSheet(
            "color: #22C55E; font-size: 10pt; background: transparent;"
        )
        self.thought_display.append(
            "\n" + "=" * 60 + "\n  AUTONOMOUS LOOP STARTED\n" + "=" * 60
        )
        self._set_status("Autonomous loop running...")

        self.agentic_thread = AgenticThread(
            self.system_prompt_input.toPlainText(),
            self.chat_history,
            self._get_hyperparams()
        )
        self.agentic_thread.new_thought_token.connect(self._on_thought_token)
        self.agentic_thread.new_chat_token.connect(self._on_chat_token)
        self.agentic_thread.new_raw_token.connect(lambda _: None)
        self.agentic_thread.iteration_finished.connect(self._on_agentic_iter)
        self.agentic_thread.loop_finished.connect(self._on_agentic_done)
        self.agentic_thread.error_occurred.connect(self._on_error)
        self.agentic_thread.start()

    def stop_agentic_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.auto_loop_toggle.setChecked(False)
        self.agentic_status.setText("Stopping")
        self.agentic_status.setStyleSheet(
            "color: #F59E0B; font-size: 10pt; background: transparent;"
        )
        self.stop_agentic_button.setEnabled(False)

    def _on_agentic_iter(self, iteration, thought, response):
        self.chat_history.append({"role": "assistant", "content": response})
        self.agentic_status.setText(f"Iteration {iteration + 1}")

    def _on_agentic_done(self, total):
        self._set_controls(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText("Done")
        self.agentic_status.setStyleSheet(
            "color: #3A3A3F; font-size: 10pt; background: transparent;"
        )
        self.chat_display.append(
            f"\n<i><font color='#22C55E'>Loop finished after {total} iteration(s).</font></i>\n"
        )
        self.user_input.setFocus()
        self._set_status(f"Loop complete -- {total} iteration(s)")

    # ==========================================================================
    # Training Curator
    # ==========================================================================

    def _rate_thumbs_up(self):
        if not self._last_user_msg or not self._last_response:
            return
        save_example(
            system_prompt=self.system_prompt_input.toPlainText(),
            user_msg=self._last_user_msg,
            good_response=self._last_response,
            source="thumbs_up"
        )
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_up_btn.setText("Saved")
        self._refresh_curator_stats()
        self._set_status("Training example saved (positive)")

    def _rate_thumbs_down(self):
        if not self._last_user_msg:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Correct this response")
        dialog.resize(660, 340)
        dl = QVBoxLayout(dialog)
        dl.setSpacing(12)
        dl.setContentsMargins(24, 24, 24, 20)
        dl.addWidget(QLabel(f"<b>Prompt:</b> {self._last_user_msg[:120]}"))
        dl.addWidget(QLabel("<b>Ideal response:</b>"))
        editor = QTextEdit()
        editor.setPlainText(self._last_response)
        dl.addWidget(editor)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        dl.addWidget(btns)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            corrected = editor.toPlainText().strip()
            if corrected:
                save_example(
                    system_prompt=self.system_prompt_input.toPlainText(),
                    user_msg=self._last_user_msg,
                    good_response=corrected,
                    source="corrected"
                )
                self.thumbs_up_btn.setEnabled(False)
                self.thumbs_down_btn.setEnabled(False)
                self.thumbs_down_btn.setText("Saved")
                self._refresh_curator_stats()

    def _refresh_curator_stats(self):
        try:
            s = get_stats()
            self.curator_stats_label.setText(
                f"Examples: {s['total']}  (Accepted: {s['thumbs_up']}  Corrected: {s['corrected']})"
            )
        except Exception:
            pass

    def _export_training_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Training Data",
            "data/training/export_unsloth.jsonl",
            "JSONL Files (*.jsonl)"
        )
        if path:
            out_path, count = export_unsloth(path)
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {count} examples to:\n{out_path}\n\n"
                "See training/qlora_config_template.yaml for the Unsloth config."
            )
