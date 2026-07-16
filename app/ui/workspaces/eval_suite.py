"""
Eval Suite — run the harness, view results.
"""

from __future__ import annotations

import logging

import json
import os
import html
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QFileDialog, QProgressBar, QTreeWidget,
    QTreeWidgetItem, QComboBox, QTabWidget, QListWidget,
    QTextEdit, QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from app.ui.themes import MONO


logger = logging.getLogger("karl.eval_suite")


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

    def __init__(self, dataset_path: str, workflow_name: str, rag, model_name: str | None = None, adapter_name: str | None = None):
        super().__init__()
        self.dataset_path = dataset_path
        self.workflow_name = workflow_name
        self.rag = rag
        self.model_name = model_name
        self.adapter_name = adapter_name

    def run(self):
        try:
            from eval.harness import EvalHarness
            harness = EvalHarness(self.rag)
            report = harness.run(
                self.dataset_path,
                workflow_name=self.workflow_name,
                progress_cb=self.progress.emit,
                model_name=self.model_name,
                adapter_name=self.adapter_name
            )
            self.done.emit(report)
            try:
                from app.utils.training_curator import save_eval_result
                items = []
                for case in getattr(report, "cases", []):
                    grade = case.grade or {}
                    items.append({
                        "system_prompt": "",
                        "question": case.prompt,
                        "model_response": case.output or "",
                        "expected_answer": grade.get("detail", ""),
                        "passed": grade.get("passed", False),
                        "score": grade.get("score", 0.0),
                    })
                report_dict = {
                    "model_name": self.model_name or "unknown",
                    "adapter_name": self.adapter_name,
                    "dataset_name": self.dataset_path,
                    "accuracy": report.pass_rate,
                    "mrr": getattr(report, "mrr", 0.0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "items": items,
                }
                save_eval_result(report_dict)
            except Exception as e:
                logger.warning(f"Failed to auto-save eval report: {e}")
        except Exception as e:
            self.error.emit(str(e))


# ── workspace ─────────────────────────────────────────────────────────────────

class EvalSuiteWorkspace(QWidget):
    """Evaluation workspace for dataset editing, execution, and report review."""

    def __init__(self, state, parent=None):
        """Initialize loaded-case state and build the split evaluation UI."""
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._active_threads = set()
        self._loaded_cases = []
        self._build_ui()

    def _build_ui(self):
        """Build dataset controls on the left and reports/details on the right."""
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

        # Tab Widget for Left Panel
        self._left_tabs = QTabWidget()
        self._left_tabs.setObjectName("left-tabs")

        # ── TAB 1: RUN CONFIG ───────────────────────────────────────────────
        run_tab = QWidget()
        run_layout = QVBoxLayout(run_tab)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(12)

        # Dataset Panel
        dataset_panel = QWidget()
        dataset_panel.setObjectName("panel")
        dp_layout = QVBoxLayout(dataset_panel)
        dp_layout.setContentsMargins(12, 12, 12, 12)
        dp_layout.setSpacing(8)
        
        dp_layout.addWidget(_section("EVAL DATASET"))

        desc = QLabel(
            "Benchmark test suite. Load an evaluation dataset of questions and expected answers "
            "to test a selected workflow, assessing accuracy and grading pass rates."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px;")
        dp_layout.addWidget(desc)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        self._dataset_path = QLineEdit()
        self._dataset_path.setPlaceholderText("path to eval dataset.jsonl")
        self._dataset_path.setReadOnly(True)
        self._dataset_path.setToolTip("Path to the dataset file (JSONL format) to benchmark")
        rl.addWidget(self._dataset_path, 1)
        browse = QPushButton("…")
        browse.setFixedWidth(32)
        browse.setToolTip("Browse files to select a benchmark dataset JSONL")
        browse.clicked.connect(self._browse)
        rl.addWidget(browse)
        dp_layout.addWidget(row)

        # Model / Adapter selection
        model_row = QWidget()
        ml = QHBoxLayout(model_row)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)
        
        model_lbl = QLabel("Model:")
        model_lbl.setFixedWidth(70)
        ml.addWidget(model_lbl)
        
        self._model_combo = QComboBox()
        self._model_combo.setToolTip("Select model/adapter combination to use during evaluation runs")
        ml.addWidget(self._model_combo, 1)
        dp_layout.addWidget(model_row)

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
        self._workflow_combo.setToolTip("Select workflow context to use during evaluation runs")
        wfl.addWidget(self._workflow_combo, 1)
        dp_layout.addWidget(wf_row)

        run_layout.addWidget(dataset_panel)

        # Run/Control Panel
        control_panel = QWidget()
        control_panel.setObjectName("panel")
        cp_layout = QVBoxLayout(control_panel)
        cp_layout.setContentsMargins(12, 12, 12, 12)
        cp_layout.setSpacing(10)

        cp_layout.addWidget(_section("RUN CONTROL"))

        self._run_btn = QPushButton("▶ Run Evaluation")
        self._run_btn.setObjectName("btn-primary")
        self._run_btn.setToolTip("Execute benchmark test cases on the currently active model")
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

        run_layout.addWidget(control_panel)
        run_layout.addStretch()
        self._left_tabs.addTab(run_tab, "Run Config")

        # ── TAB 2: EDIT DATASET ─────────────────────────────────────────────
        edit_tab = QWidget()
        edit_layout = QVBoxLayout(edit_tab)
        edit_layout.setContentsMargins(12, 12, 12, 12)
        edit_layout.setSpacing(8)

        edit_layout.addWidget(_section("EDIT DATASET CASES"))

        # List of cases
        self._edit_cases_list = QListWidget()
        self._edit_cases_list.setToolTip("List of test cases in the loaded dataset")
        self._edit_cases_list.setFixedHeight(110)
        self._edit_cases_list.currentItemChanged.connect(self._on_edit_case_selected)
        edit_layout.addWidget(self._edit_cases_list)

        # Add / Delete buttons
        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(8)

        self._add_case_btn = QPushButton("＋ Add Case")
        self._add_case_btn.setToolTip("Add a new test case to the dataset")
        self._add_case_btn.clicked.connect(self._add_case)
        brl.addWidget(self._add_case_btn)

        self._delete_case_btn = QPushButton("－ Delete Case")
        self._delete_case_btn.setObjectName("btn-danger")
        self._delete_case_btn.setToolTip("Remove the selected test case")
        self._delete_case_btn.clicked.connect(self._delete_case)
        brl.addWidget(self._delete_case_btn)

        edit_layout.addWidget(btn_row)
        edit_layout.addWidget(_hline())

        # Form layout for selected case details
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(6)

        # Case ID
        id_row = QWidget()
        id_l = QHBoxLayout(id_row)
        id_l.setContentsMargins(0, 0, 0, 0)
        id_lbl = QLabel("Case ID:")
        id_lbl.setFixedWidth(70)
        id_l.addWidget(id_lbl)
        self._edit_case_id = QLineEdit()
        self._edit_case_id.setPlaceholderText("e.g. grnd_011")
        self._edit_case_id.textChanged.connect(self._save_current_form_to_memory)
        id_l.addWidget(self._edit_case_id)
        form_layout.addWidget(id_row)

        # Prompt
        prompt_row = QWidget()
        pl = QHBoxLayout(prompt_row)
        pl.setContentsMargins(0, 0, 0, 0)
        prompt_lbl = QLabel("Prompt:")
        prompt_lbl.setFixedWidth(70)
        prompt_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        pl.addWidget(prompt_lbl)
        self._edit_case_prompt = QTextEdit()
        self._edit_case_prompt.setPlaceholderText("user question...")
        self._edit_case_prompt.setFixedHeight(45)
        self._edit_case_prompt.textChanged.connect(self._save_current_form_to_memory)
        pl.addWidget(self._edit_case_prompt)
        form_layout.addWidget(prompt_row)

        # Context
        context_row = QWidget()
        cl = QHBoxLayout(context_row)
        cl.setContentsMargins(0, 0, 0, 0)
        context_lbl = QLabel("Context:")
        context_lbl.setFixedWidth(70)
        context_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        cl.addWidget(context_lbl)
        self._edit_case_context = QTextEdit()
        self._edit_case_context.setPlaceholderText("optional reference context...")
        self._edit_case_context.setFixedHeight(45)
        self._edit_case_context.textChanged.connect(self._save_current_form_to_memory)
        cl.addWidget(self._edit_case_context)
        form_layout.addWidget(context_row)

        # Expected
        expected_row = QWidget()
        el = QHBoxLayout(expected_row)
        el.setContentsMargins(0, 0, 0, 0)
        expected_lbl = QLabel("Expected:")
        expected_lbl.setFixedWidth(70)
        el.addWidget(expected_lbl)
        self._edit_case_expected = QLineEdit()
        self._edit_case_expected.setPlaceholderText("expected output substring...")
        self._edit_case_expected.textChanged.connect(self._save_current_form_to_memory)
        el.addWidget(self._edit_case_expected)
        form_layout.addWidget(expected_row)

        # Grader
        grader_row = QWidget()
        gl = QHBoxLayout(grader_row)
        gl.setContentsMargins(0, 0, 0, 0)
        grader_lbl = QLabel("Grader:")
        grader_lbl.setFixedWidth(70)
        gl.addWidget(grader_lbl)
        self._edit_case_grader = QComboBox()
        self._edit_case_grader.addItems(["keyword_hit", "exact_match", "json_valid", "groundedness", "not_in_context"])
        self._edit_case_grader.currentTextChanged.connect(self._on_grader_changed)
        gl.addWidget(self._edit_case_grader)
        form_layout.addWidget(grader_row)

        # Keywords
        self._kw_row = QWidget()
        self._kw_row_layout = QHBoxLayout(self._kw_row)
        self._kw_row_layout.setContentsMargins(0, 0, 0, 0)
        self._kw_lbl = QLabel("Keywords:")
        self._kw_lbl.setFixedWidth(70)
        self._kw_row_layout.addWidget(self._kw_lbl)
        self._edit_case_keywords = QLineEdit()
        self._edit_case_keywords.setPlaceholderText("comma-separated list...")
        self._edit_case_keywords.textChanged.connect(self._save_current_form_to_memory)
        self._kw_row_layout.addWidget(self._edit_case_keywords)
        form_layout.addWidget(self._kw_row)

        # Require All Checkbox
        self._req_row = QWidget()
        rl_layout = QHBoxLayout(self._req_row)
        rl_layout.setContentsMargins(0, 0, 0, 0)
        self._edit_case_req_all = QCheckBox("Require All Keywords")
        self._edit_case_req_all.stateChanged.connect(lambda state: self._save_current_form_to_memory())
        rl_layout.addWidget(self._edit_case_req_all)
        form_layout.addWidget(self._req_row)

        edit_layout.addWidget(form_widget)

        # Save dataset button
        self._save_dataset_btn = QPushButton("Save Dataset Changes")
        self._save_dataset_btn.setObjectName("btn-primary")
        self._save_dataset_btn.setToolTip("Save the current edited cases back to the JSONL dataset file")
        self._save_dataset_btn.clicked.connect(self._save_dataset)
        edit_layout.addWidget(self._save_dataset_btn)

        edit_layout.addStretch()
        self._left_tabs.addTab(edit_tab, "Edit Dataset")

        layout.addWidget(self._left_tabs)
        self._refresh_model_combo()
        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._right_tabs = QTabWidget()
        self._right_tabs.setObjectName("right-tabs")

        # Tab 1: Results List
        res_tab = QWidget()
        res_layout = QVBoxLayout(res_tab)
        res_layout.setContentsMargins(8, 8, 8, 8)
        res_layout.setSpacing(6)
        res_layout.addWidget(_section("RESULTS LIST"))

        # Filter & Export Row
        filter_row = QWidget()
        fr_lay = QHBoxLayout(filter_row)
        fr_lay.setContentsMargins(0, 0, 0, 0)
        fr_lay.setSpacing(10)
        
        self._filter_pass_chk = QCheckBox("Show Passed")
        self._filter_pass_chk.setChecked(True)
        self._filter_pass_chk.toggled.connect(self._apply_results_filter)
        fr_lay.addWidget(self._filter_pass_chk)
        
        self._filter_fail_chk = QCheckBox("Show Failed")
        self._filter_fail_chk.setChecked(True)
        self._filter_fail_chk.toggled.connect(self._apply_results_filter)
        fr_lay.addWidget(self._filter_fail_chk)
        
        fr_lay.addStretch()
        
        self._export_report_btn = QPushButton("Export Report")
        self._export_report_btn.setObjectName("btn-ghost")
        self._export_report_btn.setStyleSheet("font-size: 8pt; padding: 2px 6px;")
        self._export_report_btn.clicked.connect(self._export_eval_report)
        self._export_report_btn.setEnabled(False)
        fr_lay.addWidget(self._export_report_btn)
        
        res_layout.addWidget(filter_row)

        self._results_tree = QTreeWidget()
        self._results_tree.setHeaderLabels(["case", "grader", "pass", "response"])
        self._results_tree.setColumnWidth(0, 220)
        self._results_tree.setColumnWidth(1, 100)
        self._results_tree.setColumnWidth(2, 60)
        self._results_tree.currentItemChanged.connect(self._on_result_selected)
        res_layout.addWidget(self._results_tree, 1)

        self._right_tabs.addTab(res_tab, "Results List")


        # Tab 2: Detail Inspector
        detail_tab = QWidget()
        det_layout = QVBoxLayout(detail_tab)
        det_layout.setContentsMargins(8, 8, 8, 8)
        det_layout.setSpacing(6)
        det_layout.addWidget(_section("RESULT DETAILS"))

        self._detail_view = QTextBrowser()
        self._detail_view.setPlaceholderText("Select a result from the Results List tab to inspect details here...")
        det_layout.addWidget(self._detail_view, 1)

        self._right_tabs.addTab(detail_tab, "Detail Inspector")

        layout.addWidget(self._right_tabs, 1)
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select eval dataset", "", "JSONL (*.jsonl);;All Files (*)"
        )
        if path:
            self._dataset_path.setText(path)
            self._load_dataset_for_editing(path)
            # Auto-detect workflow matching filename
            filename = os.path.basename(path).lower()
            for i in range(self._workflow_combo.count()):
                wf_name = self._workflow_combo.itemData(i)
                if wf_name in filename:
                    self._workflow_combo.setCurrentIndex(i)
                    break

    def _run(self):
        # Preflight check
        from app.engine.model_loader import ModelLoader
        if not ModelLoader.is_loaded():
            QMessageBox.warning(
                self, "Preflight Failed",
                "No base model is currently loaded. Please load a model in the System Config tab first."
            )
            self._summary_lbl.setText("<span style='color:#F05050;'>Preflight failed: no model loaded</span>")
            return

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
        self._progress.setValue(0)
        self._results_tree.clear()
        self._summary_lbl.setText("running...")
        self._last_report = None
        self._export_report_btn.setEnabled(False)

        # Reset ETA variables
        self._eval_start_time = None

        workflow = self._workflow_combo.currentData()

        model_name = None
        adapter_name = None
        model_data = self._model_combo.itemData(self._model_combo.currentIndex())
        if model_data:
            model_name = model_data.get("model")
            adapter_name = model_data.get("adapter")

        self._thread = _EvalThread(path, workflow, self.state.rag, model_name=model_name, adapter_name=adapter_name)
        self._active_threads.add(self._thread)
        self._thread.finished.connect(
            lambda t=self._thread: self._active_threads.discard(t)
        )
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def run_suite(self):
        self._run()

    def _on_progress(self, current: int, total: int):
        import time
        if not getattr(self, "_eval_start_time", None):
            self._eval_start_time = time.time()
            
        elapsed = time.time() - self._eval_start_time
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        
        if current > 0:
            time_per_case = elapsed / current
            remaining_cases = total - current
            eta_s = time_per_case * remaining_cases
            eta_m = int(eta_s // 60)
            eta_sec = int(eta_s % 60)
            eta_str = f"{eta_m}m {eta_sec}s" if eta_m > 0 else f"{eta_sec}s"
            
            el_m = int(elapsed // 60)
            el_sec = int(elapsed % 60)
            el_str = f"{el_m}m {el_sec}s" if el_m > 0 else f"{el_sec}s"
            
            self._progress.setFormat(f"%v/%m | Case {current} of {total} | Elapsed: {el_str} | ETA: {eta_str}")
        else:
            self._progress.setFormat("%v/%m")


    def _on_done(self, report):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._last_report = report
        self._export_report_btn.setEnabled(True)

        total = report.total
        passed = report.passed
        failed = report.failed
        pass_rate = report.pass_rate

        # Compute block bar representing the pass rate (10 segments)
        filled = int(round(pass_rate * 10))
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        
        # Color coding for pass rate
        accent = self.state.custom_accent or "#00C2FF"

        self._summary_lbl.setText(
            f"<div style='margin-top:4px; font-size:10pt; line-height:1.5;'>"
            f"Total Cases: <b style='color:#E4E4F0;'>{total}</b><br/>"
            f"Passed: <b style='color:#2DD4A0;'>{passed}</b> &nbsp;&middot;&nbsp; Failed: <b style='color:#F05050;'>{failed}</b><br/>"
            f"Pass Rate: <b style='color:#E4E4F0;'>{pass_rate:.1%}</b><br/>"
            f"<span style='color:{accent}; font-family:monospace; font-size:12pt;'>[{bar}]</span>"
            f"</div>"
        )

        self._results_tree.clear()
        for case in report.cases:
            case_passed = case.grade.get("passed", False) if case.grade else False
            preview_text = case.output.replace("\n", " ")[:80] if case.output else ""
            item = QTreeWidgetItem([
                case.case_id,
                case.grader,
                "PASS" if case_passed else "FAIL",
                preview_text,
            ])
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            item.setForeground(2, QColor("#2DD4A0") if case_passed else QColor("#F05050"))
            item.setData(0, Qt.ItemDataRole.UserRole, case)
            self._results_tree.addTopLevelItem(item)

        self._apply_results_filter()


    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._summary_lbl.setText(f"<span style='color:#F05050;'>error: {html.escape(msg)}</span>")

    def _on_result_selected(self, item, _prev):
        if not item:
            return
        case = item.data(0, Qt.ItemDataRole.UserRole)
        if case:
            from app.ui.themes import get_theme_colors
            colors = get_theme_colors(self.state)
            accent = colors.get("accent", "#00C2FF")
            text_hi = colors.get("text_hi", "#E4E4F0")
            text_mid = colors.get("text_mid", "#9090A8")
            text_lo = colors.get("text_lo", "#505068")
            bg_deep = colors.get("bg_deep", "#0A0A14")
            bg_surface = colors.get("bg_surface", "#14141F")
            bg_raised = colors.get("bg_raised", "#161625")
            border = colors.get("border", "#252535")
            green = colors.get("green", "#2DD4A0")
            red = colors.get("red", "#F05050")
            self._right_tabs.setCurrentIndex(1)
            case_passed = case.grade.get("passed", False) if case.grade else False
            status_text = "PASSED" if case_passed else "FAILED"
            status_color = green if case_passed else red
            score = case.grade.get("score", 0.0) if case.grade else 0.0
            grader_detail = case.grade.get("detail", "") if case.grade else ""
            
            html_parts = [
                f"<div style='font-size:9.5pt; color:{text_hi}; font-family:{MONO}; line-height:1.4;'>"
                f"<div style='border-bottom:1px solid {border}; padding-bottom:8px; margin-bottom:12px;'>"
                f"<span style='font-size:10.5pt;'>Case ID: <b style='color:{accent};'>{html.escape(case.case_id)}</b></span>"
                f"<span style='float:right; background:{status_color}20; color:{status_color}; border:1px solid {status_color}; border-radius:4px; padding:2px 8px; font-weight:bold; font-size:8.5pt;'>{status_text}</span>"
                f"</div>"
                
                f"<div style='font-size:8.5pt; color:{text_mid}; margin-bottom:12px;'>"
                f"Grader: <b>{html.escape(case.grader)}</b> &middot; "
                f"Score: <b>{score:.2f}</b> &middot; "
                f"Latency: <b>{case.latency_s:.2f}s</b>"
                f"</div>"
            ]

            if grader_detail:
                detail_bg = bg_raised if case_passed else "#201414"
                detail_border = border if case_passed else "#401818"
                detail_text_color = text_mid if case_passed else red
                html_parts.append(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:{text_lo}; margin-bottom:4px; letter-spacing:1px;'>GRADER DETAIL</div>"
                    f"<div style='background:{detail_bg}; border:1px solid {detail_border}; border-radius:4px; padding:8px 12px; color:{detail_text_color}; font-size:9pt; white-space:pre-wrap;'>{html.escape(grader_detail)}</div>"
                    f"</div>"
                )

            if case.error:
                html_parts.append(
                    f"<div style='margin-bottom:12px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:{red}; margin-bottom:4px; letter-spacing:1px;'>ERROR</div>"
                    f"<div style='background:#201414; border:1px solid #401818; border-radius:4px; padding:8px 12px; color:{red}; font-size:9pt; white-space:pre-wrap;'>{html.escape(case.error)}</div>"
                    f"</div>"
                )

            html_parts.append(
                f"<div style='margin-bottom:14px;'>"
                f"<div style='font-size:7.5pt; font-weight:bold; color:{text_lo}; margin-bottom:6px; letter-spacing:1.5px;'>PROMPT</div>"
                f"<div style='background:{bg_surface}; border:1px solid {border}; border-radius:6px; padding:10px 14px; color:{text_hi}; font-size:9.5pt; line-height:1.4; white-space:pre-wrap;'>{html.escape(case.prompt)}</div>"
                f"</div>"
            )

            html_parts.append(
                f"<div style='margin-bottom:14px;'>"
                f"<div style='font-size:7.5pt; font-weight:bold; color:{text_lo}; margin-bottom:6px; letter-spacing:1.5px;'>OUTPUT</div>"
                f"<div style='background:{bg_deep}; border:1px solid {border}; border-radius:6px; padding:10px 14px; color:{green}; font-size:9.5pt; line-height:1.4; white-space:pre-wrap;'>{html.escape(case.output)}</div>"
                f"</div>"
            )

            if case.context_used:
                context_html = ""
                for idx, chunk in enumerate(case.context_used, 1):
                    context_html += f"<div style='border-bottom:1px solid {border}; padding-bottom:6px; margin-bottom:6px; font-size:8.5pt; color:{text_mid};'>[Chunk {idx}]</div>"
                    context_html += f"<div style='margin-bottom:10px; font-size:8.5pt; color:{text_mid}; white-space:pre-wrap;'>{html.escape(chunk)}</div>"
                
                html_parts.append(
                    f"<div style='margin-bottom:14px;'>"
                    f"<div style='font-size:7.5pt; font-weight:bold; color:{text_lo}; margin-bottom:6px; letter-spacing:1.5px;'>CONTEXT USED</div>"
                    f"<div style='background:{bg_surface}; border:1px solid {border}; border-radius:6px; padding:10px 14px;'>{context_html}</div>"
                    f"</div>"
                )

            html_parts.append("</div>")
            self._detail_view.setHtml("".join(html_parts))

    # ── model selection helpers ───────────────────────────────────────────────

    def _is_adapter_compatible(self, model_filename: str, adapter_name: str) -> bool:
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
        if "1.5b" in model_filename.lower() and "1.5b" in adapter_name.lower():
            return True
        if "8b" in model_filename.lower() and "8b" in adapter_name.lower():
            return True
        return False

    def _refresh_model_combo(self):
        self._model_combo.blockSignals(True)
        current_data = self._model_combo.itemData(self._model_combo.currentIndex())
        self._model_combo.clear()
        
        adapters_dir = "data/adapters"
        adapters = []
        if os.path.exists(adapters_dir):
            try:
                for d in sorted(os.listdir(adapters_dir)):
                    d_path = os.path.join(adapters_dir, d)
                    if os.path.isdir(d_path):
                        files_in_dir = os.listdir(d_path)
                        if any(f.endswith(".gguf") or f.endswith(".bin") for f in files_in_dir):
                            adapters.append(d)
            except Exception as e:
                logger.warning(f"Error scanning adapters: {e}")

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
                    
        # Restore selection
        if current_data:
            found = False
            for idx in range(self._model_combo.count()):
                d = self._model_combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == current_data.get("model") and d.get("adapter") == current_data.get("adapter"):
                    self._model_combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found and self._model_combo.count() > 0:
                self._model_combo.setCurrentIndex(0)
        else:
            from app.engine.model_loader import ModelLoader
            active_model = getattr(ModelLoader, "_model_name", None)
            active_adapter = getattr(ModelLoader, "_active_adapter", None)
            found = False
            for idx in range(self._model_combo.count()):
                d = self._model_combo.itemData(idx)
                if isinstance(d, dict) and d.get("model") == active_model and d.get("adapter") == active_adapter:
                    self._model_combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found and self._model_combo.count() > 0:
                self._model_combo.setCurrentIndex(0)
                
        self._model_combo.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_model_combo()

    # ── dataset editor helpers ────────────────────────────────────────────────

    def _load_dataset_for_editing(self, path: str):
        self._loaded_cases = []
        self._edit_cases_list.blockSignals(True)
        self._edit_cases_list.clear()
        self._clear_fields()
        
        if not path or not os.path.exists(path):
            self._edit_cases_list.blockSignals(False)
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        self._loaded_cases.append(json.loads(line))
                    except Exception as e:
                        logger.warning(f"Error decoding case line: {e}")
            
            # Populate the list widget
            for case in self._loaded_cases:
                self._edit_cases_list.addItem(case.get("id", "unknown"))
                
            if self._edit_cases_list.count() > 0:
                self._edit_cases_list.setCurrentRow(0)
        except Exception as e:
            logger.warning(f"Error loading dataset: {e}")
        finally:
            self._edit_cases_list.blockSignals(False)

    def _on_edit_case_selected(self, current, previous):
        if previous:
            row = self._edit_cases_list.row(previous)
            self._save_fields_to_case(row)
            
        if current:
            row = self._edit_cases_list.row(current)
            self._load_case_to_fields(row)
        else:
            self._clear_fields()

    def _save_fields_to_case(self, index: int):
        if index < 0 or index >= len(self._loaded_cases):
            return
        case = self._loaded_cases[index]
        
        case["id"] = self._edit_case_id.text().strip()
        case["prompt"] = self._edit_case_prompt.toPlainText().strip()
        
        context = self._edit_case_context.toPlainText().strip()
        if context:
            case["context"] = context
        elif "context" in case:
            del case["context"]
            
        expected = self._edit_case_expected.text().strip()
        if expected:
            case["expected"] = expected
        elif "expected" in case:
            del case["expected"]
            
        grader = self._edit_case_grader.currentText()
        case["grader"] = grader
        
        if grader == "keyword_hit":
            kws = [k.strip() for k in self._edit_case_keywords.text().split(",") if k.strip()]
            case["keywords"] = kws
            case["require_all"] = self._edit_case_req_all.isChecked()
            if "schema_keys" in case: del case["schema_keys"]
        elif grader == "json_valid":
            keys = [k.strip() for k in self._edit_case_keywords.text().split(",") if k.strip()]
            case["schema_keys"] = keys
            if "keywords" in case: del case["keywords"]
            if "require_all" in case: del case["require_all"]
        else:
            if "keywords" in case: del case["keywords"]
            if "require_all" in case: del case["require_all"]
            if "schema_keys" in case: del case["schema_keys"]
            
        # Update list item text if ID changed
        item = self._edit_cases_list.item(index)
        if item and item.text() != case["id"]:
            self._edit_cases_list.blockSignals(True)
            item.setText(case["id"])
            self._edit_cases_list.blockSignals(False)

    def _load_case_to_fields(self, index: int):
        if index < 0 or index >= len(self._loaded_cases):
            self._clear_fields()
            return
        case = self._loaded_cases[index]
        
        self._block_form_signals(True)
        
        self._edit_case_id.setText(case.get("id", ""))
        self._edit_case_prompt.setPlainText(case.get("prompt", ""))
        self._edit_case_context.setPlainText(case.get("context", ""))
        
        expected = case.get("expected", "")
        if isinstance(expected, (dict, list)):
            expected = json.dumps(expected)
        self._edit_case_expected.setText(str(expected))
        
        grader = case.get("grader", "keyword_hit")
        idx = self._edit_case_grader.findText(grader)
        if idx >= 0:
            self._edit_case_grader.setCurrentIndex(idx)
            
        self._update_grader_fields_visibility(grader)
        
        if grader == "keyword_hit":
            kws = case.get("keywords", [])
            self._edit_case_keywords.setText(", ".join(kws))
            self._edit_case_req_all.setChecked(case.get("require_all", True))
        elif grader == "json_valid":
            keys = case.get("schema_keys", [])
            self._edit_case_keywords.setText(", ".join(keys))
        else:
            self._edit_case_keywords.clear()
            
        self._block_form_signals(False)

    def _add_case(self):
        current_item = self._edit_cases_list.currentItem()
        if current_item:
            self._save_fields_to_case(self._edit_cases_list.row(current_item))
            
        new_id = f"case_{len(self._loaded_cases) + 1:03d}"
        new_case = {
            "id": new_id,
            "prompt": "New prompt...",
            "grader": "exact_match",
            "expected": "Expected answer..."
        }
        self._loaded_cases.append(new_case)
        self._edit_cases_list.addItem(new_id)
        
        new_item = self._edit_cases_list.item(self._edit_cases_list.count() - 1)
        self._edit_cases_list.setCurrentItem(new_item)

    def _delete_case(self):
        current_item = self._edit_cases_list.currentItem()
        if not current_item:
            return
        
        row = self._edit_cases_list.row(current_item)
        reply = QMessageBox.question(
            self, "Delete Case",
            f"Are you sure you want to delete case '{current_item.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._loaded_cases.pop(row)
            self._edit_cases_list.takeItem(row)
            
            if self._edit_cases_list.count() > 0:
                new_row = min(row, self._edit_cases_list.count() - 1)
                self._edit_cases_list.setCurrentRow(new_row)
            else:
                self._clear_fields()

    def _save_dataset(self):
        current_item = self._edit_cases_list.currentItem()
        if current_item:
            self._save_fields_to_case(self._edit_cases_list.row(current_item))
            
        path = self._dataset_path.text().strip()
        if not path:
            QMessageBox.warning(self, "No Dataset", "Please load a dataset first.")
            return
            
        try:
            with open(path, "w", encoding="utf-8") as f:
                for case in self._loaded_cases:
                    f.write(json.dumps(case, ensure_ascii=False) + "\n")
            QMessageBox.information(self, "Success", f"Saved {len(self._loaded_cases)} cases to {os.path.basename(path)}.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save dataset: {e}")

    def _clear_fields(self):
        self._block_form_signals(True)
        self._edit_case_id.clear()
        self._edit_case_prompt.clear()
        self._edit_case_context.clear()
        self._edit_case_expected.clear()
        self._edit_case_keywords.clear()
        self._edit_case_req_all.setChecked(False)
        self._block_form_signals(False)

    def _block_form_signals(self, block: bool):
        self._edit_case_id.blockSignals(block)
        self._edit_case_prompt.blockSignals(block)
        self._edit_case_context.blockSignals(block)
        self._edit_case_expected.blockSignals(block)
        self._edit_case_grader.blockSignals(block)
        self._edit_case_keywords.blockSignals(block)
        self._edit_case_req_all.blockSignals(block)

    def _save_current_form_to_memory(self):
        current_item = self._edit_cases_list.currentItem()
        if current_item:
            row = self._edit_cases_list.row(current_item)
            self._save_fields_to_case(row)

    def _on_grader_changed(self, grader: str):
        self._update_grader_fields_visibility(grader)
        self._save_current_form_to_memory()

    def _update_grader_fields_visibility(self, grader: str):
        if grader == "keyword_hit":
            self._kw_lbl.setText("Keywords:")
            self._edit_case_keywords.setPlaceholderText("comma-separated list...")
            self._kw_row.setVisible(True)
            self._req_row.setVisible(True)
        elif grader == "json_valid":
            self._kw_lbl.setText("Keys:")
            self._edit_case_keywords.setPlaceholderText("comma-separated keys...")
            self._kw_row.setVisible(True)
            self._req_row.setVisible(False)
        else:
            self._kw_row.setVisible(False)
            self._req_row.setVisible(False)

    def _apply_results_filter(self):
        show_pass = self._filter_pass_chk.isChecked()
        show_fail = self._filter_fail_chk.isChecked()
        for idx in range(self._results_tree.topLevelItemCount()):
            item = self._results_tree.topLevelItem(idx)
            is_pass = item.text(2) == "PASS"
            should_show = (is_pass and show_pass) or (not is_pass and show_fail)
            item.setHidden(not should_show)

    def _export_eval_report(self):
        if not getattr(self, "_last_report", None):
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Eval Report", "eval_report.json", "JSON (*.json)"
        )
        if not path:
            return
            
        try:
            report = self._last_report
            cases_json = []
            for case in report.cases:
                cases_json.append({
                    "case_id": case.case_id,
                    "prompt": case.prompt,
                    "output": case.output,
                    "grader": case.grader,
                    "grade": case.grade,
                    "latency_s": case.latency_s,
                    "error": case.error
                })
            report_dict = {
                "dataset_path": self._dataset_path.text(),
                "workflow_name": self._workflow_combo.currentData(),
                "total": report.total,
                "passed": report.passed,
                "failed": report.failed,
                "pass_rate": report.pass_rate,
                "cases": cases_json
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Export Complete", f"Report saved successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report: {e}")
