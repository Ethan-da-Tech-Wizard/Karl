"""
Prompt Lab — side-by-side prompt engineering workspace.

Left prompt (A) vs right prompt (B): run both, compare outputs.
All runs are logged to trace.
"""

from __future__ import annotations

import json
import os
import re
import html
import difflib

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QTextEdit, QLabel,
    QFrame, QComboBox, QListWidget, QLineEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from app.ui.themes import MONO


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def generate_char_diff_html(a: str, b: str) -> str:
    """
    Computes character-level diff and returns HTML with highlighted additions/deletions.
    Preserves text spaces and newlines using pre-wrap wrapper.
    """
    diff = difflib.ndiff(list(a), list(b))
    html_parts = [
        f"<div style='font-family:{MONO}; font-size:9.5pt; color:#E4E4F0; line-height:1.5; white-space:pre-wrap;'>"
    ]
    
    current_op = None
    current_chunk = []
    
    def flush():
        nonlocal current_op, current_chunk
        if not current_chunk:
            return
        text = "".join(current_chunk)
        escaped = html.escape(text)
        if current_op == '-':
            # Deletion (in A, not in B)
            html_parts.append(
                f"<span style='background-color: rgba(240, 80, 80, 0.2); "
                f"color: #F05050; text-decoration: line-through;'>{escaped}</span>"
            )
        elif current_op == '+':
            # Addition (in B, not in A)
            html_parts.append(
                f"<span style='background-color: rgba(45, 212, 160, 0.2); "
                f"color: #2DD4A0;'>{escaped}</span>"
            )
        else:
            # Unchanged
            html_parts.append(escaped)
        current_chunk = []
        
    for code in diff:
        op = code[0]
        char = code[2:]
        if op == '?':
            continue
            
        if op != current_op:
            flush()
            current_op = op
            
        current_chunk.append(char)
        
    flush()
    html_parts.append("</div>")
    return "".join(html_parts)


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
    generation_done = pyqtSignal(str)      # response text

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

    def set_system_text(self, text: str):
        self._system_edit.setPlainText(text)

    def set_user_text(self, text: str):
        self._user_edit.setPlainText(text)

    def clear_output(self):
        self._output.clear()

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

    def _on_done(self, response: str):
        self.generation_done.emit(response)

    def _on_error(self, msg: str):
        self._output.append(f"\n[error: {msg}]")


# ── workspace ─────────────────────────────────────────────────────────────────

class PromptLabWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._hyperparams = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 1024}
        self._output_a = ""
        self._output_b = ""
        self._pairs_dir = "data/prompt_pairs"
        os.makedirs(self._pairs_dir, exist_ok=True)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left panel: saved pairs list
        root.addWidget(self._build_left_panel())

        # Right panel: A/B execution space
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Title row + run both
        top_row = QWidget()
        tr_layout = QHBoxLayout(top_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Prompt Lab")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        tr_layout.addWidget(title)
        tr_layout.addStretch()

        run_both = QPushButton("▶▶ Run Both")
        run_both.setObjectName("btn-primary")
        run_both.clicked.connect(self._run_both)
        tr_layout.addWidget(run_both)
        right_layout.addWidget(top_row)

        # Splitter columns
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._col_a = _PromptColumn("A")
        self._col_b = _PromptColumn("B")

        self._col_a.run_requested.connect(self._run_column)
        self._col_b.run_requested.connect(self._run_column)

        self._col_a.generation_done.connect(self._on_col_a_done)
        self._col_b.generation_done.connect(self._on_col_b_done)

        splitter.addWidget(self._col_a)
        splitter.addWidget(self._col_b)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        right_layout.addWidget(splitter, 1)

        # Difference view panel
        self._diff_box = QWidget()
        self._diff_box.setObjectName("panel")
        db_layout = QVBoxLayout(self._diff_box)
        db_layout.setContentsMargins(12, 12, 12, 12)
        db_layout.setSpacing(6)
        
        db_layout.addWidget(_section("DIFFERENCE VIEW (A vs B)"))
        
        self._diff_view = QTextBrowser()
        self._diff_view.setPlaceholderText("Difference view will render here after both outputs complete...")
        self._diff_view.setTextFormat(Qt.TextFormat.RichText)
        self._diff_view.setFixedHeight(180)
        db_layout.addWidget(self._diff_view)
        
        right_layout.addWidget(self._diff_box)

        root.addWidget(right_widget, 1)

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("panel")
        w.setFixedWidth(220)
        
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        layout.addWidget(_section("PROMPT PAIRS"))
        
        self._pairs_list = QListWidget()
        self._pairs_list.currentTextChanged.connect(self._on_pair_selected)
        layout.addWidget(self._pairs_list, 1)
        self._refresh_pairs()
        
        # Save input and controls
        save_section = QWidget()
        ssl = QVBoxLayout(save_section)
        ssl.setContentsMargins(0, 4, 0, 0)
        ssl.setSpacing(6)
        
        self._pair_name_input = QLineEdit()
        self._pair_name_input.setPlaceholderText("Pair name...")
        ssl.addWidget(self._pair_name_input)
        
        self._save_btn = QPushButton("Save Pair")
        self._save_btn.setObjectName("btn-primary")
        self._save_btn.clicked.connect(self._save_pair)
        ssl.addWidget(self._save_btn)
        
        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setObjectName("btn-danger")
        self._delete_btn.clicked.connect(self._delete_pair)
        ssl.addWidget(self._delete_btn)
        
        layout.addWidget(save_section)
        return w

    def _refresh_pairs(self):
        self._pairs_list.clear()
        if not os.path.exists(self._pairs_dir):
            return
        files = [f for f in os.listdir(self._pairs_dir) if f.endswith(".json")]
        for f in sorted(files):
            name = os.path.splitext(f)[0]
            self._pairs_list.addItem(name)

    def _on_pair_selected(self, name: str):
        if not name:
            return
        path = os.path.join(self._pairs_dir, f"{name}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self._col_a.set_system_text(data.get("system_a", ""))
                self._col_a.set_user_text(data.get("user_a", ""))
                self._col_b.set_system_text(data.get("system_b", ""))
                self._col_b.set_user_text(data.get("user_b", ""))
                self._pair_name_input.setText(name)
                
                # Reset outputs and diff
                self._col_a.clear_output()
                self._col_b.clear_output()
                self._diff_view.clear()
                self._output_a = ""
                self._output_b = ""
            except Exception as e:
                print(f"[PromptLab] Error loading pair '{name}': {e}")

    def _save_pair(self):
        name = self._pair_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a name for the prompt pair.")
            return
            
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
        if safe_name != name:
            name = safe_name
            self._pair_name_input.setText(name)
            
        data = {
            "name": name,
            "system_a": self._col_a.system_text(),
            "user_a": self._col_a.user_text(),
            "system_b": self._col_b.system_text(),
            "user_b": self._col_b.user_text(),
        }
        
        path = os.path.join(self._pairs_dir, f"{name}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self._pairs_list.blockSignals(True)
            self._refresh_pairs()
            
            items = self._pairs_list.findItems(name, Qt.MatchFlag.MatchExact)
            if items:
                self._pairs_list.setCurrentItem(items[0])
            self._pairs_list.blockSignals(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save pair: {e}")

    def _delete_pair(self):
        item = self._pairs_list.currentItem()
        if not item:
            return
        name = item.text()
        
        reply = QMessageBox.question(
            self, "Delete Pair",
            f"Are you sure you want to delete prompt pair '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            path = os.path.join(self._pairs_dir, f"{name}.json")
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    QMessageBox.critical(self, "Delete Error", f"Could not delete file: {e}")
                    return
            
            self._pair_name_input.clear()
            self._refresh_pairs()

    def _run_column(self, label: str, _user_text: str):
        if label == "A":
            self._output_a = ""
            self._diff_view.setHtml("<span style='color:#9090A8;'>Generating output A...</span>")
            self._col_a.start_run(self._hyperparams)
        else:
            self._output_b = ""
            self._diff_view.setHtml("<span style='color:#9090A8;'>Generating output B...</span>")
            self._col_b.start_run(self._hyperparams)

    def _run_both(self):
        self._output_a = ""
        self._output_b = ""
        self._diff_view.setHtml("<span style='color:#9090A8;'>Generating outputs A and B...</span>")
        self._col_a.start_run(self._hyperparams)
        self._col_b.start_run(self._hyperparams)

    def _on_col_a_done(self, text: str):
        self._output_a = text
        self._update_diff()

    def _on_col_b_done(self, text: str):
        self._output_b = text
        self._update_diff()

    def _update_diff(self):
        if not self._output_a or not self._output_b:
            self._diff_view.setHtml(
                "<span style='color:#505068;'>Waiting for both outputs to complete before rendering diff...</span>"
            )
            return
            
        try:
            diff_html = generate_char_diff_html(self._output_a, self._output_b)
            self._diff_view.setHtml(diff_html)
        except Exception as e:
            self._diff_view.setHtml(f"<span style='color:#F05050;'>Error generating diff: {html.escape(str(e))}</span>")
