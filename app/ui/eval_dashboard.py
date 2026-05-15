"""
Eval Dashboard — M18 + M19
===========================
M18: Browses eval/results/ JSONL reports and shows pass-rate history.
M19: Fires the EvalHarness against a chosen dataset from the UI.

Usage:
    from app.ui.eval_dashboard import EvalDashboardDialog
    dlg = EvalDashboardDialog(self)
    dlg.exec()
"""

import json
import os
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QHeaderView,
)

RESULTS_DIR = "eval/results"
DATASETS_DIR = "eval/datasets"


# ── M19: Background eval runner ───────────────────────────────────────────────

class EvalRunThread(QThread):
    """Runs EvalHarness.run() off the UI thread."""
    case_done   = pyqtSignal(int, int, str, bool, float)  # current, total, id, passed, score
    run_finished = pyqtSignal(object)   # EvalReport
    run_error    = pyqtSignal(str)

    def __init__(self, dataset_path: str, workflow_name: str):
        super().__init__()
        self.dataset_path  = dataset_path
        self.workflow_name = workflow_name

    def run(self):
        try:
            # Import here to avoid circular imports at module load time
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            ))))
            from eval.harness import EvalHarness

            harness = EvalHarness()

            # Monkey-patch _run_model to emit progress after each case
            _orig_run = harness.run.__func__

            def _patched_run(self_h, dataset_path, workflow_name, **kwargs):
                from core.workflows import get_workflow
                from core.prompt_templates import get_template
                import time

                workflow_cfg = get_workflow(workflow_name)
                template_name = kwargs.get("template_override") or workflow_cfg["template"]
                hp = kwargs.get("hyperparams") or {"max_tokens": 512, "temperature": 0.2, "top_p": 0.95}

                cases = self_h._load_dataset(dataset_path)
                total = len(cases)
                results = []

                for i, case in enumerate(cases, 1):
                    case_id = case.get("id", f"case_{i:03d}")
                    context_chunks = self_h._resolve_context(case, workflow_cfg)
                    system_prompt = self_h._build_system_prompt(template_name, context_chunks, case)

                    try:
                        output, latency = self_h._run_model(system_prompt, case.get("prompt", ""), hp)
                        grade = self_h._grade(output, case, context_chunks)
                        error = None
                    except Exception as e:
                        output, latency = "", 0.0
                        grade = {"passed": False, "score": 0.0, "detail": f"EXCEPTION: {e}"}
                        error = str(e)

                    from eval.harness import CaseResult
                    results.append(CaseResult(
                        case_id=case_id,
                        prompt=case.get("prompt", ""),
                        workflow=workflow_name,
                        template=template_name,
                        output=output,
                        grader=case.get("grader", "keyword_hit"),
                        grade=grade,
                        latency_s=round(latency, 3),
                        context_used=context_chunks,
                        error=error,
                    ))
                    self.case_done.emit(i, total, case_id, bool(grade.get("passed")), grade.get("score", 0.0))

                from eval.harness import EvalReport
                import statistics
                latencies = [r.latency_s for r in results]
                scores    = [r.grade.get("score", 0.0) for r in results]
                passed    = sum(1 for r in results if r.grade.get("passed"))
                errors    = sum(1 for r in results if r.error)

                return EvalReport(
                    workflow=workflow_name,
                    template=template_name,
                    dataset=dataset_path,
                    total=len(results),
                    passed=passed,
                    failed=len(results) - passed - errors,
                    errors=errors,
                    pass_rate=passed / len(results) if results else 0.0,
                    avg_latency_s=round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
                    avg_score=round(sum(scores) / len(scores), 3) if scores else 0.0,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    cases=results,
                )

            import types
            harness.run = types.MethodType(lambda s, dp, wn, **kw: _patched_run(s, dp, wn, **kw), harness)

            report = _patched_run(harness, self.dataset_path, self.workflow_name)
            harness.save_report(report)
            self.run_finished.emit(report)

        except Exception as e:
            self.run_error.emit(str(e))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_reports() -> list[dict]:
    """Return all summary dicts from eval/results/*.jsonl, newest first."""
    reports = []
    if not os.path.isdir(RESULTS_DIR):
        return reports
    for fname in sorted(os.listdir(RESULTS_DIR), reverse=True):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(RESULTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "summary":
                        obj["_file"] = fname
                        reports.append(obj)
                        break
                except json.JSONDecodeError:
                    pass
    return reports


def _load_report_cases(filename: str) -> list[dict]:
    fpath = os.path.join(RESULTS_DIR, filename)
    cases = []
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "case":
                    cases.append(obj)
            except json.JSONDecodeError:
                pass
    return cases


def _available_datasets() -> list[tuple[str, str]]:
    """Return [(display_name, full_path), ...]."""
    pairs = []
    if not os.path.isdir(DATASETS_DIR):
        return pairs
    for fname in sorted(os.listdir(DATASETS_DIR)):
        if fname.endswith(".jsonl"):
            pairs.append((fname.replace(".jsonl", ""), os.path.join(DATASETS_DIR, fname)))
    return pairs


# ── M18: History panel ────────────────────────────────────────────────────────

class _HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("<b>Past Eval Runs</b>"))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Timestamp", "Workflow", "Template", "Pass %", "Avg Score", "Latency"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.setStyleSheet(
            "QTableWidget { background: #0F172A; color: #CBD5E1; "
            "gridline-color: #1E293B; font-size: 9pt; }"
            "QHeaderView::section { background: #1E293B; color: #94A3B8; "
            "font-weight: bold; padding: 4px; }"
        )
        layout.addWidget(self.table)

        layout.addWidget(QLabel("<b>Case Breakdown</b>"))
        self.case_display = QTextBrowser()
        self.case_display.setStyleSheet(
            "background: #0F172A; color: #CBD5E1; font-family: 'Consolas'; "
            "font-size: 9pt; border: 1px solid #1E293B; border-radius: 4px;"
        )
        layout.addWidget(self.case_display)

        self._reports = []
        self.refresh()

    def refresh(self):
        self._reports = _load_reports()
        self.table.setRowCount(0)
        for r in self._reports:
            row = self.table.rowCount()
            self.table.insertRow(row)
            ts  = r.get("timestamp", "")[:19].replace("T", " ")
            pr  = r.get("pass_rate", 0)
            avg = r.get("avg_score", 0)
            lat = r.get("avg_latency_s", 0)

            self.table.setItem(row, 0, QTableWidgetItem(ts))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("workflow", "")))
            self.table.setItem(row, 2, QTableWidgetItem(r.get("template", "")))

            pr_item = QTableWidgetItem(f"{pr:.1%}")
            pr_item.setForeground(
                QColor("#10B981") if pr >= 0.8 else
                QColor("#F59E0B") if pr >= 0.5 else
                QColor("#EF4444")
            )
            self.table.setItem(row, 3, pr_item)
            self.table.setItem(row, 4, QTableWidgetItem(f"{avg:.3f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{lat:.2f}s"))

    def _on_select(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = self.table.currentRow()
        if row >= len(self._reports):
            return
        report = self._reports[row]
        fname = report.get("_file", "")
        if not fname:
            return
        cases = _load_report_cases(fname)
        lines = [
            f"{'✓' if c.get('grade', {}).get('passed') else '✗'}  "
            f"{c.get('case_id', '?'):<22}"
            f"  score={c.get('grade', {}).get('score', 0):.2f}"
            f"  lat={c.get('latency_s', 0):.1f}s\n"
            f"     {c.get('grade', {}).get('detail', '')}"
            for c in cases
        ]
        self.case_display.setPlainText("\n".join(lines))


# ── M19: Runner panel ─────────────────────────────────────────────────────────

class _RunnerPanel(QWidget):
    run_complete = pyqtSignal()  # notify history panel to refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("<b>Run Eval Against Loaded Model</b>"))

        ds_row = QHBoxLayout()
        ds_row.addWidget(QLabel("Dataset:"))
        self.ds_combo = QComboBox()
        for name, path in _available_datasets():
            self.ds_combo.addItem(name, path)
        ds_row.addWidget(self.ds_combo)
        layout.addLayout(ds_row)

        from core.workflows import list_workflows
        wf_row = QHBoxLayout()
        wf_row.addWidget(QLabel("Workflow:"))
        self.wf_combo = QComboBox()
        for wf_name, wf_label in list_workflows():
            self.wf_combo.addItem(wf_label, wf_name)
        wf_row.addWidget(self.wf_combo)
        layout.addLayout(wf_row)

        self.run_btn = QPushButton("▶  Run Eval")
        self.run_btn.setStyleSheet("background-color: #1E3A5F; font-weight: bold; padding: 6px;")
        self.run_btn.clicked.connect(self._start_run)
        layout.addWidget(self.run_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #1E293B; border-radius: 4px; color: #CBD5E1; }"
            "QProgressBar::chunk { background: #2563EB; border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        self.status_display = QTextBrowser()
        self.status_display.setStyleSheet(
            "background: #0F172A; color: #6EE7B7; font-family: 'Consolas'; "
            "font-size: 9pt; border: 1px solid #1E293B; border-radius: 4px;"
        )
        self.status_display.setMaximumHeight(220)
        layout.addWidget(self.status_display)

        self._thread = None

    def _start_run(self):
        ds_path = self.ds_combo.currentData()
        wf_name = self.wf_combo.currentData()
        if not ds_path or not wf_name:
            return
        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_display.clear()
        self.status_display.append(f"Starting: {os.path.basename(ds_path)} / {wf_name}\n")

        self._thread = EvalRunThread(ds_path, wf_name)
        self._thread.case_done.connect(self._on_case_done)
        self._thread.run_finished.connect(self._on_finished)
        self._thread.run_error.connect(self._on_error)
        self._thread.start()

    def _on_case_done(self, current: int, total: int, case_id: str, passed: bool, score: float):
        pct = int(current / total * 100)
        self.progress_bar.setValue(pct)
        status = "✓" if passed else "✗"
        self.status_display.append(f"  [{status}] {case_id:<22} score={score:.2f}")

    def _on_finished(self, report):
        self.run_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_display.append(
            f"\n── Summary ──────────────────────────────\n"
            f"  Pass rate : {report.pass_rate:.1%}  ({report.passed}/{report.total})\n"
            f"  Avg score : {report.avg_score:.3f}\n"
            f"  Avg latency: {report.avg_latency_s:.2f}s\n"
            f"  Report saved to eval/results/"
        )
        self.run_complete.emit()

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.status_display.append(f"\n❌ Error: {msg}")


# ── Dialog ────────────────────────────────────────────────────────────────────

class EvalDashboardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Eval Dashboard — M18/M19")
        self.resize(1200, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._history = _HistoryPanel(self)
        self._runner  = _RunnerPanel(self)
        self._runner.run_complete.connect(self._history.refresh)

        splitter.addWidget(self._history)
        splitter.addWidget(self._runner)
        splitter.setSizes([760, 420])

        layout.addWidget(splitter)

        close_row = QHBoxLayout()
        refresh_btn = QPushButton("↻ Refresh History")
        refresh_btn.clicked.connect(self._history.refresh)
        close_row.addWidget(refresh_btn)
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
