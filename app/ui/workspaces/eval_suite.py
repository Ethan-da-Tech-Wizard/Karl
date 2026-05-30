"""
Eval Suite — run the harness, view results.
"""

from __future__ import annotations

import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QFileDialog, QProgressBar, QTreeWidget,
    QTreeWidgetItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


# ── eval thread ───────────────────────────────────────────────────────────────

class _EvalThread(QThread):
    progress = pyqtSignal(int, int)    # current, total
    done     = pyqtSignal(object)      # EvalReport
    error    = pyqtSignal(str)

    def __init__(self, dataset_path: str, rag):
        super().__init__()
        self.dataset_path = dataset_path
        self.rag = rag

    def run(self):
        try:
            from eval.harness import EvalHarness
            harness = EvalHarness(self.rag)
            report = harness.run(self.dataset_path, progress_cb=self.progress.emit)
            self.done.emit(report)
        except Exception as e:
            self.error.emit(str(e))


# ── workspace ─────────────────────────────────────────────────────────────────

class EvalSuiteWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

    def _build_left(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section("DATASET"))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        self._dataset_path = QLineEdit()
        self._dataset_path.setPlaceholderText("path to eval dataset.jsonl")
        self._dataset_path.setReadOnly(True)
        rl.addWidget(self._dataset_path, 1)
        browse = QPushButton("…")
        browse.setFixedWidth(32)
        browse.clicked.connect(self._browse)
        rl.addWidget(browse)
        layout.addWidget(row)

        layout.addWidget(_hline())
        layout.addWidget(_section("RUN"))

        self._run_btn = QPushButton("▶ run eval")
        self._run_btn.setObjectName("btn-primary")
        self._run_btn.clicked.connect(self._run)
        layout.addWidget(self._run_btn)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        layout.addWidget(_hline())
        layout.addWidget(_section("SUMMARY"))

        self._summary_lbl = QLabel("no results yet")
        self._summary_lbl.setObjectName("lbl-muted")
        self._summary_lbl.setWordWrap(True)
        layout.addWidget(self._summary_lbl)

        layout.addStretch()
        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section("RESULTS"))

        self._results_tree = QTreeWidget()
        self._results_tree.setHeaderLabels(["case", "grader", "pass", "response"])
        self._results_tree.setColumnWidth(0, 180)
        self._results_tree.setColumnWidth(1, 100)
        self._results_tree.setColumnWidth(2, 50)
        self._results_tree.currentItemChanged.connect(self._on_result_selected)
        layout.addWidget(self._results_tree, 2)

        layout.addWidget(_section("DETAIL"))

        self._detail_view = QTextBrowser()
        self._detail_view.setPlaceholderText("select a result to inspect")
        layout.addWidget(self._detail_view, 1)

        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select eval dataset", "", "JSONL (*.jsonl);;All Files (*)"
        )
        if path:
            self._dataset_path.setText(path)

    def _run(self):
        path = self._dataset_path.text().strip()
        if not path:
            self._summary_lbl.setText("select a dataset first")
            return
        if not os.path.exists(path):
            self._summary_lbl.setText(f"file not found: {path}")
            return

        self._run_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._results_tree.clear()
        self._summary_lbl.setText("running...")

        self._thread = _EvalThread(path, self.state.rag)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    def _on_done(self, report):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)

        s = report.summary
        self._summary_lbl.setText(
            f"{s.get('total_cases', 0)} cases  ·  "
            f"{s.get('passed', 0)} passed  ·  "
            f"{s.get('pass_rate', 0):.1%} pass rate"
        )

        self._results_tree.clear()
        for case in report.cases:
            item = QTreeWidgetItem([
                case.get("id", "—"),
                case.get("grader", "—"),
                "✓" if case.get("passed") else "✗",
                case.get("response", "")[:80],
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, case)
            self._results_tree.addTopLevelItem(item)

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._summary_lbl.setText(f"error: {msg}")

    def _on_result_selected(self, item, _prev):
        if not item:
            return
        case = item.data(0, Qt.ItemDataRole.UserRole)
        if case:
            self._detail_view.setPlainText(
                json.dumps(case, indent=2, ensure_ascii=False)
            )
