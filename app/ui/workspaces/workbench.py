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

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QTextEdit, QComboBox,
    QLabel, QSizePolicy, QFrame, QCheckBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QKeySequence, QShortcut

from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from core.workflows import list_workflows


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

_USER_TPL = (
    '<div style="margin:10px 0 4px 60px; text-align:right;">'
    '<div style="color:#505068;font-size:8pt;margin-bottom:3px;">you</div>'
    '<div style="background:#1C1C2A;border:1px solid #383850;border-radius:4px;'
    'padding:8px 12px;color:#E4E4F0;font-family:monospace;font-size:10pt;'
    'white-space:pre-wrap;display:inline-block;text-align:left;">{text}</div>'
    '</div>'
)

_KARL_HDR = (
    '<div style="margin:10px 60px 0 0;">'
    '<div style="color:#505068;font-size:8pt;margin-bottom:3px;">karl</div>'
    '<div style="background:#14141F;border:1px solid #252535;border-radius:4px;'
    'padding:8px 12px;color:#E4E4F0;font-family:monospace;font-size:10pt;'
    'white-space:pre-wrap;min-height:1em;">'
)

_KARL_FOOT = '</div></div>'


class ChatView(QTextBrowser):
    """Scrollable conversation display with streaming support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        self._messages: list[tuple[str, str]] = []   # (role, text)
        self._streaming_buf = ""
        self._streaming = False

    # public API ──────────────────────────────────────────────────────────────

    def push_user(self, text: str):
        self._finalize_stream()
        self._messages.append(("user", text))
        self._render_all()

    def begin_stream(self):
        self._streaming = True
        self._streaming_buf = ""
        # Append the karl header block then let tokens stream in
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertHtml(_KARL_HDR)

    def append_token(self, token: str):
        if not self._streaming:
            return
        self._streaming_buf += token
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def finalize_stream(self):
        if not self._streaming:
            return
        self._messages.append(("assistant", self._streaming_buf))
        self._streaming_buf = ""
        self._streaming = False
        # Close the HTML block we opened in begin_stream
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(_KARL_FOOT)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_display(self):
        self._messages.clear()
        self._streaming_buf = ""
        self._streaming = False
        self.clear()

    def append_system_note(self, text: str):
        self._finalize_stream()
        safe = _escape(text)
        html = (
            f'<div style="margin:6px 0;color:#505068;font-size:8pt;'
            f'text-align:center;">{safe}</div>'
        )
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        self.ensureCursorVisible()

    # internals ───────────────────────────────────────────────────────────────

    def _finalize_stream(self):
        if self._streaming:
            self.finalize_stream()

    def _render_all(self):
        parts = []
        for role, text in self._messages:
            safe = _escape(text)
            if role == "user":
                parts.append(_USER_TPL.format(text=safe))
            else:
                parts.append(_KARL_HDR + safe + _KARL_FOOT)
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

class WorkbenchWorkspace(QWidget):
    status_changed = pyqtSignal(str, bool)   # (text, active)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")

        self.chat_history: list[dict] = []
        self._thread: LLMThread | AgenticThread | None = None
        self._last_response = ""
        self._last_thought = ""
        self._hyperparams = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 2048,
        }
        self._system_prompt = (
            "You are Karl, a precise and thoughtful AI assistant. "
            "Reason carefully before responding."
        )

        self._build_ui()
        self._connect_shortcuts()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(1)

        # Left: reasoning panel
        self._reasoning_panel = self._build_reasoning_panel()
        splitter.addWidget(self._reasoning_panel)

        # Right: chat + input
        right = self._build_chat_panel()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([280, 720])

        root.addWidget(splitter)

    def _build_reasoning_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("panel")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setObjectName("panel-header")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(12, 5, 8, 5)
        hdr.setFixedHeight(30)
        hdr_layout.addWidget(_label("REASONING", "section-header"))
        hdr_layout.addStretch()
        self._toggle_reason_btn = QPushButton("hide")
        self._toggle_reason_btn.setObjectName("btn-ghost")
        self._toggle_reason_btn.setFixedWidth(36)
        self._toggle_reason_btn.clicked.connect(self._toggle_reasoning)
        hdr_layout.addWidget(self._toggle_reason_btn)
        layout.addWidget(hdr)

        self._reasoning_view = QTextBrowser()
        self._reasoning_view.setObjectName("reasoning-view")
        self._reasoning_view.setReadOnly(True)
        self._reasoning_view.setPlaceholderText("reasoning tokens will appear here...")
        layout.addWidget(self._reasoning_view, 1)

        return w

    def _build_chat_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # chat display
        self._chat_view = ChatView(w)
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
        self._thumb_btn.setObjectName("btn-ghost")
        self._thumb_btn.setEnabled(False)
        self._thumb_btn.clicked.connect(self._on_thumb_up)

        self._correct_btn = QPushButton("✎ correct")
        self._correct_btn.setObjectName("btn-ghost")
        self._correct_btn.setEnabled(False)
        self._correct_btn.clicked.connect(self._on_correct)

        self._new_session_btn = QPushButton("+ new session")
        self._new_session_btn.setObjectName("btn-ghost")
        self._new_session_btn.clicked.connect(self._new_session)

        for b in (self._thumb_btn, self._correct_btn, self._new_session_btn):
            fb_layout.addWidget(b)

        layout.addWidget(feedback_row)
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
        ic_layout.addWidget(self._input)

        # controls
        ctrl = QWidget()
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        self._workflow_combo = QComboBox()
        self._workflow_combo.setFixedWidth(160)
        for name, label in list_workflows():
            self._workflow_combo.addItem(label, name)
        ctrl_layout.addWidget(self._workflow_combo)

        self._rag_check = QCheckBox("RAG")
        self._rag_check.setToolTip("Inject knowledge base context")
        ctrl_layout.addWidget(self._rag_check)

        self._loop_check = QCheckBox("Loop")
        self._loop_check.setToolTip("Run in agentic loop mode")
        ctrl_layout.addWidget(self._loop_check)

        ctrl_layout.addStretch()

        self._stop_btn = QPushButton("■ stop")
        self._stop_btn.setObjectName("btn-danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        ctrl_layout.addWidget(self._stop_btn)

        self._send_btn = QPushButton("send ↵")
        self._send_btn.setObjectName("btn-primary")
        self._send_btn.clicked.connect(self._send)
        ctrl_layout.addWidget(self._send_btn)

        ic_layout.addWidget(ctrl)
        layout.addWidget(input_container)

        return w

    def _connect_shortcuts(self):
        sc = QShortcut(QKeySequence("Ctrl+Return"), self)
        sc.activated.connect(self._send)

    # ── actions ───────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.toPlainText().strip()
        if not text or self._thread is not None:
            return

        self._input.clear()
        self._chat_view.push_user(text)
        self._reasoning_view.clear()
        self._thumb_btn.setEnabled(False)
        self._correct_btn.setEnabled(False)

        self.chat_history.append({"role": "user", "content": text})

        chunks = []
        if self._rag_check.isChecked() and self.state.rag.total_chunks > 0:
            chunks = self.state.rag.retrieve(text, top_k=3)

        if self._loop_check.isChecked():
            self._start_agentic(chunks)
        else:
            self._start_single(chunks)

    def _start_single(self, chunks: list[str]):
        self._chat_view.begin_stream()
        self._set_busy(True)
        t = LLMThread(
            system_prompt=self._system_prompt,
            chat_history=list(self.chat_history),
            hyperparams=self._hyperparams,
            retrieved_chunks=chunks,
        )
        t.new_thought_token.connect(self._on_thought)
        t.new_chat_token.connect(self._on_chat)
        t.generation_finished.connect(self._on_done)
        t.error_occurred.connect(self._on_error)
        self._thread = t
        t.start()

    def _start_agentic(self, chunks: list[str]):
        self._set_busy(True)
        self._chat_view.append_system_note("— agentic loop started —")
        t = AgenticThread(
            system_prompt=self._system_prompt,
            initial_history=list(self.chat_history),
            hyperparams=self._hyperparams,
        )
        t.new_thought_token.connect(self._on_thought)
        t.new_chat_token.connect(self._on_chat)
        t.iteration_finished.connect(self._on_iteration)
        t.loop_finished.connect(self._on_loop_done)
        t.error_occurred.connect(self._on_error)
        self._thread = t
        t.start()

    def _stop(self):
        if self._thread:
            if hasattr(self._thread, "request_stop"):
                self._thread.request_stop()

    def _toggle_reasoning(self):
        visible = self._reasoning_view.isVisible()
        self._reasoning_view.setVisible(not visible)
        self._toggle_reason_btn.setText("show" if visible else "hide")

    def _new_session(self):
        self.chat_history.clear()
        self._chat_view.clear_display()
        self._reasoning_view.clear()
        self._last_response = ""
        self._last_thought = ""
        self._thumb_btn.setEnabled(False)
        self._correct_btn.setEnabled(False)

    # ── thread slots ──────────────────────────────────────────────────────────

    def _on_thought(self, token: str):
        cursor = self._reasoning_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self._reasoning_view.setTextCursor(cursor)
        self._reasoning_view.ensureCursorVisible()

    def _on_chat(self, token: str):
        self._chat_view.append_token(token)

    def _on_done(self, thought: str, response: str, truncated: bool, _ended_in_thought: bool):
        self._chat_view.finalize_stream()
        self.chat_history.append({"role": "assistant", "content": response})
        self._last_response = response
        self._last_thought = thought
        if truncated:
            self._chat_view.append_system_note("— generation truncated —")
        self._set_busy(False)
        self._thumb_btn.setEnabled(True)
        self._correct_btn.setEnabled(True)
        self._thread = None
        self.status_changed.emit("idle", False)

    def _on_iteration(self, index: int, _thought: str, response: str):
        self._chat_view.finalize_stream()
        self._chat_view.append_system_note(f"— iteration {index + 1} complete —")
        self._chat_view.begin_stream()
        self._last_response = response

    def _on_loop_done(self, total: int):
        self._chat_view.finalize_stream()
        self._chat_view.append_system_note(f"— loop finished ({total} iterations) —")
        self._set_busy(False)
        self._thread = None
        self.status_changed.emit("idle", False)

    def _on_error(self, msg: str):
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
            )
            self._thumb_btn.setText("✓ saved")
            self._thumb_btn.setEnabled(False)

    def _on_correct(self):
        self._correct_btn.setText("editing...")
        self._correct_btn.setEnabled(False)
        self._input.setPlainText(self._last_response)
        self._input.setFocus()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool):
        self._send_btn.setEnabled(not busy)
        self._stop_btn.setEnabled(busy)
        self._input.setEnabled(not busy)
        state_text = "generating..." if busy else "idle"
        self.status_changed.emit(state_text, busy)

    # ── public API for main_window ────────────────────────────────────────────

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt

    def set_hyperparams(self, params: dict):
        self._hyperparams.update(params)
