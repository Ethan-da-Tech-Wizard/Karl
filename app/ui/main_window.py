"""
Karl — Main Window  (UI v2)
===========================
Layout:   LEFT (Sessions + Knowledge Base)
        | CENTER (Raw Archive / Thought Stream / Chat + Input)
        | RIGHT (System Prompt / Workflow / Hyperparameters / Curator)

Every interactive widget carries a rich tooltip so the user always knows
what a control does without consulting external docs.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QSplitter,
    QTextEdit, QLabel, QDoubleSpinBox, QSpinBox, QGroupBox,
    QListWidget, QFileDialog, QCheckBox, QMessageBox, QDialog,
    QDialogButtonBox, QComboBox, QFrame, QStatusBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import save_example, get_stats, export_unsloth
from core.workflows import list_workflows, get_workflow
from core.prompt_templates import get_template, list_templates


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section_label(text: str) -> QLabel:
    """Returns a styled section-header label."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #71717A; font-size: 8pt; font-weight: bold; "
        "letter-spacing: 0.08em; text-transform: uppercase; "
        "padding: 10px 0 4px 0;"
    )
    return lbl


def _separator() -> QFrame:
    """Returns a 1-px horizontal divider."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet("color: #27272A; border: none; border-top: 1px solid #27272A; max-height: 1px;")
    return line


# ── Background threads ────────────────────────────────────────────────────────

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


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karl — LLM Introspection Environment")
        self.resize(1500, 900)
        self.setMinimumSize(1100, 680)

        # ── State ──────────────────────────────────────────────────────────────
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

        self._build_ui()
        self._build_status_bar()
        self.refresh_session_list()
        self._run_upgrade_check()
        self._refresh_curator_stats()

    # ══════════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([240, 850, 340])

    def _build_status_bar(self):
        """Bottom status bar — shows idle/generating state and latency."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #52525B; font-size: 8.5pt;")
        self.status_bar.addWidget(self._status_label)
        self._latency_label = QLabel("")
        self._latency_label.setStyleSheet("color: #3F3F46; font-size: 8.5pt;")
        self.status_bar.addPermanentWidget(self._latency_label)

    # ── LEFT PANEL ────────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(240)
        panel.setStyleSheet("background-color: #0F0F12; border-right: 1px solid #1E1E22;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)

        # ── Sessions ──────────────────────────────────────────────────────────
        layout.addWidget(_section_label("Sessions"))
        layout.addWidget(_separator())

        self.session_list = QListWidget()
        self.session_list.setToolTip(
            "<b>Saved Sessions</b><br>"
            "Each session stores your full conversation history and system prompt.<br>"
            "<b>Double-click</b> any session to reload it exactly as you left it.<br>"
            "Sessions are saved as JSON files in <code>data/sessions/</code>."
        )
        self.session_list.setMinimumHeight(120)
        self.session_list.itemDoubleClicked.connect(self.load_session)
        layout.addWidget(self.session_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_new = QPushButton("＋ New")
        self.btn_new.setToolTip(
            "<b>New Session</b><br>"
            "Clears the current conversation and starts a blank slate.<br>"
            "Your system prompt is preserved but chat history is wiped."
        )
        self.btn_new.clicked.connect(self.new_session)

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setToolTip(
            "<b>Save Session</b><br>"
            "Saves the current conversation to <code>data/sessions/</code> as a JSON file.<br>"
            "Saving to the same session file will overwrite it."
        )
        self.btn_save.clicked.connect(self.save_session)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        # ── Knowledge Base ────────────────────────────────────────────────────
        layout.addSpacing(12)
        layout.addWidget(_section_label("Knowledge Base (RAG)"))
        layout.addWidget(_separator())

        kb_info = QLabel(
            "Drop documents here to give Karl\n"
            "context it can retrieve during chat."
        )
        kb_info.setStyleSheet("color: #52525B; font-size: 8.5pt; padding: 0 0 4px 0;")
        kb_info.setWordWrap(True)
        layout.addWidget(kb_info)

        self.kb_list = QListWidget()
        self.kb_list.setToolTip(
            "<b>Ingested Documents</b><br>"
            "Files listed here have been chunked, embedded, and stored in a local FAISS vector index.<br>"
            "During each generation, Karl searches this index and injects the most relevant "
            "chunks into the system prompt automatically.<br>"
            "The index persists across restarts in <code>data/vector_db/</code>."
        )
        self.kb_list.setMinimumHeight(100)
        layout.addWidget(self.kb_list)

        self.btn_ingest = QPushButton("📄 Ingest Document")
        self.btn_ingest.setToolTip(
            "<b>Ingest Document</b><br>"
            "Loads a file (PDF, DOCX, TXT, PY, MD, CSV) into the local vector database.<br>"
            "The file is split into overlapping text chunks, embedded using "
            "<code>all-MiniLM-L6-v2</code>, and stored in a FAISS flat index.<br>"
            "Larger files produce more chunks and may slow retrieval slightly."
        )
        self.btn_ingest.clicked.connect(self.ingest_document)
        layout.addWidget(self.btn_ingest)

        layout.addStretch()
        return panel

    # ── CENTER PANEL ──────────────────────────────────────────────────────────

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_splitter.setChildrenCollapsible(False)
        layout.addWidget(center_splitter)

        center_splitter.addWidget(self._build_raw_panel())
        center_splitter.addWidget(self._build_thought_panel())
        center_splitter.addWidget(self._build_chat_panel())
        center_splitter.setSizes([0, 280, 520])

        return panel

    def _build_raw_panel(self) -> QWidget:
        """Raw Token Archive — hidden by default."""
        container = QWidget()
        container.setStyleSheet("background-color: #09090B; border-bottom: 1px solid #1E1E22;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("⬡  Raw Token Archive")
        title.setStyleSheet("color: #3F3F46; font-size: 8.5pt; font-weight: bold; letter-spacing: 0.05em;")
        title.setToolTip(
            "<b>Raw Token Archive</b><br>"
            "Shows every single token exactly as it leaves the model — <i>before</i> any parsing.<br>"
            "Useful for debugging prompt format issues or studying tokenization behaviour.<br>"
            "Each generation also writes a timestamped <code>.tokens</code> file to "
            "<code>data/logs/raw/</code> for offline analysis."
        )
        self.raw_toggle = QCheckBox("Show")
        self.raw_toggle.setToolTip(
            "<b>Toggle Raw Archive Panel</b><br>"
            "Shows or hides the low-level token stream below the Thought panel.<br>"
            "Hidden by default to reduce visual clutter."
        )
        self.raw_toggle.setChecked(False)
        self.raw_toggle.stateChanged.connect(self._toggle_raw_panel)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.raw_toggle)
        layout.addLayout(header)

        self.raw_display = QTextBrowser()
        self.raw_display.setStyleSheet(
            "background-color: #050508; color: #2A4A2A; "
            "font-family: 'Consolas', monospace; font-size: 8pt; "
            "border: none; border-radius: 0;"
        )
        self.raw_display.setVisible(False)
        self.raw_display.setMaximumHeight(120)
        layout.addWidget(self.raw_display)

        return container

    def _build_thought_panel(self) -> QWidget:
        """Diagnostic Lane — the model's live reasoning trace."""
        container = QWidget()
        container.setStyleSheet("background-color: #0D0D10; border-bottom: 1px solid #1E1E22;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("🔬  Diagnostic Lane")
        title.setStyleSheet("color: #6B7280; font-size: 9.5pt; font-weight: bold;")
        title.setToolTip(
            "<b>Diagnostic Lane — Reasoning Trace</b><br>"
            "Displays the model's internal chain-of-thought in real time.<br>"
            "DeepSeek-R1 wraps its reasoning inside <code>&lt;think&gt;</code> … <code>&lt;/think&gt;</code> tags. "
            "Karl intercepts these tokens as they stream and routes them here, <i>before</i> they reach "
            "the Final Response panel.<br><br>"
            "This is where you observe <i>how</i> the model arrives at its answer — the key differentiator "
            "versus opaque chat tools. Edit <code>core/cognitive_parser.py</code> to change parsing rules."
        )
        subtitle = QLabel("(model's internal reasoning — streamed live)")
        subtitle.setStyleSheet("color: #374151; font-size: 8pt; padding-left: 6px;")
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()
        layout.addLayout(header)

        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #0D1117; color: #6B7280; "
            "font-family: 'Consolas', monospace; font-size: 9pt; "
            "border: 1px solid #1E2733; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(self.thought_display)

        return container

    def _build_chat_panel(self) -> QWidget:
        """Final Response panel + input row + controls."""
        container = QWidget()
        container.setStyleSheet("background-color: #141417;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)

        # ── Response display ───────────────────────────────────────────────────
        resp_title = QLabel("💬  Final Response")
        resp_title.setStyleSheet("color: #E4E4E7; font-size: 10pt; font-weight: bold;")
        resp_title.setToolTip(
            "<b>Final Response Panel</b><br>"
            "Shows the model's cleaned answer — everything <i>after</i> the "
            "<code>&lt;/think&gt;</code> closing tag.<br>"
            "This is what gets stored in the conversation history and what you'd "
            "use in production. The raw <code>&lt;think&gt;</code> block is stripped out "
            "before it enters the chat history to keep context lean."
        )
        layout.addWidget(resp_title)

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet(
            "background-color: #18181B; color: #E4E4E7; "
            "font-family: 'Segoe UI', sans-serif; font-size: 10.5pt; "
            "border: 1px solid #27272A; border-radius: 6px; padding: 10px 12px;"
        )
        layout.addWidget(self.chat_display)

        # ── Input row ─────────────────────────────────────────────────────────
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your prompt here…")
        self.user_input.setToolTip(
            "<b>Prompt Input</b><br>"
            "Type your message here and press <b>Enter</b> or click <b>Generate</b>.<br>"
            "You can also type a fake thought here and click <b>Force Thought</b> to "
            "inject it directly into the reasoning context."
        )
        self.user_input.returnPressed.connect(self.send_message)

        self.force_thought_button = QPushButton("🧠 Force Thought")
        self.force_thought_button.setObjectName("btn_force_thought")
        self.force_thought_button.setToolTip(
            "<b>Force Thought</b><br>"
            "Takes whatever text is in the prompt box and injects it into the conversation "
            "history as a <code>&lt;think&gt;…&lt;/think&gt;</code> block attributed to the assistant.<br><br>"
            "This allows you to <i>plant a fake reasoning step</i> and then observe how the model "
            "continues from that seeded premise — a core technique for cognitive manipulation experiments."
        )
        self.force_thought_button.clicked.connect(self.force_thought)

        self.send_button = QPushButton("▶  Generate")
        self.send_button.setObjectName("btn_generate")
        self.send_button.setToolTip(
            "<b>Generate</b><br>"
            "Sends your prompt to the model and begins streaming the response.<br>"
            "The Diagnostic Lane fills with reasoning tokens first; "
            "the Final Response panel fills with the cleaned answer.<br>"
            "If <b>Auto-Loop</b> is enabled, generation feeds directly into the Agentic Loop."
        )
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.user_input)
        input_row.addWidget(self.force_thought_button)
        input_row.addWidget(self.send_button)
        layout.addLayout(input_row)

        # ── Workflow report ────────────────────────────────────────────────────
        report_header = QHBoxLayout()
        self.report_toggle = QCheckBox("Show Workflow Report")
        self.report_toggle.setChecked(True)
        self.report_toggle.setToolTip(
            "<b>Workflow Report</b><br>"
            "After each generation, displays a one-line diagnostic summary:<br>"
            "• <b>workflow</b> — which mode was active<br>"
            "• <b>template</b> — which prompt template was used<br>"
            "• <b>rag_chunks</b> — how many knowledge-base chunks were retrieved<br>"
            "• <b>latency</b> — wall-clock generation time in seconds"
        )
        self.report_toggle.stateChanged.connect(self._toggle_report_panel)
        report_header.addWidget(self.report_toggle)
        report_header.addStretch()
        layout.addLayout(report_header)

        self.report_display = QTextBrowser()
        self.report_display.setMaximumHeight(52)
        self.report_display.setStyleSheet(
            "background-color: #09090B; color: #4ADE80; "
            "font-family: 'Consolas', monospace; font-size: 8pt; "
            "border: 1px solid #14532D; border-radius: 4px; padding: 6px 8px;"
        )
        self.report_display.setPlaceholderText("Workflow report will appear here after each generation.")
        layout.addWidget(self.report_display)

        # ── Rating row ────────────────────────────────────────────────────────
        rating_row = QHBoxLayout()
        rating_row.setSpacing(8)
        rating_lbl = QLabel("Rate this response:")
        rating_lbl.setStyleSheet("color: #52525B; font-size: 9pt;")
        rating_lbl.setToolTip(
            "<b>Response Rating</b><br>"
            "Use these buttons to curate training data for future fine-tuning.<br>"
            "👍 saves the (prompt → response) pair as a <i>good example</i>.<br>"
            "✏️ opens an editor so you can write the correct response — "
            "that corrected pair is saved as a <i>fixed example</i>.<br>"
            "All data is stored in <code>data/training/curated.jsonl</code>."
        )

        self.thumbs_up_btn = QPushButton("👍  Good")
        self.thumbs_up_btn.setObjectName("btn_thumbs_up")
        self.thumbs_up_btn.setToolTip(
            "<b>Mark as Good</b><br>"
            "Saves the current (prompt, response) pair to the training curator as a "
            "positive example. Use when the model's answer was exactly what you wanted."
        )
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_up_btn.clicked.connect(self._rate_thumbs_up)

        self.thumbs_down_btn = QPushButton("✏️  Fix")
        self.thumbs_down_btn.setObjectName("btn_thumbs_down")
        self.thumbs_down_btn.setToolTip(
            "<b>Correct & Save</b><br>"
            "Opens a dialog pre-filled with the model's response.<br>"
            "Edit it to the ideal answer, then click Save — the corrected pair is stored "
            "in the training curator for supervised fine-tuning."
        )
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_down_btn.clicked.connect(self._rate_thumbs_down)

        rating_row.addWidget(rating_lbl)
        rating_row.addWidget(self.thumbs_up_btn)
        rating_row.addWidget(self.thumbs_down_btn)
        rating_row.addStretch()
        layout.addLayout(rating_row)

        # ── Agentic controls ──────────────────────────────────────────────────
        layout.addWidget(_separator())
        agentic_row = QHBoxLayout()
        agentic_row.setSpacing(8)

        self.auto_loop_toggle = QCheckBox("Auto-Loop")
        self.auto_loop_toggle.setToolTip(
            "<b>Auto-Loop Mode</b><br>"
            "When ON, each completed generation automatically feeds back into the Agentic Loop "
            "without any user input.<br>"
            "The loop continues until the stop condition in <code>core/agentic_loop.py</code> "
            "returns <code>False</code>, or until you click <b>Stop</b>.<br>"
            "The Generate button label changes to <b>Send + Loop</b> as a reminder."
        )
        self.auto_loop_toggle.stateChanged.connect(self._on_auto_loop_toggled)

        self.agentic_button = QPushButton("▶▶  Run Agentic Loop")
        self.agentic_button.setObjectName("btn_agentic")
        self.agentic_button.setToolTip(
            "<b>Run Agentic Loop</b><br>"
            "Starts the autonomous self-iteration loop on the current conversation.<br>"
            "Karl will repeatedly generate, evaluate its own output, and inject a new "
            "prompt turn — all driven by <code>core/agentic_loop.py</code>.<br><br>"
            "<b>How to customise:</b> edit <code>should_continue()</code> to control the stop "
            "condition, and <code>build_next_prompt()</code> to control what Karl says to itself "
            "between iterations. Both functions are hot-reloaded between iterations — "
            "no restart needed."
        )
        self.agentic_button.clicked.connect(self.start_agentic_loop)

        self.stop_agentic_button = QPushButton("■  Stop")
        self.stop_agentic_button.setObjectName("btn_stop")
        self.stop_agentic_button.setToolTip(
            "<b>Stop Agentic Loop</b><br>"
            "Sends a stop signal to the running agentic thread.<br>"
            "The current generation finishes first; the loop then exits cleanly."
        )
        self.stop_agentic_button.setEnabled(False)
        self.stop_agentic_button.clicked.connect(self.stop_agentic_loop)

        self.agentic_status = QLabel("Agentic: Idle")
        self.agentic_status.setStyleSheet("color: #3F3F46; font-size: 9pt; padding-left: 4px;")
        self.agentic_status.setToolTip(
            "<b>Agentic Loop Status</b><br>"
            "Shows the current state of the autonomous loop:<br>"
            "• <b>Idle</b> — no loop running<br>"
            "• <b>Running…</b> — actively generating<br>"
            "• <b>Iteration N done</b> — just finished an iteration<br>"
            "• <b>Done (N iterations)</b> — loop completed normally<br>"
            "• <b>Stopping…</b> — stop was requested, awaiting clean exit"
        )

        agentic_row.addWidget(self.auto_loop_toggle)
        agentic_row.addWidget(self.agentic_button)
        agentic_row.addWidget(self.stop_agentic_button)
        agentic_row.addWidget(self.agentic_status)
        agentic_row.addStretch()
        layout.addLayout(agentic_row)

        return container

    # ── RIGHT PANEL ───────────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(340)
        panel.setStyleSheet("background-color: #0F0F12; border-left: 1px solid #1E1E22;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 16, 14, 12)
        layout.setSpacing(6)

        # ── System Prompt ─────────────────────────────────────────────────────
        layout.addWidget(_section_label("System Prompt"))
        layout.addWidget(_separator())

        sys_info = QLabel("Defines the model's persona and rules for every turn.")
        sys_info.setStyleSheet("color: #52525B; font-size: 8.5pt; padding-bottom: 4px;")
        sys_info.setWordWrap(True)
        layout.addWidget(sys_info)

        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlainText(
            "You are a precise, analytical AI assistant.\n"
            "When reasoning inside <think> blocks: be direct, avoid repeating 'Wait' or 'But wait', "
            "and do not re-state conclusions you have already reached.\n"
            "Your final answer after </think> should be clean and concise."
        )
        self.system_prompt_input.setMaximumHeight(160)
        self.system_prompt_input.setToolTip(
            "<b>System Prompt</b><br>"
            "This text is prepended to <i>every</i> generation as the <code>&lt;|im_start|&gt;system</code> turn.<br>"
            "It sets the model's persona, rules, and response style.<br><br>"
            "Tips for DeepSeek-R1:<br>"
            "• Keep it concise — the model's <code>&lt;think&gt;</code> block handles reasoning detail<br>"
            "• Avoid micromanaging the chain-of-thought; the model handles that internally<br>"
            "• If using a Workflow mode, the template overrides this field automatically<br><br>"
            "This field is hot-editable — changes take effect on the very next generation."
        )
        layout.addWidget(self.system_prompt_input)

        # ── Workflow Mode ─────────────────────────────────────────────────────
        layout.addSpacing(6)
        layout.addWidget(_section_label("Workflow & Template"))
        layout.addWidget(_separator())

        wf_info = QLabel(
            "Workflows bundle a template, RAG settings, and an output schema "
            "into a single named mode."
        )
        wf_info.setStyleSheet("color: #52525B; font-size: 8.5pt; padding-bottom: 4px;")
        wf_info.setWordWrap(True)
        layout.addWidget(wf_info)

        wf_row = QHBoxLayout()
        wf_lbl = QLabel("Workflow:")
        wf_lbl.setToolTip(
            "<b>Workflow Mode</b><br>"
            "Selects a preset operating mode for Karl.<br><br>"
            "• <b>General Chat</b> — open conversation, thought stream visible<br>"
            "• <b>Document Extractor</b> — extracts structured JSON from ingested docs (RAG required)<br>"
            "• <b>Grounded Answer</b> — refuses to answer unless evidence is in retrieved context<br>"
            "• <b>Code Review</b> — returns a JSON array of code issues (severity, location, suggestion)<br><br>"
            "Changing workflow auto-selects the matching prompt template and RAG top-k."
        )
        self.workflow_combo = QComboBox()
        for wf_name, wf_label in list_workflows():
            self.workflow_combo.addItem(wf_label, wf_name)
        self.workflow_combo.setToolTip(wf_lbl.toolTip())
        self.workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        wf_row.addWidget(wf_lbl)
        wf_row.addWidget(self.workflow_combo, 1)
        layout.addLayout(wf_row)

        tpl_row = QHBoxLayout()
        tpl_lbl = QLabel("Template:")
        tpl_lbl.setToolTip(
            "<b>Prompt Template</b><br>"
            "Chooses the system-prompt template that wraps each generation.<br>"
            "Templates live in <code>core/prompt_templates.py</code> — add your own there.<br><br>"
            "• <b>reasoning_minimal</b> — lean prompt for reasoning models (DeepSeek-R1)<br>"
            "• <b>gpt_structured</b> — structured sections with explicit RAG context injection<br>"
            "• <b>json_extractor</b> — schema-first extraction, output must be valid JSON<br>"
            "• <b>grounded_answer</b> — refuses to answer if evidence is not in context<br>"
            "• <b>code_review</b> — returns a JSON array of findings<br><br>"
            "Hot-reloaded on every generation — edit the file and the next click picks it up."
        )
        self.template_combo = QComboBox()
        for tpl in list_templates():
            self.template_combo.addItem(tpl)
        self.template_combo.setToolTip(tpl_lbl.toolTip())
        tpl_row.addWidget(tpl_lbl)
        tpl_row.addWidget(self.template_combo, 1)
        layout.addLayout(tpl_row)

        rag_row = QHBoxLayout()
        rag_lbl = QLabel("RAG top-k:")
        rag_lbl.setToolTip(
            "<b>RAG Top-K</b><br>"
            "Number of knowledge-base chunks to retrieve and inject into the prompt.<br>"
            "Set to <b>0</b> to disable retrieval entirely for this generation.<br>"
            "Higher values give the model more context but increase token usage and latency.<br>"
            "Recommended: 3–5 for most tasks."
        )
        self.rag_topk_spin = QSpinBox()
        self.rag_topk_spin.setRange(0, 10)
        self.rag_topk_spin.setValue(3)
        self.rag_topk_spin.setToolTip(rag_lbl.toolTip())
        rag_row.addWidget(rag_lbl)
        rag_row.addWidget(self.rag_topk_spin)
        rag_row.addStretch()
        layout.addLayout(rag_row)

        self.ctx_headers_check = QCheckBox("Contextual chunk headers")
        self.ctx_headers_check.setToolTip(
            "<b>Contextual Chunk Headers</b><br>"
            "When ON, each retrieved chunk is prefixed with:<br>"
            "<code>[Source: filename | Chunk N]</code><br>"
            "This helps the model cite which document a fact came from and improves "
            "grounded-answer accuracy. Slightly increases token count per chunk."
        )
        self.ctx_headers_check.stateChanged.connect(self._on_headers_toggled)
        layout.addWidget(self.ctx_headers_check)

        # ── Hyperparameters ───────────────────────────────────────────────────
        layout.addSpacing(6)
        layout.addWidget(_section_label("Generation Hyperparameters"))
        layout.addWidget(_separator())

        temp_row = QHBoxLayout()
        temp_lbl = QLabel("Temperature:")
        temp_lbl.setToolTip(
            "<b>Temperature</b><br>"
            "Controls the randomness of the model's output distribution.<br>"
            "• <b>0.0</b> — fully deterministic (always picks the highest-probability token)<br>"
            "• <b>0.7</b> — balanced creativity and coherence (recommended default)<br>"
            "• <b>1.5+</b> — very creative / chaotic, may produce nonsense<br><br>"
            "For reasoning models like DeepSeek-R1, values between 0.5–0.8 work well."
        )
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setValue(0.7)
        self.temp_spin.setToolTip(temp_lbl.toolTip())
        temp_row.addWidget(temp_lbl)
        temp_row.addWidget(self.temp_spin)
        temp_row.addStretch()
        layout.addLayout(temp_row)

        top_p_row = QHBoxLayout()
        top_p_lbl = QLabel("Top-P:")
        top_p_lbl.setToolTip(
            "<b>Top-P (Nucleus Sampling)</b><br>"
            "Only tokens whose cumulative probability reaches <i>P</i> are considered.<br>"
            "• <b>1.0</b> — considers the full vocabulary (no filtering)<br>"
            "• <b>0.95</b> — trims the long tail of improbable tokens (recommended)<br>"
            "• <b>0.5</b> — very conservative, sticks to likely tokens<br><br>"
            "Used together with Temperature. Lowering both makes outputs more focused."
        )
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        self.top_p_spin.setToolTip(top_p_lbl.toolTip())
        top_p_row.addWidget(top_p_lbl)
        top_p_row.addWidget(self.top_p_spin)
        top_p_row.addStretch()
        layout.addLayout(top_p_row)

        tok_row = QHBoxLayout()
        tok_lbl = QLabel("Max Tokens:")
        tok_lbl.setToolTip(
            "<b>Max New Tokens</b><br>"
            "Hard cap on how many tokens the model generates per turn.<br>"
            "• <b>512</b> — default, good for most short answers<br>"
            "• <b>1024–2048</b> — needed for long analyses or code generation<br>"
            "• <b>4096</b> — maximum for the current context window<br><br>"
            "If the model hits this limit mid-generation, Karl automatically chains "
            "a continuation request ('Continue.') to complete the response."
        )
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1, 4096)
        self.tokens_spin.setValue(512)
        self.tokens_spin.setToolTip(tok_lbl.toolTip())
        tok_row.addWidget(tok_lbl)
        tok_row.addWidget(self.tokens_spin)
        tok_row.addStretch()
        layout.addLayout(tok_row)

        # ── Upgrade area ──────────────────────────────────────────────────────
        self.upgrade_label = QLabel("")
        self.upgrade_label.setWordWrap(True)
        self.upgrade_label.setStyleSheet("color: #93C5FD; font-size: 8.5pt; padding: 6px 0;")
        self.upgrade_label.setVisible(False)
        layout.addWidget(self.upgrade_label)

        self.upgrade_button = QPushButton("⬆  Upgrade Model")
        self.upgrade_button.setToolTip(
            "<b>Upgrade Model</b><br>"
            "Karl detected that your hardware can run a larger, higher-quality model.<br>"
            "Clicking this will download the new GGUF file, swap it in, and push the "
            "updated <code>data/active_model.json</code> to GitHub automatically.<br>"
            "Restart Karl after the upgrade to load the new model."
        )
        self.upgrade_button.setVisible(False)
        self.upgrade_button.clicked.connect(self._confirm_upgrade)
        layout.addWidget(self.upgrade_button)

        # ── Training Data Curator ─────────────────────────────────────────────
        layout.addSpacing(6)
        layout.addWidget(_section_label("Training Data Curator"))
        layout.addWidget(_separator())

        curator_info = QLabel(
            "Rate responses with 👍/✏️ above to build a fine-tuning dataset."
        )
        curator_info.setStyleSheet("color: #52525B; font-size: 8.5pt; padding-bottom: 4px;")
        curator_info.setWordWrap(True)
        layout.addWidget(curator_info)

        self.curator_stats_label = QLabel("Examples: 0  (👍 0  ✏️ 0)")
        self.curator_stats_label.setStyleSheet("font-size: 9pt; color: #71717A;")
        self.curator_stats_label.setToolTip(
            "<b>Curator Statistics</b><br>"
            "Shows how many training examples have been collected this session.<br>"
            "• 👍 = positive examples (model got it right)<br>"
            "• ✏️ = corrected examples (you wrote the ideal answer)<br>"
            "Data lives in <code>data/training/curated.jsonl</code>."
        )
        layout.addWidget(self.curator_stats_label)

        export_btn = QPushButton("📦  Export for Unsloth")
        export_btn.setToolTip(
            "<b>Export Training Data</b><br>"
            "Writes all curated (prompt → response) pairs to a JSONL file formatted "
            "for <b>Unsloth</b> supervised fine-tuning.<br>"
            "The output file can be fed directly to a QLoRA training run "
            "using the template in <code>training/qlora_config_template.yaml</code>.<br>"
            "See <code>training/WHEN_TO_TUNE.md</code> for guidance on when tuning is worthwhile."
        )
        export_btn.clicked.connect(self._export_training_data)
        layout.addWidget(export_btn)

        # ── Hackable core hint ────────────────────────────────────────────────
        layout.addSpacing(8)
        hint = QLabel(
            "💡 <b>Hackable Core</b><br>"
            "Edit these files freely — Karl hot-reloads them on every generation:<br>"
            "<code>core/interaction_loop.py</code> — prompt builder<br>"
            "<code>core/agentic_loop.py</code> — loop stop condition<br>"
            "<code>core/prompt_templates.py</code> — add new templates<br>"
            "<code>core/workflows.py</code> — add new workflow modes"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: #3F3F46; font-size: 8pt; padding: 8px; "
            "background-color: #09090B; border-radius: 6px; "
            "border: 1px solid #18181B; line-height: 1.6;"
        )
        hint.setToolTip(
            "<b>The Hackable Core</b><br>"
            "Karl is designed so that prompt engineers can modify the generation pipeline "
            "without restarting the app.<br>"
            "The files listed here are reloaded via <code>importlib.reload()</code> before "
            "every generation — just save the file and click Generate."
        )
        layout.addWidget(hint)

        layout.addStretch()
        return panel

    # ══════════════════════════════════════════════════════════════════════════
    # Upgrade (M8 + M10)
    # ══════════════════════════════════════════════════════════════════════════

    def _run_upgrade_check(self):
        self._upgrade_check_thread = UpgradeCheckThread()
        self._upgrade_check_thread.upgrade_available.connect(self._on_upgrade_available)
        self._upgrade_check_thread.no_upgrade.connect(lambda: self._set_status("Ready"))
        self._upgrade_check_thread.start()

    def _on_upgrade_available(self, entry, profile):
        self._pending_upgrade_entry = entry
        self.upgrade_label.setText(
            f"Hardware upgrade available!\n"
            f"RAM: {profile['ram_gb']} GB | VRAM: {profile['vram_gb']} GB\n"
            f"→ {entry['name']} (Tier {entry['tier']})"
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
            self.upgrade_label.setText("Downloading… this may take several minutes.")
            self._dl_thread = UpgradeDownloadThread(self._pending_upgrade_entry)
            self._dl_thread.finished.connect(self._on_upgrade_complete)
            self._dl_thread.error.connect(self._on_upgrade_error)
            self._dl_thread.start()

    def _on_upgrade_complete(self, path):
        self.upgrade_label.setText(f"✅ Upgraded! Restart Karl to use the new model.\n({path})")
        self.upgrade_button.setVisible(False)
        self._set_status("Upgrade complete — restart to apply")

    def _on_upgrade_error(self, msg):
        self.upgrade_label.setText(f"❌ Upgrade failed: {msg}")
        self.upgrade_button.setEnabled(True)
        self._set_status("Upgrade failed")

    # ══════════════════════════════════════════════════════════════════════════
    # Panel toggles
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_raw_panel(self, state):
        self.raw_display.setVisible(bool(state))

    def _toggle_report_panel(self, state):
        self.report_display.setVisible(bool(state))

    # ══════════════════════════════════════════════════════════════════════════
    # Workflow / Template handlers
    # ══════════════════════════════════════════════════════════════════════════

    def _on_workflow_changed(self, index):
        wf_name = self.workflow_combo.itemData(index)
        try:
            wf_cfg = get_workflow(wf_name)
            default_tpl = wf_cfg.get("template", "reasoning_minimal")
            for i in range(self.template_combo.count()):
                if self.template_combo.itemText(i) == default_tpl:
                    self.template_combo.setCurrentIndex(i)
                    break
            self.rag_topk_spin.setValue(wf_cfg.get("rag_top_k", 3))
        except KeyError:
            pass

    def _on_headers_toggled(self, state):
        self.rag_pipeline.contextual_headers = bool(state)

    def _get_current_workflow_name(self) -> str:
        idx = self.workflow_combo.currentIndex()
        return self.workflow_combo.itemData(idx) or "general_chat"

    def _get_current_template_name(self) -> str:
        return self.template_combo.currentText() or "reasoning_minimal"

    def _update_report_panel(self, workflow, template, chunks, latency, status=""):
        chunk_count = len(chunks)
        sources = list({
            c.split("]")[0].replace("[Source: ", "")
            for c in chunks if "[Source:" in c
        })
        source_str = ", ".join(sources) if sources else f"{chunk_count} chunk(s)"
        msg = (
            f"workflow={workflow}  template={template}  "
            f"rag_chunks={chunk_count}  "
            f"{'sources=[' + source_str + ']  ' if chunk_count else ''}"
            f"latency={latency:.1f}s  {status}"
        )
        self.report_display.setPlainText(msg)
        self._latency_label.setText(f"Last generation: {latency:.1f}s")

    def _on_auto_loop_toggled(self, state):
        self.send_button.setText("▶▶  Send + Loop" if state else "▶  Generate")

    # ══════════════════════════════════════════════════════════════════════════
    # Status helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, text: str):
        self._status_label.setText(text)

    # ══════════════════════════════════════════════════════════════════════════
    # Sessions
    # ══════════════════════════════════════════════════════════════════════════

    def refresh_session_list(self):
        self.session_list.clear()
        for f in self.memory_manager.list_sessions():
            self.session_list.addItem(f)

    def new_session(self):
        self.chat_history = []
        self.current_session_file = None
        self.chat_display.clear()
        self.thought_display.clear()
        self.raw_display.clear()
        self.chat_display.append("<i>Started new session.</i>")
        self._set_status("New session started")

    def save_session(self):
        if not self.chat_history:
            return
        sys_prompt = self.system_prompt_input.toPlainText()
        self.current_session_file = self.memory_manager.save_session(
            self.chat_history, sys_prompt, self.current_session_file
        )
        self.refresh_session_list()
        self.chat_display.append(f"<i>Session saved as {self.current_session_file}</i>")
        self._set_status(f"Session saved: {self.current_session_file}")

    def load_session(self, item):
        filename = item.text()
        sys_prompt, history = self.memory_manager.load_session(filename)
        self.system_prompt_input.setPlainText(sys_prompt)
        self.chat_history = history
        self.current_session_file = filename
        self.chat_display.clear()
        self.thought_display.clear()
        self.raw_display.clear()
        self.chat_display.append(f"<i>Loaded session: {filename}</i>")
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>You:</b> {content}")
            elif role == "assistant":
                if "<think>" in content and "</think>" in content:
                    thought = content.split("</think>")[0].replace("<think>", "").strip()
                    resp = content.split("</think>")[1].strip()
                    self.thought_display.append(f"<b>[Past Thought]</b>\n{thought}\n")
                    self.chat_display.append(f"<b>Karl:</b> {resp}\n")
                else:
                    self.chat_display.append(f"<b>Karl:</b> {content}\n")
        self._set_status(f"Session loaded: {filename}")

    def ingest_document(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Document to Ingest", "",
            "Supported Files (*.pdf *.docx *.txt *.py *.md *.csv);;All Files (*.*)"
        )
        if filepath:
            self.chat_display.append(f"<i>Ingesting {filepath}…</i>")
            self._set_status(f"Ingesting {filepath.split('/')[-1]}…")
            chunks = self.rag_pipeline.ingest_file(filepath)
            filename = filepath.replace("\\", "/").split("/")[-1]
            if chunks > 0:
                self.kb_list.addItem(f"{filename} ({chunks} chunks)")
                self.chat_display.append(f"<i>✅ Added <b>{filename}</b> — {chunks} chunks indexed.</i>")
                self._set_status(f"Ingested {filename} ({chunks} chunks)")
            else:
                self.chat_display.append(
                    f"<i><font color='#EF4444'>Could not read {filename}.</font></i>"
                )
                self._set_status(f"Failed to ingest {filename}")

    # ══════════════════════════════════════════════════════════════════════════
    # Generation helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _get_hyperparams(self) -> dict:
        return {
            "temperature": self.temp_spin.value(),
            "top_p": self.top_p_spin.value(),
            "max_tokens": self.tokens_spin.value(),
        }

    def _set_controls_enabled(self, enabled: bool):
        self.user_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.force_thought_button.setEnabled(enabled)
        self.btn_ingest.setEnabled(enabled)
        self.agentic_button.setEnabled(enabled)
        self.auto_loop_toggle.setEnabled(enabled)

    def force_thought(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self.thought_display.append(f"\n<b>[FORCED THOUGHT]</b>\n{text}")
        self.chat_history.append({"role": "assistant", "content": f"<think>\n{text}\n</think>"})
        self._set_status("Forced thought injected into context")

    # ══════════════════════════════════════════════════════════════════════════
    # Single generation
    # ══════════════════════════════════════════════════════════════════════════

    def send_message(self):
        import time as _time
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._last_user_msg = text
        self.thumbs_up_btn.setEnabled(False)
        self.thumbs_down_btn.setEnabled(False)
        self.thumbs_up_btn.setText("👍  Good")
        self.thumbs_down_btn.setText("✏️  Fix")
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(self.auto_loop_toggle.isChecked())

        self.chat_display.append(f"<b>You:</b> {text}")
        self.chat_display.append("<b>Karl:</b> ")
        self.thought_display.append(f"\n─── Generation: '{text[:40]}…' ───")

        self.chat_history.append({"role": "user", "content": text})

        wf_name = self._get_current_workflow_name()
        tpl_name = self._get_current_template_name()
        top_k = self.rag_topk_spin.value()

        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        rag_context = "\n\n".join(retrieved) if retrieved else ""

        if wf_name != "general_chat":
            sys_prompt = get_template(tpl_name, rag_context=rag_context)
        else:
            sys_prompt = self.system_prompt_input.toPlainText()
            if retrieved:
                sys_prompt += "\n\n# RELEVANT KNOWLEDGE:\n" + "".join(f"- {c}\n" for c in retrieved)

        self._last_workflow = wf_name
        self._last_template = tpl_name
        self._last_chunks_used = retrieved
        self._gen_start_time = _time.time()

        self._set_status("Generating…")

        self.thread = LLMThread(sys_prompt, self.chat_history, self._get_hyperparams(), retrieved)
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
        self.thread.error_occurred.connect(self.handle_error)
        self.thread.start()

    def handle_thought_token(self, token):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.thought_display.setTextCursor(c)

    def handle_chat_token(self, token):
        c = self.chat_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(token)
        self.chat_display.setTextCursor(c)

    def handle_raw_token(self, token):
        if self.raw_display.isVisible():
            c = self.raw_display.textCursor()
            c.movePosition(c.MoveOperation.End)
            c.insertText(token)
            self.raw_display.setTextCursor(c)

    def _fire_generation(self, history_override=None, start_in_thought=False):
        sys_prompt = self.system_prompt_input.toPlainText()
        history = history_override if history_override is not None else self.chat_history
        self.thread = LLMThread(
            sys_prompt, history, self._get_hyperparams(),
            start_in_thought=start_in_thought
        )
        self.thread.new_thought_token.connect(self.handle_thought_token)
        self.thread.new_chat_token.connect(self.handle_chat_token)
        self.thread.new_raw_token.connect(self.handle_raw_token)
        self.thread.generation_finished.connect(self.handle_generation_finished)
        self.thread.error_occurred.connect(self.handle_error)
        self.thread.start()

    def handle_generation_finished(self, final_thought, final_response, truncated=False, ended_in_thought=False):
        import time as _time
        self.chat_history.append({"role": "assistant", "content": final_response})
        self._last_response = final_response

        if truncated:
            self.new_thought_token_direct("\n[↻ continuing…]\n")
            continuation_history = list(self.chat_history) + [
                {"role": "user", "content": "Continue."}
            ]
            self._fire_generation(
                history_override=continuation_history,
                start_in_thought=ended_in_thought
            )
            return

        self.chat_display.append("\n")
        self.thumbs_up_btn.setEnabled(bool(self._last_user_msg))
        self.thumbs_down_btn.setEnabled(bool(self._last_user_msg))

        latency = _time.time() - self._gen_start_time
        self._last_latency = latency
        self._update_report_panel(
            workflow=self._last_workflow,
            template=self._last_template,
            chunks=self._last_chunks_used,
            latency=latency,
        )
        self._set_status(f"Done — {latency:.1f}s")

        if self.auto_loop_toggle.isChecked():
            self.start_agentic_loop()
        else:
            self._set_controls_enabled(True)
            self.stop_agentic_button.setEnabled(False)
            self.user_input.setFocus()

    def new_thought_token_direct(self, text):
        c = self.thought_display.textCursor()
        c.movePosition(c.MoveOperation.End)
        c.insertText(text)
        self.thought_display.setTextCursor(c)

    def handle_error(self, msg):
        self.chat_display.append(f"<br><font color='#EF4444'><b>Error:</b> {msg}</font><br>")
        self._set_controls_enabled(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText("Agentic: Error")
        self._set_status(f"Error: {msg[:60]}")

    # ══════════════════════════════════════════════════════════════════════════
    # Agentic Loop
    # ══════════════════════════════════════════════════════════════════════════

    def start_agentic_loop(self):
        if not self.chat_history:
            self.chat_display.append(
                "<font color='#F59E0B'><i>Send a message first to seed the loop.</i></font>"
            )
            return
        self._set_controls_enabled(False)
        self.stop_agentic_button.setEnabled(True)
        self.agentic_status.setText("Agentic: Running…")
        self.agentic_status.setStyleSheet("color: #4ADE80; font-size: 9pt; padding-left: 4px;")
        self.thought_display.append(
            "\n" + "═" * 50 + "\n  AGENTIC LOOP STARTED\n" + "═" * 50
        )
        self._set_status("Agentic loop running…")

        self.agentic_thread = AgenticThread(
            self.system_prompt_input.toPlainText(),
            self.chat_history,
            self._get_hyperparams()
        )
        self.agentic_thread.new_thought_token.connect(self.handle_thought_token)
        self.agentic_thread.new_chat_token.connect(self.handle_chat_token)
        self.agentic_thread.new_raw_token.connect(self.handle_raw_token)
        self.agentic_thread.iteration_finished.connect(self.handle_agentic_iteration)
        self.agentic_thread.loop_finished.connect(self.handle_agentic_finished)
        self.agentic_thread.error_occurred.connect(self.handle_error)
        self.agentic_thread.start()

    def stop_agentic_loop(self):
        if self.agentic_thread:
            self.agentic_thread.request_stop()
        self.auto_loop_toggle.setChecked(False)
        self.agentic_status.setText("Agentic: Stopping…")
        self.agentic_status.setStyleSheet("color: #F59E0B; font-size: 9pt; padding-left: 4px;")
        self.stop_agentic_button.setEnabled(False)
        self._set_status("Stopping agentic loop…")

    def handle_agentic_iteration(self, iteration, thought, response):
        self.chat_history.append({"role": "assistant", "content": response})
        self.agentic_status.setText(f"Agentic: Iteration {iteration + 1} done")

    def handle_agentic_finished(self, total):
        self._set_controls_enabled(True)
        self.stop_agentic_button.setEnabled(False)
        self.agentic_status.setText(f"Agentic: Done ({total} iterations)")
        self.agentic_status.setStyleSheet("color: #52525B; font-size: 9pt; padding-left: 4px;")
        self.chat_display.append(
            f"\n<i><font color='#4ADE80'>— Agentic loop finished after {total} iteration(s) —</font></i>\n"
        )
        self.user_input.setFocus()
        self._set_status(f"Agentic loop done — {total} iteration(s)")

    # ══════════════════════════════════════════════════════════════════════════
    # Training Data Curator (M11)
    # ══════════════════════════════════════════════════════════════════════════

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
        self.thumbs_up_btn.setText("✅ Saved")
        self._refresh_curator_stats()
        self._set_status("Training example saved (positive)")

    def _rate_thumbs_down(self):
        if not self._last_user_msg:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Correct this response")
        dialog.resize(640, 320)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        prompt_lbl = QLabel(f"<b>Your prompt:</b> {self._last_user_msg[:120]}")
        prompt_lbl.setWordWrap(True)
        layout.addWidget(prompt_lbl)

        layout.addWidget(QLabel("<b>Write the ideal response:</b>"))
        editor = QTextEdit()
        editor.setPlaceholderText("Type the ideal response here…")
        editor.setPlainText(self._last_response)
        layout.addWidget(editor)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)

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
                self.thumbs_down_btn.setText("✅ Fixed")
                self._refresh_curator_stats()
                self._set_status("Training example saved (corrected)")

    def _refresh_curator_stats(self):
        try:
            stats = get_stats()
            self.curator_stats_label.setText(
                f"Examples: {stats['total']}  (👍 {stats['thumbs_up']}  ✏️ {stats['corrected']})"
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
                "Ready for Unsloth fine-tuning.\n"
                "See training/qlora_config_template.yaml for the training config."
            )
            self._set_status(f"Exported {count} training examples to {out_path}")
