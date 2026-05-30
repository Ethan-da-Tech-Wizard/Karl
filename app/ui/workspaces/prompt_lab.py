"""
Prompt Lab — side-by-side prompt engineering workspace.

Left prompt (A) vs right prompt (B): run both, compare outputs.
All runs are logged to trace.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QTextEdit, QLabel,
    QFrame, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


# ── single-shot run thread (thin wrapper around ModelLoader) ─────────────────

class _RunThread(QThread):
    token = pyqtSignal(str)
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, system_prompt: str, user_prompt: str, hyperparams: dict):
        super().__init__()
        self.system_prompt = system_prompt
        self.user_prompt   = user_prompt
        self.hyperparams   = hyperparams

    def run(self):
        try:
            from app.engine.model_loader import ModelLoader
            import core.interaction_loop
            import importlib
            importlib.reload(core.interaction_loop)

            llm = ModelLoader.get_instance()
            history = [{"role": "user", "content": self.user_prompt}]
            prompt  = core.interaction_loop.build_prompt(self.system_prompt, history)

            full = ""
            for chunk in llm(
                prompt,
                max_tokens=self.hyperparams.get("max_tokens", 1024),
                temperature=self.hyperparams.get("temperature", 0.7),
                top_p=self.hyperparams.get("top_p", 0.95),
                stream=True,
                stop=["<|im_end|>", "<|endoftext|>", "<|im_start|>"],
                echo=False,
            ):
                if "choices" not in chunk:
                    continue
                text = chunk["choices"][0].get("text", "")
                if text:
                    full += text
                    self.token.emit(text)

            # strip think block from shown output
            from core.cognitive_parser import parse_thought_stream
            _, response = parse_thought_stream(full)
            self.done.emit(response)

        except Exception as e:
            self.error.emit(str(e))


# ── single prompt column ──────────────────────────────────────────────────────

class _PromptColumn(QWidget):
    run_requested = pyqtSignal(str, str)   # (label, user_text)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.label = label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(_section(f"PROMPT  {label}"))

        self._system_edit = QTextEdit()
        self._system_edit.setPlaceholderText("system prompt (optional)...")
        self._system_edit.setFixedHeight(60)
        layout.addWidget(self._system_edit)

        self._user_edit = QTextEdit()
        self._user_edit.setPlaceholderText("user message...")
        self._user_edit.setFixedHeight(80)
        layout.addWidget(self._user_edit)

        layout.addWidget(_section(f"OUTPUT  {label}"))

        self._output = QTextBrowser()
        self._output.setPlaceholderText("output will stream here...")
        layout.addWidget(self._output, 1)

        btn = QPushButton(f"▶ run {label}")
        btn.clicked.connect(self._emit_run)
        layout.addWidget(btn)

        self._thread: _RunThread | None = None

    def _emit_run(self):
        self.run_requested.emit(self.label, self._user_edit.toPlainText().strip())

    def system_text(self) -> str:
        return self._system_edit.toPlainText().strip()

    def user_text(self) -> str:
        return self._user_edit.toPlainText().strip()

    def start_run(self, hyperparams: dict):
        user = self.user_text()
        if not user:
            return
        self._output.clear()
        self._output.setPlainText("generating...")
        self._thread = _RunThread(self.system_text(), user, hyperparams)
        self._thread.token.connect(self._on_token)
        self._thread.done.connect(self._on_done)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_token(self, token: str):
        from PyQt6.QtGui import QTextCursor
        c = self._output.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertText(token)
        self._output.setTextCursor(c)
        self._output.ensureCursorVisible()

    def _on_done(self, _response: str):
        pass

    def _on_error(self, msg: str):
        self._output.append(f"\n[error: {msg}]")


# ── workspace ─────────────────────────────────────────────────────────────────

class PromptLabWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._hyperparams = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 1024}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # title + run-both button
        top_row = QWidget()
        tr_layout = QHBoxLayout(top_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Prompt Lab")
        title.setObjectName("lbl-accent")
        tr_layout.addWidget(title)
        tr_layout.addStretch()

        run_both = QPushButton("▶▶ run both")
        run_both.setObjectName("btn-primary")
        run_both.clicked.connect(self._run_both)
        tr_layout.addWidget(run_both)
        root.addWidget(top_row)

        # columns
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._col_a = _PromptColumn("A")
        self._col_b = _PromptColumn("B")

        for col in (self._col_a, self._col_b):
            splitter.addWidget(col)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # Diff view placeholder (will be filled in Phase 3.2)
        self._diff_box = QFrame()
        self._diff_box.setObjectName("panel")
        self._diff_box.setFixedHeight(64)
        db_layout = QVBoxLayout(self._diff_box)
        db_layout.setContentsMargins(12, 6, 12, 6)
        
        lbl = QLabel("DIFFERENCE VIEW (PHASE 3.2)")
        lbl.setObjectName("lbl-muted")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        db_layout.addWidget(lbl)
        
        root.addWidget(self._diff_box)

    def _run_both(self):
        self._col_a.start_run(self._hyperparams)
        self._col_b.start_run(self._hyperparams)
