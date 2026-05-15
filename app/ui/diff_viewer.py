"""
Prompt Diff Viewer — M17
========================
Opens as a modal dialog from the main window.  Lets the user pick two trace
entries from data/logs/traces/ and see them side-by-side: workflow, template,
hyperparams, RAG context, reasoning trace, and final response.

Usage (from MainWindow):
    from app.ui.diff_viewer import DiffViewerDialog
    dlg = DiffViewerDialog(self)
    dlg.exec()
"""

import json
import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

TRACE_DIR = "data/logs/traces"


def _load_all_entries() -> list[dict]:
    """Return all trace entries across all daily JSONL files, newest first."""
    entries = []
    if not os.path.isdir(TRACE_DIR):
        return entries
    for fname in sorted(os.listdir(TRACE_DIR), reverse=True):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(TRACE_DIR, fname)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entry["_source_file"] = fname
                    entries.append(entry)
                except json.JSONDecodeError:
                    pass
    return entries


def _entry_label(entry: dict, index: int) -> str:
    ts = entry.get("timestamp", "")[:19].replace("T", " ")
    wf = entry.get("workflow", "?")
    tpl = entry.get("template", "?")
    lat = entry.get("execution_time_seconds", 0)
    return f"[{index}]  {ts}  |  {wf}/{tpl}  |  {lat:.1f}s"


def _render_entry(entry: dict) -> str:
    """Return a human-readable block for one trace entry."""
    lines = []
    lines.append(f"Timestamp : {entry.get('timestamp', 'N/A')}")
    lines.append(f"Workflow  : {entry.get('workflow', 'N/A')}")
    lines.append(f"Template  : {entry.get('template', 'N/A')}")
    lines.append(f"Latency   : {entry.get('execution_time_seconds', 0):.2f}s")

    hp = entry.get("hyperparameters", {})
    if hp:
        lines.append(
            f"Hyperparams: temp={hp.get('temperature','?')}  "
            f"top_p={hp.get('top_p','?')}  "
            f"max_tokens={hp.get('max_tokens','?')}"
        )

    rag = entry.get("rag_context_used", [])
    lines.append(f"\nRAG chunks ({len(rag)}):")
    for i, chunk in enumerate(rag[:3], 1):
        preview = str(chunk)[:120].replace("\n", " ")
        lines.append(f"  [{i}] {preview}…")
    if len(rag) > 3:
        lines.append(f"  … and {len(rag) - 3} more")

    lines.append("\n── Reasoning Trace ──────────────────────────────────")
    thought = entry.get("parsed_thought", "").strip()
    lines.append(thought[:2000] if thought else "(none)")

    lines.append("\n── Final Response ───────────────────────────────────")
    resp = entry.get("parsed_response", "").strip()
    lines.append(resp[:2000] if resp else "(none)")

    return "\n".join(lines)


class _EntryPanel(QWidget):
    """One side of the diff (label + combo + text display)."""

    def __init__(self, title: str, entries: list[dict], parent=None):
        super().__init__(parent)
        self._entries = entries

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{title}</b>"))

        self.combo = QComboBox()
        self.combo.addItem("— select a trace entry —", None)
        for i, e in enumerate(entries):
            self.combo.addItem(_entry_label(e, i), i)
        self.combo.currentIndexChanged.connect(self._on_select)
        layout.addWidget(self.combo)

        self.display = QTextBrowser()
        self.display.setStyleSheet(
            "background-color: #0F172A; color: #CBD5E1; "
            "font-family: 'Consolas', monospace; font-size: 9pt; "
            "border: 1px solid #334155; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.display)

    def _on_select(self, idx):
        entry_idx = self.combo.itemData(idx)
        if entry_idx is None:
            self.display.clear()
            return
        entry = self._entries[entry_idx]
        self.display.setPlainText(_render_entry(entry))

    def get_selected_entry(self) -> dict | None:
        idx = self.combo.itemData(self.combo.currentIndex())
        if idx is None:
            return None
        return self._entries[idx]


class DiffViewerDialog(QDialog):
    """
    Side-by-side trace diff dialog.

    Opens two _EntryPanel widgets in a horizontal splitter.
    A "Highlight Differences" button marks lines that differ between
    the two responses (simple line-level diff).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Diff Viewer — M17")
        self.resize(1300, 760)

        self._entries = _load_all_entries()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header info
        info = QLabel(
            f"<b>Trace entries loaded:</b> {len(self._entries)} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; Source: <code>{TRACE_DIR}/</code>"
        )
        info.setStyleSheet("color: #94A3B8; font-size: 9pt; padding: 4px;")
        layout.addWidget(info)

        if not self._entries:
            layout.addWidget(QLabel(
                "<i>No trace files found. Run a generation first.</i>"
            ))
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
            return

        # Two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._left  = _EntryPanel("Run A (Left)",  self._entries, self)
        self._right = _EntryPanel("Run B (Right)", self._entries, self)
        splitter.addWidget(self._left)
        splitter.addWidget(self._right)
        splitter.setSizes([640, 640])
        layout.addWidget(splitter)

        # Controls
        btn_row = QHBoxLayout()
        diff_btn = QPushButton("Highlight Response Differences")
        diff_btn.setStyleSheet("background-color: #1E3A5F; font-weight: bold; padding: 4px 12px;")
        diff_btn.clicked.connect(self._highlight_diff)
        btn_row.addWidget(diff_btn)

        clear_btn = QPushButton("Clear Highlights")
        clear_btn.clicked.connect(self._clear_highlights)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _highlight_diff(self):
        """Colour lines in each panel that differ from the other's response."""
        left_entry  = self._left.get_selected_entry()
        right_entry = self._right.get_selected_entry()

        if not left_entry or not right_entry:
            return

        left_resp  = (left_entry.get("parsed_response")  or "").splitlines()
        right_resp = (right_entry.get("parsed_response") or "").splitlines()

        max_lines = max(len(left_resp), len(right_resp))
        left_resp  += [""] * (max_lines - len(left_resp))
        right_resp += [""] * (max_lines - len(right_resp))

        differ_indices = {i for i in range(max_lines) if left_resp[i] != right_resp[i]}

        for panel, response_lines in (
            (self._left,  left_resp),
            (self._right, right_resp),
        ):
            self._apply_highlights(panel.display, response_lines, differ_indices)

    def _apply_highlights(self, display: QTextBrowser, lines: list[str], differ_indices: set[int]):
        """Highlight differing response lines in the full display text."""
        doc   = display.document()
        cursor = QTextCursor(doc)

        # fmt for differing lines
        diff_fmt = QTextCharFormat()
        diff_fmt.setBackground(QColor("#3B1F1F"))

        normal_fmt = QTextCharFormat()
        normal_fmt.setBackground(QColor("transparent"))

        # Walk through text blocks; match response section lines
        block = doc.begin()
        in_response = False
        resp_line_idx = 0

        while block.isValid():
            text = block.text()

            if "── Final Response" in text:
                in_response = True
                resp_line_idx = 0
                block = block.next()
                continue

            if in_response:
                fmt = diff_fmt if resp_line_idx in differ_indices else normal_fmt
                cursor.setPosition(block.position())
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                cursor.setCharFormat(fmt)
                resp_line_idx += 1

            block = block.next()

    def _clear_highlights(self):
        normal_fmt = QTextCharFormat()
        normal_fmt.setBackground(QColor("transparent"))
        for panel in (self._left, self._right):
            cursor = QTextCursor(panel.display.document())
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.setCharFormat(normal_fmt)
