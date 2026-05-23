"""
Karl -- Main Window v5
======================
Single-page clean chat interface.
Left panel: sessions + file ingestion.
Main area: thinking panel (collapsible) + response + input.
Right panel: configure (theme picker + a few sliders only).
No workflow complexity. Just talk to it.
"""

import time as _time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QSplitter,
    QTextEdit, QLabel, QDoubleSpinBox, QSpinBox,
    QListWidget, QFileDialog, QCheckBox, QMessageBox,
    QComboBox, QFrame, QStatusBar, QApplication, QSizePolicy,
    QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.utils.memory_manager import MemoryManager
from app.utils.rag_pipeline import RAGPipeline
from app.utils.training_curator import save_example, get_stats
from app.ui.themes import THEMES, generate_stylesheet


# ---------------------------------------------------------------------------
# Background threads
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


# ---------------------------------------------------------------------------
# Tiny UI helpers
# ---------------------------------------------------------------------------

def _rule() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("border: none; border-top: 1px solid #222226; max-height: 1px;")
    return f


def _cap_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #3A3A3F; font-size: 8pt; font-weight: bold; "
        "letter-spacing: 0.12em; padding: 14px 0 5px 0; background: transparent;"
    )
    return lbl


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    SYSTEM_PROMPT = (
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
        self.setMinimumSize(1100, 680)

        # State
        self.chat_history: list[dict] = []
        self.memory_manager = MemoryManager()
        self.rag_pipeline = RAGPipeline()
        self.current_session_file = None
        self.agentic_thread = None
        self._last_user_msg = ""
        self._last_response = ""
        self._last_chunks: list = []
        self._gen_start = 0.0
        self._current_theme = "Midnight"
        self._thinking_visible = True

        self._build_ui()
        self._build_status_bar()
        self._refresh_sessions()
        self._run_upgrade_check()
        self._apply_theme("Midnight")

    # ==========================================================================
    # UI build
    # ==========================================================================

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_center())
        splitter.addWidget(self._build_right())
        splitter.setSizes([230, 1000, 280])

    # --------------------------------------------------------------------------
    # LEFT -- Sessions + Knowledge Base
    # --------------------------------------------------------------------------

    def _build_left(self) -> QWidget:
        p = QWidget()
        p.setFixedWidth(230)
        p.setObjectName("left_panel")
        p.setStyleSheet("QWidget#left_panel { background-color: #08080B; border-right: 1px solid #1A1A1D; }")
        l = QVBoxLayout(p)
        l.setContentsMargins(14, 18, 14, 16)
        l.setSpacing(5)

        # App title
        title = QLabel("Karl")
        title.setStyleSheet(
            "color: #2A2A2E; font-size: 13pt; font-weight: bold; "
            "letter-spacing: 0.08em; padding-bottom: 8px; background: transparent;"
        )
        l.addWidget(title)
        l.addWidget(_rule())

        # Sessions
        l.addWidget(_cap_label("Sessions"))
        self.session_list = QListWidget()
        self.session_list.setToolTip(
            "Saved conversations.\nDouble-click to restore a session."
        )
        self.session_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.session_list.itemDoubleClicked.connect(self._load_session)
        l.addWidget(self.session_list)

        sr = QHBoxLayout()
        sr.setSpacing(6)
        btn_new = QPushButton("New")
        btn_new.setToolTip("Start a fresh conversation.")
        btn_new.clicked.connect(self._new_session)
        btn_save = QPushButton("Save")
        btn_save.setToolTip("Save the current conversation.")
        btn_save.clicked.connect(self._save_session)
        sr.addWidget(btn_new)
        sr.addWidget(btn_save)
        l.addLayout(sr)

        # Knowledge Base
        l.addSpacing(8)
        l.addWidget(_cap_label("Knowledge Base"))
        kb_hint = QLabel("Ingest files so Karl can reference them automatically.")
        kb_hint.setWordWrap(True)
        kb_hint.setStyleSheet("color: #2A2A2E; font-size: 8.5pt; padding-bottom: 6px; background: transparent;")
        l.addWidget(kb_hint)

        self.kb_list = QListWidget()
        self.kb_list.setMaximumHeight(130)
        self.kb_list.setToolTip(
            "Ingested documents.\nTheir content is retrieved and injected automatically when relevant."
        )
        l.addWidget(self.kb_list)

        btn_ingest = QPushButton("Add File")
        btn_ingest.setToolTip(
            "Load a file into the knowledge base.\n"
            "Supported: PDF, DOCX, TXT, PY, MD, CSV."
        )
        btn_ingest.clicked.connect(self._ingest_doc)
        l.addWidget(btn_ingest)

        return p

    # --------------------------------------------------------------------------
    # CENTER -- Thinking + Chat + Input
    # --------------------------------------------------------------------------

    def _build_center(self) -> QWidget:
        p = QWidget()
        l = QVBoxLayout(p)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        vs = QSplitter(Qt.Orientation.Vertical)
        vs.setChildrenCollapsible(True)
        l.addWidget(vs)

        vs.addWidget(self._build_thinking_panel())
        vs.addWidget(self._build_chat_panel())
        vs.setSizes([260, 620])
        return p

    def _build_thinking_panel(self) -> QWidget:
        c = QWidget()
        c.setObjectName("think_panel")
        c.setStyleSheet("QWidget#think_panel { background-color: #070A11; border-bottom: 1px solid #0F1020; }")
        l = QVBoxLayout(c)
        l.setContentsMargins(20, 12, 20, 10)
        l.setSpacing(6)

        hdr = QHBoxLayout()
        hdr_lbl = QLabel("Reasoning")
        hdr_lbl.setStyleSheet(
            "color: #1A2A4A; font-size: 8.5pt; font-weight: bold; "
            "letter-spacing: 0.10em; background: transparent;"
        )
        hdr_lbl.setToolTip(
            "Karl's internal chain of thought.\n"
            "Streams live while the model thinks before answering.\n"
            "You can collapse this panel by dragging the divider up."
        )
        self.think_toggle = QPushButton("Hide")
        self.think_toggle.setFixedHeight(22)
        self.think_toggle.setFixedWidth(52)
        self.think_toggle.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #1A2A4A; "
            "border-radius: 3px; color: #1A2A4A; font-size: 8pt; padding: 0; }"
            "QPushButton:hover { color: #2A3A6A; border-color: #2A3A6A; }"
        )
        self.think_toggle.clicked.connect(self._toggle_thinking)
        hdr.addWidget(hdr_lbl)
        hdr.addStretch()
        hdr.addWidget(self.think_toggle)
        l.addLayout(hdr)

        self.thought_display = QTextBrowser()
        self.thought_display.setStyleSheet(
            "background-color: #050810; color: #1F3070; "
            "font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 9.5pt; "
            "border: 1px solid #0A1228; border-radius: 4px; padding: 10px 14px;"
        )
        l.addWidget(self.thought_display)
        return c

    def _build_chat_panel(self) -> QWidget:
        c = QWidget()
        l = QVBoxLayout(c)
        l.setContentsMargins(20, 14, 20, 16)
        l.setSpacing(10)

        # Response header + rating
        hdr = QHBoxLayout()
        resp_lbl = QLabel("Response")
        resp_lbl.setStyleSheet(
            "color: #3A3A3F; font-size: 8.5pt; font-weight: bold; "
            "letter-spacing: 0.10em; background: transparent;"
        )
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setObjectName("btn_accept")
        self.accept_btn.setFixedHeight(26)
        self.accept_btn.setToolTip("Save this response as a positive training example.")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self._accept)

        self.correct_btn = QPushButton("Correct")
        self.correct_btn.setObjectName("btn_correct")
        self.correct_btn.setFixedHeight(26)
        self.correct_btn.setToolTip("Edit this response to save the ideal version for training.")
        self.correct_btn.setEnabled(False)
        self.correct_btn.clicked.connect(self._correct)

        hdr.addWidget(resp_lbl)
        hdr.addStretch()
        hdr.addWidget(self.accept_btn)
        hdr.addWidget(self.correct_btn)
        l.addLayout(hdr)

        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet(
            "background-color: #0E0E11; color: #DDDDE0; "
            "font-family: 'Segoe UI', sans-serif; font-size: 12pt; "
            "border: 1px solid #1E1E22; border-radius: 4px; padding: 16px 20px; "
            "line-height: 1.65;"
        )
        l.addWidget(self.chat_display)

        # Input
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ask Karl anything...")
        self.user_input.setMinimumHeight(42)
        self.user_input.setStyleSheet(
            "QLineEdit { font-size: 12pt; padding: 10px 14px; }"
        )
        self.user_input.returnPressed.connect(self._send)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("btn_generate")
        self.send_btn.setFixedHeight(42)
        self.send_btn.setFixedWidth(90)
        self.send_btn.setToolTip("Send your message to Karl. (Enter key also works.)")
        self.send_btn.clicked.connect(self._send)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("btn_stop")
        self.stop_btn.setFixedHeight(42)
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Stop the current generation.")
        self.stop_btn.clicked.connect(self._stop)

        input_row.addWidget(self.user_input)
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.stop_btn)
        l.addLayout(input_row)

        return c

    # --------------------------------------------------------------------------
    # RIGHT -- Settings
    # --------------------------------------------------------------------------

    def _build_right(self) -> QWidget:
        p = QWidget()
        p.setFixedWidth(280)
        p.setObjectName("right_panel")
        p.setStyleSheet("QWidget#right_panel { background-color: #08080B; border-left: 1px solid #1A1A1D; }")
        l = QVBoxLayout(p)
        l.setContentsMargins(16, 18, 16, 16)
        l.setSpacing(6)

        # Theme
        l.addWidget(_cap_label("Theme"))

        self.theme_combo = QComboBox()
        for name in sorted(THEMES.keys()):
            self.theme_combo.addItem(name)
        self.theme_combo.setCurrentText("Midnight")
        self.theme_combo.setToolTip(f"30 color palettes. Switches instantly.")
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        l.addWidget(self.theme_combo)

        # System prompt
        l.addSpacing(6)
        l.addWidget(_cap_label("System Prompt"))
        sys_hint = QLabel("Defines Karl's persona. Editable at any time.")
        sys_hint.setWordWrap(True)
        sys_hint.setStyleSheet("color: #2A2A2E; font-size: 8.5pt; padding-bottom: 4px; background: transparent;")
        l.addWidget(sys_hint)

        self.sys_prompt_input = QTextEdit()
        self.sys_prompt_input.setPlainText(self.SYSTEM_PROMPT)
        self.sys_prompt_input.setMaximumHeight(160)
        self.sys_prompt_input.setToolTip(
            "Injected as the system turn on every generation.\n"
            "Keep it concise -- the model handles reasoning internally."
        )
        l.addWidget(self.sys_prompt_input)

        # RAG top-k
        l.addSpacing(6)
        l.addWidget(_cap_label("Context Retrieval"))
        rag_hint = QLabel("Number of knowledge base chunks to include per message.")
        rag_hint.setWordWrap(True)
        rag_hint.setStyleSheet("color: #2A2A2E; font-size: 8.5pt; padding-bottom: 4px; background: transparent;")
        l.addWidget(rag_hint)

        rag_row = QHBoxLayout()
        rag_lbl = QLabel("Chunks (top-k)")
        rag_lbl.setStyleSheet("color: #505055; font-size: 10pt; background: transparent;")
        self.rag_spin = QSpinBox()
        self.rag_spin.setRange(0, 10)
        self.rag_spin.setValue(3)
        self.rag_spin.setToolTip("Set to 0 to disable retrieval entirely.")
        rag_row.addWidget(rag_lbl)
        rag_row.addStretch()
        rag_row.addWidget(self.rag_spin)
        l.addLayout(rag_row)

        # Generation
        l.addSpacing(6)
        l.addWidget(_cap_label("Generation"))

        def _spin_row(label, widget, tip=""):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #505055; font-size: 10pt; background: transparent;")
            if tip:
                lbl.setToolTip(tip)
                widget.setToolTip(tip)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(widget)
            return row

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setValue(0.7)
        l.addLayout(_spin_row("Temperature", self.temp_spin,
            "0.0 = deterministic. 0.7 = balanced. 1.2+ = creative."))

        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.95)
        l.addLayout(_spin_row("Top-P", self.top_p_spin,
            "Nucleus sampling. 0.95 is recommended."))

        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(128, 4096)
        self.tokens_spin.setValue(2048)
        l.addLayout(_spin_row("Max Tokens", self.tokens_spin,
            "Maximum tokens per generation. 2048 recommended.\n"
            "Karl chains continuations automatically if the response is cut off."))

        # Loop controls
        l.addSpacing(6)
        l.addWidget(_rule())
        l.addSpacing(4)
        l.addWidget(_cap_label("Autonomous Loop"))
        loop_hint = QLabel(
            "Lets Karl self-iterate on a question, refining its answer across multiple passes."
        )
        loop_hint.setWordWrap(True)
        loop_hint.setStyleSheet("color: #2A2A2E; font-size: 8.5pt; padding-bottom: 4px; background: transparent;")
        l.addWidget(loop_hint)

        self.loop_btn = QPushButton("Run Loop")
        self.loop_btn.setObjectName("btn_agentic")
        self.loop_btn.setToolTip(
            "Starts the self-iteration loop.\n"
            "Karl generates, reflects, and refines up to 20 times\n"
            "or until it writes 'FINAL ANSWER:'.\n\n"
            "Edit core/agentic_loop.py to customize stop conditions."
        )
        self.loop_btn.clicked.connect(self._start_loop)

        self.stop_loop_btn = QPushButton("Stop Loop")
        self.stop_loop_btn.setObjectName("btn_stop")
        self.stop_loop_btn.setEnabled(False)
        self.stop_loop_btn.clicked.connect(self._stop_loop)

        self.loop_status = QLabel("Idle")
        self.loop_status.setStyleSheet("color: #2A2A2E; font-size: 9.5pt; background: transparent;")

        l.addWidget(self.loop_btn)
        l.addWidget(self.stop_loop_btn)
        l.addWidget(self.loop_status)

        l.addStretch()

        # Upgrade notice (hidden until check completes)
        self.upgrade_lbl = QLabel("")
        self.upgrade_lbl.setWordWrap(True)
        self.upgrade_lbl.setStyleSheet("color: #93C5FD; font-size: 8.5pt; background: transparent;")
        self.upgrade_lbl.setVisible(False)
        l.addWidget(self.upgrade_lbl)

        self.upgrade_btn = QPushButton("Upgrade Model")
        self.upgrade_btn.setVisible(False)
        self.upgrade_btn.clicked.connect(self._confirm_upgrade)
        l.addWidget(self.upgrade_btn)

        return p

    # --------------------------------------------------------------------------
    # Status bar
    # --------------------------------------------------------------------------

    def _build_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet("color: #3A3A3F; font-size: 9pt;")
        sb.addWidget(self._status_lbl)
        self._latency_lbl = QLabel("")
        self._latency_lbl.setStyleSheet("color: #252528; font-size: 9pt;")
        sb.addPermanentWidget(self._latency_lbl)

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    # ==========================================================================
    # Theme
    # ==========================================================================

    def _apply_theme(self, name: str):
        self._current_theme = name
        QApplication.instance().setStyleSheet(generate_stylesheet(name))

    # ==========================================================================
    # Panel toggle
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
        self.chat_history = []
        self.current_session_file = None
        self.chat_display.clear()
        self.thought_display.clear()
        self.chat_display.setPlaceholderText("Your conversation with Karl appears here.")
        self._set_status("New session")

    def _save_session(self):
        if not self.chat_history:
            return
        self.current_session_file = self.memory_manager.save_session(
            self.chat_history,
            self.sys_prompt_input.toPlainText(),
            self.current_session_file
        )
        self._refresh_sessions()
        self._set_status(f"Saved: {self.current_session_file}")

    def _load_session(self, item):
        sys_prompt, history = self.memory_manager.load_session(item.text())
        self.sys_prompt_input.setPlainText(sys_prompt)
        self.chat_history = history
        self.current_session_file = item.text()
        self.chat_display.clear()
        self.thought_display.clear()
        for msg in history:
            role, content = msg.get("role"), msg.get("content", "")
            if role == "user":
                self.chat_display.append(f"<b>You:</b>  {content}\n")
            elif role == "assistant":
                clean = content
                if "</think>" in clean:
                    clean = clean.split("</think>", 1)[1].strip()
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
        name = path.replace("\\", "/").split("/")[-1]
        if chunks > 0:
            self.kb_list.addItem(f"{name}  ({chunks})")
            self._set_status(f"Ingested {name} -- {chunks} chunks")
        else:
            self._set_status(f"Failed: {name}")

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
            "top_p": self.top_p_spin.value(),
            "max_tokens": self.tokens_spin.value(),
        }

    # ==========================================================================
    # Generation
    # ==========================================================================

    def _send(self):
        text = self.user_input.text().strip()
        if not text:
            return
        self.user_input.clear()
        self._last_user_msg = text
        self.accept_btn.setEnabled(False)
        self.correct_btn.setEnabled(False)
        self.accept_btn.setText("Accept")
        self.correct_btn.setText("Correct")
        self._set_controls(False)

        self.chat_display.append(f"<b>You:</b>  {text}\n")
        self.chat_display.append("<b>Karl:</b>  ")
        self.thought_display.append(f"\n--- {text[:60]} ---\n")

        self.chat_history.append({"role": "user", "content": text})

        # Build system prompt -- inject RAG if any
        top_k = self.rag_spin.value()
        retrieved = self.rag_pipeline.retrieve(text, top_k=top_k) if top_k > 0 else []
        self._last_chunks = retrieved
        sys_prompt = self.sys_prompt_input.toPlainText().strip() or self.SYSTEM_PROMPT
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

    def _stop(self):
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

    def _fire_continuation(self, history, start_in_thought=False):
        sys_prompt = self.sys_prompt_input.toPlainText().strip() or self.SYSTEM_PROMPT
        self.thread = LLMThread(sys_prompt, history, self._hyperparams(),
                                start_in_thought=start_in_thought)
        self.thread.new_thought_token.connect(self._on_thought)
        self.thread.new_chat_token.connect(self._on_chat)
        self.thread.new_raw_token.connect(lambda _: None)
        self.thread.generation_finished.connect(self._on_done)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _on_done(self, thought, response, truncated=False, ended_in_thought=False):
        self.chat_history.append({"role": "assistant", "content": response})
        self._last_response = response

        if truncated:
            self._on_thought("\n[continuing...]\n")
            cont = list(self.chat_history) + [{"role": "user", "content": "Continue."}]
            self._fire_continuation(cont, start_in_thought=ended_in_thought)
            return

        self.chat_display.append("\n")
        self.accept_btn.setEnabled(True)
        self.correct_btn.setEnabled(True)

        latency = _time.time() - self._gen_start
        rag_note = f"  |  {len(self._last_chunks)} chunk(s) retrieved" if self._last_chunks else ""
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
            self.chat_display.append(
                "<i><font color='#F59E0B'>Send a message first to seed the loop.</font></i>"
            )
            return
        self._set_controls(False)
        self.stop_loop_btn.setEnabled(True)
        self.loop_status.setText("Running")
        self.loop_status.setStyleSheet("color: #22C55E; font-size: 9.5pt; background: transparent;")
        self.thought_display.append("\n" + "=" * 50 + "\nAUTONOMOUS LOOP STARTED\n" + "=" * 50)
        self._set_status("Loop running...")

        sys_prompt = self.sys_prompt_input.toPlainText().strip() or self.SYSTEM_PROMPT
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
        self.loop_status.setText("Stopping")
        self.loop_status.setStyleSheet("color: #F59E0B; font-size: 9.5pt; background: transparent;")

    def _on_loop_done(self, total: int):
        self._set_controls(True)
        self.stop_loop_btn.setEnabled(False)
        self.loop_status.setText("Done")
        self.loop_status.setStyleSheet("color: #2A2A2E; font-size: 9.5pt; background: transparent;")
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
        dlg.resize(640, 320)
        dl = QVBoxLayout(dlg)
        dl.setContentsMargins(20, 20, 20, 16)
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
            f"Upgrade: {entry['name']}\n(RAM {profile['ram_gb']}GB)"
        )
        self.upgrade_lbl.setVisible(True)
        self.upgrade_btn.setVisible(True)

    def _confirm_upgrade(self):
        reply = QMessageBox.question(
            self, "Upgrade Karl",
            f"Download {self._pending_entry['name']}?\nThis will restart the model.",
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



