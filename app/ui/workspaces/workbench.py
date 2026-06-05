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
    QDoubleSpinBox, QSpinBox, QListWidget,
    QTreeWidget, QTreeWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QKeySequence, QShortcut, QColor

from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from core.workflows import list_workflows
from app.utils.session_tree import SessionTree


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
    '<div style="color:#505068;font-size:7.5pt;font-weight:bold;margin-bottom:3px;letter-spacing:1px;">'
    'YOU &nbsp;|&nbsp; <a href="branch:{node_id}" style="color:#00C2FF;text-decoration:none;">branch</a></div>'
    '<div style="background:#1C1C2A;border:1px solid #383850;border-radius:4px;'
    'padding:10px 14px;color:#E4E4F0;font-size:10pt;'
    'white-space:pre-wrap;display:inline-block;text-align:left;">{text}</div>'
    '</div>'
)

_KARL_HDR = (
    '<div style="margin:10px 60px 0 0;">'
    '<div style="color:#505068;font-size:7.5pt;font-weight:bold;margin-bottom:3px;letter-spacing:1px;">'
    'KARL &nbsp;|&nbsp; <a href="branch:{node_id}" style="color:#00C2FF;text-decoration:none;">branch</a></div>'
    '<div style="background:#14141F;border:1px solid #252535;border-radius:4px;'
    'padding:10px 14px;color:#E4E4F0;font-size:10pt;'
    'white-space:pre-wrap;min-height:1em;">'
)

_KARL_FOOT = '</div></div>'


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

    # public API ──────────────────────────────────────────────────────────────

    def push_user(self, text: str, node_id: str):
        self._finalize_stream()
        self._messages.append(("user", text, node_id))
        self._render_all()

    def begin_stream(self, node_id: str = ""):
        self._streaming = True
        self._streaming_buf = ""
        self._streaming_node_id = node_id
        # Append the karl header block then let tokens stream in
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertHtml(_KARL_HDR.format(node_id=node_id))

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
        self._messages.append(("assistant", self._streaming_buf, final_node_id))
        self._streaming_buf = ""
        self._streaming = False
        # Close the HTML block we opened in begin_stream
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.insertHtml(_KARL_FOOT)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        # Cleanly re-render with the final node ID and links
        self._render_all()

    def clear_display(self):
        self._messages.clear()
        self._streaming_buf = ""
        self._streaming = False
        self.clear()

    def replace_last_assistant(self, text: str):
        if self._messages and self._messages[-1][0] == "assistant":
            self._messages[-1] = ("assistant", text, self._messages[-1][2])
            self._render_all()


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

    def append_rag_sources(self, results: list[dict]):
        self._finalize_stream()
        if not results:
            return
        lines = []
        lines.append(
            '<div style="margin:8px 60px 8px 10px; padding:10px 12px; '
            'background:#1C1C2A; border:1px solid #383850; border-radius:4px; '
            'font-family: \'JetBrains Mono\', monospace; font-size:8.5pt;">'
        )
        lines.append('<div style="color:#00C2FF; font-weight:bold; margin-bottom:6px;">🔍 Injected RAG Context:</div>')
        for r in results:
            lines.append(
                f'<div style="color:#E4E4F0; margin-bottom:4px;">'
                f'• <b>{_escape(r["source_file"])}</b> (Chunk {r["chunk_id"]}, distance: '
                f'<span style="color:#F0B030;">{r["distance"]:.4f}</span>)'
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
        for role, text, node_id in self._messages:
            safe = _escape(text)
            if role == "user":
                parts.append(_USER_TPL.format(text=safe, node_id=node_id))
            else:
                parts.append(_KARL_HDR.format(node_id=node_id) + safe + _KARL_FOOT)
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

        self._build_ui()
        self._connect_shortcuts()
        self._refresh_sessions()
        self._refresh_model_combo()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(1)

        # Pane 0: Sessions panel
        self._sessions_panel = self._build_sessions_panel()
        splitter.addWidget(self._sessions_panel)

        # Pane 1: Reasoning panel
        self._reasoning_panel = self._build_reasoning_panel()
        splitter.addWidget(self._reasoning_panel)

        # Pane 2: Chat panel
        right = self._build_chat_panel()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([200, 280, 720])

        root.addWidget(splitter)

    def _build_sessions_panel(self) -> QWidget:
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
        hdr_layout.addWidget(_label("SESSIONS", "section-header"))
        layout.addWidget(hdr)

        self._sessions_list = QListWidget()
        self._sessions_list.currentItemChanged.connect(self._on_session_clicked)
        layout.addWidget(self._sessions_list, 1)

        # separator
        layout.addWidget(_hline())

        # branches header
        hdr_branches = QWidget()
        hdr_branches.setObjectName("panel-header")
        hdr_branches_layout = QHBoxLayout(hdr_branches)
        hdr_branches_layout.setContentsMargins(12, 5, 8, 5)
        hdr_branches.setFixedHeight(30)
        hdr_branches_layout.addWidget(_label("BRANCHES", "section-header"))
        layout.addWidget(hdr_branches)

        self._branches_tree = QTreeWidget()
        self._branches_tree.setHeaderHidden(True)
        self._branches_tree.itemClicked.connect(self._on_branch_clicked)
        layout.addWidget(self._branches_tree, 1)

        return w

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
        
        self._reasoning_stats_lbl = QLabel("")
        self._reasoning_stats_lbl.setObjectName("lbl-muted")
        self._reasoning_stats_lbl.setStyleSheet("margin-left: 8px; font-weight: normal; font-size: 8pt;")
        hdr_layout.addWidget(self._reasoning_stats_lbl)
        
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
        self._thumb_btn.setObjectName("btn-ghost")
        self._thumb_btn.setEnabled(False)
        self._thumb_btn.setToolTip("Curate this response as a positive training example")
        self._thumb_btn.clicked.connect(self._on_thumb_up)

        self._thumb_down_btn = QPushButton("✗ bad")
        self._thumb_down_btn.setObjectName("btn-ghost")
        self._thumb_down_btn.setEnabled(False)
        self._thumb_down_btn.setToolTip("Flag this response as an incorrect/negative training example")
        self._thumb_down_btn.clicked.connect(self._on_thumb_down)

        self._correct_btn = QPushButton("✎ correct")
        self._correct_btn.setObjectName("btn-ghost")
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
        ctrl_layout.addWidget(self._rag_check)

        self._loop_check = QCheckBox("Loop")
        self._loop_check.setToolTip("Run generation in an autonomous iterative agentic loop")
        ctrl_layout.addWidget(self._loop_check)

        self._params_toggle = QPushButton("⚙")
        self._params_toggle.setObjectName("btn-ghost")
        self._params_toggle.setFixedWidth(28)
        self._params_toggle.setToolTip("Toggle generation parameters")
        self._params_toggle.clicked.connect(self._toggle_params)
        ctrl_layout.addWidget(self._params_toggle)

        ctrl_layout.addStretch()

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

        user_node = self.chat_history.add_message("user", text)
        self._chat_view.push_user(text, user_node.id)

        chunks = []
        if self._rag_check.isChecked() and self.state.rag.total_chunks > 0:
            top_k = getattr(self.state, "rag_top_k", 3)
            threshold = getattr(self.state, "rag_threshold", 0.0)
            retrieved_metadata = self.state.rag.retrieve_with_metadata(
                text,
                top_k=top_k
            )
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
        t = LLMThread(
            system_prompt=self._system_prompt,
            chat_history=list(self.chat_history),
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
        t = AgenticThread(
            system_prompt=self._system_prompt,
            initial_history=list(self.chat_history),
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
        visible = self._reasoning_view.isVisible()
        self._reasoning_view.setVisible(not visible)
        self._toggle_reason_btn.setText("show" if visible else "hide")

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
            
            note = f"— Active model switched to: {filename} (adapter: {adapter_name or 'none'}) —"
            self._chat_view.append_system_note(note)
        except Exception as e:
            self._chat_view.append_system_note(f"[Error switching model: {str(e)}]")
        finally:
            self._set_busy(False)
            self.status_changed.emit("idle", False)

    def _new_session(self):
        self._save_current_session()
        self._current_session_file = None
        self.chat_history.clear()
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
            diag_text = (
                f"— Generation Diagnostics —\n"
                f"Model: {model_name} (n_ctx={n_ctx})\n"
                f"Prompt: {diagnostics.get('prompt_tokens', 0)} tokens (prefill in {diagnostics.get('prefill_time', 0):.2f}s @ {diagnostics.get('prefill_tps', 0):.1f} t/s)\n"
                f"Generation: {diagnostics.get('generation_tokens', 0)} tokens (generated in {diagnostics.get('generation_time', 0):.2f}s @ {diagnostics.get('generation_tps', 0):.1f} t/s)\n"
                f"Total Time: {diagnostics.get('total_time', 0):.2f}s @ {diagnostics.get('total_tps', 0):.1f} t/s"
            )
            self._chat_view.append_system_note(diag_text)

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
        self._chat_view.begin_stream()
        self._last_response = response

    def _on_loop_done(self, total: int):
        self._reasoning_stats_lbl.setText("")
        self._chat_view.finalize_stream()
        if self._thread and hasattr(self._thread, "chat_history"):
            thread_history = self._thread.chat_history
            original_len = len(self.chat_history)
            new_msgs = thread_history[original_len:]
            for msg in new_msgs:
                self.chat_history.add_message(msg["role"], msg["content"])
            
            # Refresh ChatView to ensure all messages have correct node_ids
            self._chat_view.clear_display()
            active_path = self.chat_history.get_active_path()
            self._chat_view._messages = [(n.role, n.content, n.id) for n in active_path]
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
        self._current_session_file = self.state.memory.save_session(
            chat_history=self.chat_history,
            system_prompt=self._system_prompt,
            filename=self._current_session_file
        )
        self._refresh_sessions()

    def _refresh_sessions(self):
        self._sessions_list.blockSignals(True)
        self._sessions_list.clear()
        sessions = self.state.memory.list_sessions()
        sessions.sort(reverse=True)
        for s in sessions:
            self._sessions_list.addItem(s)
        if getattr(self, "_current_session_file", None):
            items = self._sessions_list.findItems(self._current_session_file, Qt.MatchFlag.MatchFixedString)
            if items:
                self._sessions_list.setCurrentItem(items[0])
        self._sessions_list.blockSignals(False)

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

        self._chat_view.clear_display()
        active_path = self.chat_history.get_active_path()
        self._chat_view._messages = [(n.role, n.content, n.id) for n in active_path]
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

    def _set_busy(self, busy: bool):
        self._send_btn.setEnabled(not busy)
        self._stop_btn.setEnabled(busy)
        self._input.setEnabled(not busy)
        state_text = "generating..." if busy else "idle"
        self.status_changed.emit(state_text, busy)

    def _on_chat_link_clicked(self, url):
        link = url.toString()
        if link.startswith("branch:"):
            node_id = link.split(":", 1)[1]
            self._branch_from_node(node_id)

    def _branch_from_node(self, node_id):
        if not self.chat_history:
            return
        self.chat_history.set_current_node(node_id)
        
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
        self._chat_view._messages = [(n.role, n.content, n.id) for n in active_path]
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
