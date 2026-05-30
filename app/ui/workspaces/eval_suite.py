"""
Eval Suite — run the harness, view results.
"""

from __future__ import annotations

import json
import os
import html

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QFileDialog, QProgressBar, QTreeWidget,
    QTreeWidgetItem, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from app.ui.themes import MONO


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

    def __init__(self, dataset_path: str, workflow_name: str, rag):
        super().__init__()
        self.dataset_path = dataset_path
        self.workflow_name = workflow_name
        self.rag = rag

    def run(self):
        try:
            from eval.harness import EvalHarness
            harness = EvalHarness(self.rag)
            report = harness.run(
                self.dataset_path,
                workflow_name=self.workflow_name,
                progress_cb=self.progress.emit
            )
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
        layout.setSpacing(12)

        # Dataset Panel
        dataset_panel = QWidget()
        dataset_panel.setObjectName("panel")
        dp_layout = QVBoxLayout(dataset_panel)
        dp_layout.setContentsMargins(12, 12, 12, 12)
        dp_layout.setSpacing(8)
        
        dp_layout.addWidget(_section("EVAL DATASET"))

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
        dp_layout.addWidget(row)

        # Workflow selection
        from core.workflows import list_workflows
        wf_row = QWidget()
        wfl = QHBoxLayout(wf_row)
        wfl.setContentsMargins(0, 0, 0, 0)
        wfl.setSpacing(8)
        
        wf_lbl = QLabel("Workflow:")
        wf_lbl.setFixedWidth(70)
        wfl.addWidget(wf_lbl)
        
        self._workflow_combo = QComboBox()
        for name, label in list_workflows():
            self._workflow_combo.addItem(f"{label} ({name})", name)
        wfl.addWidget(self._workflow_combo, 1)
        dp_layout.addWidget(wf_row)

        layout.addWidget(dataset_panel)

        # Run/Control Panel
        control_panel = QWidget()
        control_panel.setObjectName("panel")
        cp_layout = QVBoxLayout(control_panel)
        cp_layout.setContentsMargins(12, 12, 12, 12)
        cp_layout.setSpacing(10)

        cp_layout.addWidget(_section("RUN CONTROL"))

        self._run_btn = QPushButton("▶ Run Evaluation")
        self._run_btn.setObjectName("btn-primary")
        self._run_btn.clicked.connect(self._run)
        cp_layout.addWidget(self._run_btn)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(12)
        cp_layout.addWidget(self._progress)

        cp_layout.addWidget(_hline())
        cp_layout.addWidget(_section("METRICS SUMMARY"))

        self._summary_lbl = QLabel("no results yet")
        self._summary_lbl.setObjectName("lbl-muted")
        self._summary_lbl.setWordWrap(True)
        self._summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        cp_layout.addWidget(self._summary_lbl)

        layout.addWidget(control_panel)
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
        self._results_tree.setColumnWidth(0, 220)
        self._results_tree.setColumnWidth(1, 100)
        self._results_tree.setColumnWidth(2, 60)
        self._results_tree.currentItemChanged.connect(self._on_result_selected)
        layout.addWidget(self._results_tree, 1)

        layout.addWidget(_section("DETAIL"))

        self._detail_view = QTextBrowser()
        self._detail_view.setPlaceholderText("select a result to inspect")
        self._detail_view.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._detail_view, 1)

        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select eval dataset", "", "JSONL (*.jsonl);;All Files (*)"
        )
        if path:
            self._dataset_path.setText(path)
            # Auto-detect workflow matching filename
            filename = os.path.basename(path).lower()
            for i in range(self._workflow_combo.count()):
                wf_name = self._workflow_combo.itemData(i)
                if wf_name in filename:
                    self._workflow_combo.setCurrentIndex(i)
                    break

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

        workflow = self._workflow_combo.currentData()

        self._thread = _EvalThread(path, workflow, self.state.rag)
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

        total = report.total
        passed = report.passed
        failed = report.failed
        pass_rate = report.pass_rate

        self._summary_lbl.setText(
            f"<div style='margin-top:4px; font-size:10pt; line-height:1.4;'>"
            f"Total Cases: <b style='color:#E4E4F0;'>{total}</b><br/>"
            f"Passed: <b style='color:#2DD4A0;'>{passed}</b><br/>"
            f"Failed: <b style='color:#F05050;'>{failed}</b><br/>"
            f"Pass Rate: <b style='color:#00C2FF; font-size:12pt;'>{pass_rate:.1%}</b>"
            f"</div>"
        )

        self._results_tree.clear()
        for case in report.cases:
            case_passed = case.grade.get("passed", False) if case.grade else False
            preview_text = case.output.replace("\n", " ")[:80] if case.output else ""
            item = QTreeWidgetItem([
                case.case_id,
                case.grader,
                "✓" if case_passed else "✗",
                preview_text,
            ])
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            item.setForeground(2, QColor("#2DD4A0") if case_passed else QColor("#F05050"))
            item.setData(0, Qt.ItemDataRole.UserRole, case)
            self._results_tree.addTopLevelItem(item)

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._summary_lbl.setText(f"<span style='color:#F05050;'>error: {html.escape(msg)}</span>")

    def _on_result_selected(self, item, _prev):
        if not item:
            return
        case = item.data(0, Qt.ItemDataRole.UserRole)
        if case:
            case_passed = case.grade.get("passed", False) if case.grade else False
            status_text = "PASSED" if case_passed else "FAILED"
            status_color = "#2DD4A0" if case_passed else "#F05050"
            score = case.grade.get("score", 0.0) if case.grade else 0.0
            grader_detail = case.grade.get("detail", "") if case.grade else ""
            
            html_parts = [
                f"<div style='font-size:9.5pt; color:#E4E4F0; font-family:{MONO}; line-height:1.4;'>"
                f"<div style='border-bottom:1px solid #252535; padding-bottom:8px; margin-bottom:12px;'>"
                f"<span style='font-size:10.5pt;'>Case ID: <b style='color:#00C2FF;'>{html.escape(case.case_id)}</b></span>"
                f"<span style='float:right; background:{status_color}20; color:{status_color}; border:1px solid {status_color}; border-radius:4px; padding:2px 8px; font-weight:bold; font-size:8.5pt;'>{status_text}</span>"
                f"</div>"
                
                f"<div style='font-size:8.5pt; color:#9090A8; margin-bottom:12px;'>"
                f"Grader: <b>{html.escape(case.grader)}</b> &middot; "
                f"Score: <b>{score:.2f}</b> &middot; "
                f"Latency: <b>{case.latency_s:.2f}s</b>"
                f"</div>"
            ]

            if grader_detail:
                detail_bg = "#161625" if case_passed else "#201414"
                detail_border = "#252535" if case_passed else "#401818"
                detail_text_color = "#9090A8" if case_passed else "#F05050"
                html_parts.append(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:#505068; margin-bottom:4px; letter-spacing:1px;'>GRADER DETAIL</div>"
                    f"<div style='background:{detail_bg}; border:1px solid {detail_border}; border-radius:4px; padding:8px 12px; color:{detail_text_color}; font-size:9pt; white-space:pre-wrap;'>{html.escape(grader_detail)}</div>"
                    f"</div>"
                )

            if case.error:
                html_parts.append(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:#F05050; margin-bottom:4px; letter-spacing:1px;'>ERROR</div>"
                    f"<div style='background:#201414; border:1px solid #401818; border-radius:4px; padding:8px 12px; color:#F05050; font-size:9pt; white-space:pre-wrap;'>{html.escape(case.error)}</div>"
                    f"</div>"
                )

            html_parts.append(
                f"<div style='margin-bottom:12px;'>"
                f"<div style='font-size:7.5pt; font-weight:bold; color:#505068; margin-bottom:4px; letter-spacing:1px;'>PROMPT</div>"
                f"<div style='background:#111119; border:1px solid #252535; border-radius:4px; padding:8px 12px; color:#E4E4F0; white-space:pre-wrap;'>{html.escape(case.prompt)}</div>"
                f"</div>"
            )

            html_parts.append(
                f"<div style='margin-bottom:12px;'>"
                f"<div style='font-size:7.5pt; font-weight:bold; color:#505068; margin-bottom:4px; letter-spacing:1px;'>OUTPUT</div>"
                f"<div style='background:#0A0A14; border:1px solid #252535; border-radius:4px; padding:8px 12px; color:#505080; white-space:pre-wrap;'>{html.escape(case.output)}</div>"
                f"</div>"
            )

            if case.context_used:
                context_html = ""
                for idx, chunk in enumerate(case.context_used, 1):
                    context_html += f"<div style='border-bottom:1px solid #1C1C2A; padding-bottom:6px; margin-bottom:6px; font-size:8.5pt; color:#9090A8;'>[Chunk {idx}]</div>"
                    context_html += f"<div style='margin-bottom:10px; font-size:8.5pt; color:#9090A8; white-space:pre-wrap;'>{html.escape(chunk)}</div>"
                
                html_parts.append(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:#505068; margin-bottom:4px; letter-spacing:1px;'>CONTEXT USED</div>"
                    f"<div style='background:#14141F; border:1px solid #252535; border-radius:4px; padding:8px 12px;'>{context_html}</div>"
                    f"</div>"
                )

            html_parts.append("</div>")
            self._detail_view.setHtml("".join(html_parts))
