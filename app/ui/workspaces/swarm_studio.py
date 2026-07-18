from __future__ import annotations

import os
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.engine.swarm_orchestrator import SwarmOrchestratorThread
from app.ui.workspaces.agent_profile_studio import AgentProfileStudioWorkspace
from app.utils.swarm_agent_profiles import load_agent_profiles


class _TpsChart(QWidget):
    """Minimal sparkline canvas for live tokens-per-second telemetry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)
        self._samples: list[float] = []
        self._cumulative_tokens = 0
        self._latest_tps = 0.0

    def add_sample(self, tokens_per_second: float, cumulative_tokens: int) -> None:
        self._samples.append(max(0.0, tokens_per_second))
        self._samples = self._samples[-60:]
        self._latest_tps = tokens_per_second
        self._cumulative_tokens = cumulative_tokens
        self.update()

    def reset(self) -> None:
        self._samples = []
        self._cumulative_tokens = 0
        self._latest_tps = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#0A0A14"))
        painter.setPen(QPen(QColor("#252535")))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        if len(self._samples) >= 2:
            max_v = max(self._samples) or 1.0
            w = rect.width() - 8
            h = rect.height() - 22
            n = len(self._samples)
            step = w / max(1, n - 1)
            painter.setPen(QPen(QColor("#7FDBFF"), 1.5))
            points = [
                QPointF(4 + i * step, 4 + h - (v / max_v) * h)
                for i, v in enumerate(self._samples)
            ]
            for a, b in zip(points, points[1:]):
                painter.drawLine(a, b)

        painter.setPen(QPen(QColor("#C0C0D0")))
        painter.setFont(QFont("Monospace", 8))
        painter.drawText(
            rect.adjusted(4, 0, -4, -4),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            f"{self._latest_tps:.1f} tok/s · {self._cumulative_tokens} tokens total",
        )
        painter.end()


class SwarmStudioWorkspace(QWidget):
    """High-signal dashboard for Karl's multi-agent code swarm."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._thread: SwarmOrchestratorThread | None = None
        self._started_at = 0.0
        self._task_rows: dict[str, int] = {}
        self._file_contents: dict[str, str] = {}
        self._tracebacks: dict[str, str] = {}
        self._history = []
        self._task_nodes: dict[str, QGraphicsRectItem] = {}
        self._graph_scene: QGraphicsScene | None = None
        self._active_filepaths: list[str] = []
        self._agent_profiles: dict[str, dict] = {}

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._build_ui()
        self._refresh_agent_profile_selectors()
        self._load_history()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title_row = QWidget()
        tl = QHBoxLayout(title_row)
        tl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Swarm Studio")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._runtime_lbl = QLabel("idle")
        self._runtime_lbl.setObjectName("lbl-muted")
        tl.addWidget(title)
        tl.addStretch()
        tl.addWidget(self._runtime_lbl)
        root.addWidget(title_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 3)

        live_tab = QWidget()
        live_layout = QVBoxLayout(live_tab)
        live_layout.setContentsMargins(0, 8, 0, 0)
        live_layout.setSpacing(0)
        live_layout.addWidget(splitter, 1)

        self._main_tabs = QTabWidget()
        self._main_tabs.addTab(live_tab, "Live Run")
        self._profile_studio = AgentProfileStudioWorkspace(self.state)
        self._profile_studio.profile_saved.connect(lambda _name: self._refresh_agent_profile_selectors())
        self._main_tabs.addTab(self._profile_studio, "Agent Profiles")
        self._main_tabs.addTab(self._build_replay_panel(), "Replay")
        self._main_tabs.currentChanged.connect(self._on_main_tab_changed)
        root.addWidget(self._main_tabs, 1)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(8)

        header = QLabel("Objective")
        header.setObjectName("section-header")
        layout.addWidget(header)

        self._objective_input = QTextEdit()
        self._objective_input.setPlaceholderText("Describe the codebase change the swarm should plan, edit, and verify.")
        self._objective_input.setMinimumHeight(120)
        layout.addWidget(self._objective_input, 2)

        self._workspace_input = QLineEdit()
        self._workspace_input.setPlaceholderText("/home/ethan/karl")
        self._workspace_input.setText(self.state.swarm_last_workspace or os.getcwd())
        layout.addWidget(QLabel("Workspace Path"))
        layout.addWidget(self._workspace_input)

        self._test_command_input = QLineEdit()
        self._test_command_input.setPlaceholderText("venv/bin/python -m pytest tests/ -q")
        self._test_command_input.setText("venv/bin/python -m pytest tests/ -q")
        layout.addWidget(QLabel("Verification Command"))
        layout.addWidget(self._test_command_input)

        group = QGroupBox("Swarm Runtime")
        gl = QGridLayout(group)
        self._temp_spin = QSpinBox()
        self._temp_spin.setRange(0, 100)
        self._temp_spin.setValue(20)
        self._temp_spin.setSuffix("%")
        self._tokens_spin = QSpinBox()
        self._tokens_spin.setRange(256, 8192)
        self._tokens_spin.setSingleStep(256)
        self._tokens_spin.setValue(2048)
        gl.addWidget(QLabel("Coder Temp"), 0, 0)
        gl.addWidget(self._temp_spin, 0, 1)
        gl.addWidget(QLabel("Max Tokens"), 1, 0)
        gl.addWidget(self._tokens_spin, 1, 1)
        layout.addWidget(group)

        intel_group = QGroupBox("Swarm Intelligence")
        ig = QGridLayout(intel_group)
        self._candidates_spin = QSpinBox()
        self._candidates_spin.setRange(1, 5)
        self._candidates_spin.setValue(1)
        self._candidates_spin.setToolTip(
            "Multiverse execution: generate N independent candidate solutions per\n"
            "task (different temperatures) and let the Judge pick the strongest one."
        )
        ig.addWidget(QLabel("Candidates / Task"), 0, 0)
        ig.addWidget(self._candidates_spin, 0, 1)

        self._memory_check = QPushButton("Cross-Run Memory")
        self._memory_check.setCheckable(True)
        self._memory_check.setChecked(True)
        self._memory_check.setToolTip("Recall past failure patterns on this codebase before coding.")
        self._specialists_check = QPushButton("Specialist Audit")
        self._specialists_check.setCheckable(True)
        self._specialists_check.setChecked(True)
        self._specialists_check.setToolTip("Auto-run security/performance auditors on tasks that touch sensitive code.")
        self._critic_check = QPushButton("Critic Review")
        self._critic_check.setCheckable(True)
        self._critic_check.setChecked(True)
        self._critic_check.setToolTip("Red-team pass for silent failure modes and code smells.")
        self._adaptive_check = QPushButton("Adaptive Concurrency")
        self._adaptive_check.setCheckable(True)
        self._adaptive_check.setChecked(True)
        self._adaptive_check.setToolTip("Size the parallel worker pool from live GPU/CPU/VRAM headroom.")
        for btn in (self._memory_check, self._specialists_check, self._critic_check, self._adaptive_check):
            btn.setObjectName("btn-toggle")
        ig.addWidget(self._memory_check, 1, 0)
        ig.addWidget(self._specialists_check, 1, 1)
        ig.addWidget(self._critic_check, 2, 0)
        ig.addWidget(self._adaptive_check, 2, 1)
        self._architect_profile_combo = QComboBox()
        self._coder_profile_combo = QComboBox()
        self._tester_profile_combo = QComboBox()
        ig.addWidget(QLabel("Architect"), 3, 0)
        ig.addWidget(self._architect_profile_combo, 3, 1)
        ig.addWidget(QLabel("Coder"), 4, 0)
        ig.addWidget(self._coder_profile_combo, 4, 1)
        ig.addWidget(QLabel("Tester"), 5, 0)
        ig.addWidget(self._tester_profile_combo, 5, 1)
        layout.addWidget(intel_group)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        self._launch_btn = QPushButton("Launch Swarm")
        self._launch_btn.setObjectName("btn-primary")
        self._launch_btn.clicked.connect(self._launch)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("btn-danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        rl.addWidget(self._launch_btn)
        rl.addWidget(self._stop_btn)
        layout.addWidget(row)

        layout.addWidget(QLabel("Recent Objectives"))
        self._recent_list = QListWidget()
        self._recent_list.itemClicked.connect(self._load_history_item)
        layout.addWidget(self._recent_list, 1)

        # This panel stacks the objective box, two line-edit fields, two
        # QGroupBoxes of runtime/intelligence controls, the launch row, and
        # a history list -- with no room to spare, all of it got squeezed
        # below readable height at the app's 760x560 minimum size (observed:
        # the objective placeholder text and the verification-command field
        # both visibly clipped). Scrolling beats every widget losing height.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(panel)
        return scroll

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(8, 0, 8, 0)
        outer.setSpacing(8)

        self._summary_frame = QFrame()
        self._summary_frame.setObjectName("panel")
        sl = QGridLayout(self._summary_frame)
        self._layer_lbl = QLabel("Layers: 0")
        self._task_lbl = QLabel("Tasks: 0")
        self._verify_lbl = QLabel("Verification: idle")
        for label in (self._layer_lbl, self._task_lbl, self._verify_lbl):
            label.setObjectName("lbl-muted")
        sl.addWidget(self._layer_lbl, 0, 0)
        sl.addWidget(self._task_lbl, 0, 1)
        sl.addWidget(self._verify_lbl, 0, 2)
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        sl.addWidget(self._progress, 1, 0, 1, 3)
        outer.addWidget(self._summary_frame)

        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setHandleWidth(1)

        graph_container = QWidget()
        gc_layout = QVBoxLayout(graph_container)
        gc_layout.setContentsMargins(0, 0, 0, 0)
        gc_layout.setSpacing(4)

        graph_lbl = QLabel("Task Dependency Graph")
        graph_lbl.setObjectName("section-header")
        gc_layout.addWidget(graph_lbl)

        self._graph_scene = QGraphicsScene(self)
        self._graph_view = QGraphicsView(self._graph_scene)
        self._graph_view.setMinimumHeight(180)
        self._graph_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._graph_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._graph_view.setStyleSheet(
            "background: #0D0D16; border: 1px solid #252535; border-radius: 4px;"
        )
        gc_layout.addWidget(self._graph_view, 1)
        vsplit.addWidget(graph_container)

        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        self._layers_tree = QTreeWidget()
        self._layers_tree.setHeaderLabels(["Dependency Layers"])
        self._layers_tree.setMinimumHeight(80)
        bl.addWidget(self._layers_tree, 1)

        self._task_table = QTableWidget(0, 4)
        self._task_table.setHorizontalHeaderLabels(["File", "Status", "Layer", "Detail"])
        self._task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._task_table.itemSelectionChanged.connect(self._sync_selection_preview)
        self._task_table.horizontalHeader().setStretchLastSection(True)
        bl.addWidget(self._task_table, 2)

        self._status_log = QTextEdit()
        self._status_log.setReadOnly(True)
        self._status_log.setFont(QFont("Monospace", 9))
        self._status_log.setPlaceholderText("Swarm status stream.")
        bl.addWidget(self._status_log, 2)

        vsplit.addWidget(bottom)
        vsplit.setStretchFactor(0, 2)
        vsplit.setStretchFactor(1, 3)
        outer.addWidget(vsplit, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(8)

        stream_header = QLabel("Live Code Stream")
        stream_header.setObjectName("section-header")
        layout.addWidget(stream_header)

        self._stream_view = QPlainTextEdit()
        self._stream_view.setReadOnly(True)
        self._stream_view.setFont(QFont("Monospace", 8))
        self._stream_view.setPlaceholderText("Tokens appear here as each coder agent writes...")
        self._stream_view.setMaximumHeight(180)
        self._stream_view.setStyleSheet(
            "background: #080810; color: #A0D8B0; border: 1px solid #202040; border-radius: 4px; padding: 4px;"
        )
        layout.addWidget(self._stream_view)

        chart_header = QLabel("Live Telemetry")
        chart_header.setObjectName("section-header")
        layout.addWidget(chart_header)
        self._tps_chart = _TpsChart()
        layout.addWidget(self._tps_chart)

        # ── Interactive debugger: pause/step/resume mid-run ──────────────────
        debugger_group = QGroupBox("Interactive Debugger")
        dg = QVBoxLayout(debugger_group)
        dg.setSpacing(6)

        self._pause_on_step_check = QPushButton("Pause on Step")
        self._pause_on_step_check.setCheckable(True)
        self._pause_on_step_check.setObjectName("btn-toggle")
        self._pause_on_step_check.setToolTip(
            "Pause before each coder task starts so you can inspect or override it before it runs."
        )
        dg.addWidget(self._pause_on_step_check)

        debug_btn_row = QWidget()
        dbr = QHBoxLayout(debug_btn_row)
        dbr.setContentsMargins(0, 0, 0, 0)
        dbr.setSpacing(4)
        self._debug_pause_btn = QPushButton("Pause")
        self._debug_pause_btn.setToolTip("Engage step-pausing now; takes effect at the next task boundary.")
        self._debug_pause_btn.clicked.connect(self._on_debug_pause)
        self._debug_step_btn = QPushButton("Step")
        self._debug_step_btn.setEnabled(False)
        self._debug_step_btn.clicked.connect(self._on_debug_step)
        self._debug_resume_btn = QPushButton("Resume")
        self._debug_resume_btn.setEnabled(False)
        self._debug_resume_btn.clicked.connect(self._on_debug_resume)
        dbr.addWidget(self._debug_pause_btn)
        dbr.addWidget(self._debug_step_btn)
        dbr.addWidget(self._debug_resume_btn)
        dg.addWidget(debug_btn_row)

        self._debug_active_step_lbl = QLabel("No task currently paused.")
        self._debug_active_step_lbl.setObjectName("lbl-muted")
        self._debug_active_step_lbl.setWordWrap(True)
        dg.addWidget(self._debug_active_step_lbl)

        layout.addWidget(debugger_group)

        # ── Live steering: inject a human correction into an in-flight task ──
        # Doubles as the "editable text box" for the interactive debugger —
        # when paused, target the shown filepath and send an instruction.
        # Target path, message, and button used to share one row -- three
        # widgets fighting for a panel that's only ~1/3 of the app's 760px
        # minimum width left the message field showing a couple of
        # characters of its own placeholder. Message gets its own full-width
        # row since it's the one that actually needs the room.
        steer_target_row = QWidget()
        str_l = QHBoxLayout(steer_target_row)
        str_l.setContentsMargins(0, 0, 0, 0)
        str_l.setSpacing(4)
        self._steering_target = QLineEdit()
        self._steering_target.setPlaceholderText("target filepath (e.g. app/foo.py)")
        self._steering_btn = QPushButton("Steer")
        self._steering_btn.clicked.connect(self._on_send_guidance)
        str_l.addWidget(self._steering_target, 1)
        str_l.addWidget(self._steering_btn)
        layout.addWidget(steer_target_row)

        self._steering_input = QLineEdit()
        self._steering_input.setPlaceholderText("Live steering: correct the agent mid-task, no restart needed...")
        self._steering_input.returnPressed.connect(self._on_send_guidance)
        layout.addWidget(self._steering_input)

        cog_header = QLabel("Swarm Intelligence")
        cog_header.setObjectName("section-header")
        layout.addWidget(cog_header)
        self._cognition_log = QPlainTextEdit()
        self._cognition_log.setReadOnly(True)
        self._cognition_log.setFont(QFont("Monospace", 8))
        self._cognition_log.setPlaceholderText(
            "Multiverse candidates, memory recalls, specialist reviews, and concurrency\n"
            "decisions stream here in real time."
        )
        self._cognition_log.setMaximumHeight(140)
        self._cognition_log.setStyleSheet(
            "background: #0A0812; color: #C9A8FF; border: 1px solid #26203A; border-radius: 4px; padding: 4px;"
        )
        layout.addWidget(self._cognition_log)

        # ── Cherry-pick panel (hidden until the orchestrator proposes edits) ──
        self._cherry_pick_group = QGroupBox("Proposed Edits — Cherry Pick")
        cg = QVBoxLayout(self._cherry_pick_group)
        cg.setSpacing(6)

        self._cherry_pick_list = QListWidget()
        self._cherry_pick_list.setMinimumHeight(100)
        self._cherry_pick_list.itemClicked.connect(self._on_cherry_pick_item_clicked)
        cg.addWidget(self._cherry_pick_list)

        btn_row = QWidget()
        br = QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)
        br.setSpacing(4)
        _all_btn = QPushButton("All")
        _all_btn.setFixedWidth(42)
        _all_btn.clicked.connect(self._cherry_select_all)
        _none_btn = QPushButton("None")
        _none_btn.setFixedWidth(42)
        _none_btn.clicked.connect(self._cherry_select_none)
        self._commit_btn = QPushButton("Commit Checked Edits")
        self._commit_btn.setObjectName("btn-primary")
        self._commit_btn.setEnabled(False)
        self._commit_btn.clicked.connect(self._on_commit_edits)
        br.addWidget(_all_btn)
        br.addWidget(_none_btn)
        br.addStretch()
        br.addWidget(self._commit_btn)
        cg.addWidget(btn_row)

        self._cherry_pick_group.setVisible(False)
        layout.addWidget(self._cherry_pick_group)

        layout.addWidget(QLabel("File Preview"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Monospace", 9))
        layout.addWidget(self._preview, 2)

        layout.addWidget(QLabel("Verification Traceback"))
        self._traceback_browser = QTextBrowser()
        self._traceback_browser.setFont(QFont("Monospace", 9))
        self._traceback_browser.setOpenLinks(False)
        layout.addWidget(self._traceback_browser, 2)

        self._result_banner = QLabel("No run active.")
        self._result_banner.setWordWrap(True)
        self._result_banner.setObjectName("lbl-muted")
        layout.addWidget(self._result_banner)
        return panel

    def _build_replay_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._replay_manager = None
        self._replay_steps: list[dict] = []

        header_row = QWidget()
        hl = QHBoxLayout(header_row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        hl.addWidget(QLabel("Past Run:"))
        self._replay_run_combo = QComboBox()
        self._replay_run_combo.setMinimumWidth(280)
        self._replay_run_combo.currentIndexChanged.connect(self._on_replay_run_selected)
        hl.addWidget(self._replay_run_combo, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_replay_runs)
        hl.addWidget(refresh_btn)
        layout.addWidget(header_row)

        self._replay_objective_lbl = QLabel("Select a past run to inspect its step-by-step timeline.")
        self._replay_objective_lbl.setObjectName("lbl-muted")
        self._replay_objective_lbl.setWordWrap(True)
        layout.addWidget(self._replay_objective_lbl)

        replay_split = QSplitter(Qt.Orientation.Horizontal)
        replay_split.setHandleWidth(1)

        self._replay_steps_list = QListWidget()
        self._replay_steps_list.itemClicked.connect(self._on_replay_step_selected)
        replay_split.addWidget(self._replay_steps_list)

        detail_widget = QWidget()
        dw_layout = QVBoxLayout(detail_widget)
        dw_layout.setContentsMargins(0, 0, 0, 0)
        dw_layout.setSpacing(6)
        dw_layout.addWidget(QLabel("Diff"))
        self._replay_diff_view = QPlainTextEdit()
        self._replay_diff_view.setReadOnly(True)
        self._replay_diff_view.setFont(QFont("Monospace", 8))
        dw_layout.addWidget(self._replay_diff_view, 1)
        dw_layout.addWidget(QLabel("Test Output"))
        self._replay_test_view = QPlainTextEdit()
        self._replay_test_view.setReadOnly(True)
        self._replay_test_view.setFont(QFont("Monospace", 8))
        dw_layout.addWidget(self._replay_test_view, 1)
        replay_split.addWidget(detail_widget)
        replay_split.setStretchFactor(0, 1)
        replay_split.setStretchFactor(1, 2)

        layout.addWidget(replay_split, 1)
        return panel

    def _on_main_tab_changed(self, index: int) -> None:
        if self._main_tabs.tabText(index) == "Replay" and self._replay_run_combo.count() == 0:
            self._refresh_replay_runs()

    def _refresh_replay_runs(self) -> None:
        from app.utils.swarm_replay import SwarmReplayManager
        if self._replay_manager is None:
            self._replay_manager = SwarmReplayManager()

        runs = self._replay_manager.list_past_runs()
        self._replay_run_combo.blockSignals(True)
        self._replay_run_combo.clear()
        for run in runs:
            status = "ok" if run.get("success") else "failed"
            objective = (run.get("objective") or run["run_id"])[:50]
            label = f"{run.get('timestamp', '')[:19]} — {objective} ({status})"
            self._replay_run_combo.addItem(label, run["run_id"])
        self._replay_run_combo.blockSignals(False)

        if runs:
            self._on_replay_run_selected(0)
        else:
            self._replay_objective_lbl.setText("No past swarm runs found yet.")
            self._replay_steps_list.clear()
            self._replay_diff_view.clear()
            self._replay_test_view.clear()

    def _on_replay_run_selected(self, index: int) -> None:
        if index < 0 or self._replay_manager is None:
            return
        run_id = self._replay_run_combo.itemData(index)
        if not run_id:
            return
        details = self._replay_manager.get_run_details(run_id)
        self._replay_objective_lbl.setText(details.get("objective") or "(no objective recorded)")
        self._replay_steps = details.get("steps", [])
        self._replay_steps_list.clear()
        for step in self._replay_steps:
            label = f"[{step['step_index']}] {step['type']}"
            if step.get("filepath"):
                label += f" — {step['filepath']}"
            if step.get("is_drift"):
                label += "  ⚠ drift"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, step)
            self._replay_steps_list.addItem(item)
        self._replay_diff_view.clear()
        self._replay_test_view.clear()

    def _on_replay_step_selected(self, item: QListWidgetItem) -> None:
        step = item.data(Qt.ItemDataRole.UserRole) or {}
        self._replay_diff_view.setPlainText(step.get("diff") or "(no diff for this step)")
        self._replay_test_view.setPlainText(step.get("test_output") or "(no test output for this step)")

    def _load_history(self):
        self._history = self.state.memory.load_swarm_history()
        self._recent_list.clear()
        for item in self._history:
            objective = item.get("objective", "")
            row = QListWidgetItem(objective if len(objective) < 70 else objective[:67] + "...")
            row.setToolTip(objective)
            row.setData(Qt.ItemDataRole.UserRole, item)
            self._recent_list.addItem(row)

    def _save_history_item(self, objective: str, workspace_path: str, test_command: str):
        item = {
            "objective": objective,
            "workspace_path": workspace_path,
            "test_command": test_command,
            "temperature": self._temp_spin.value(),
            "max_tokens": self._tokens_spin.value(),
        }
        self._history = [old for old in self._history if old.get("objective") != objective]
        self._history.insert(0, item)
        self._history = self._history[:10]
        self.state.memory.save_swarm_history(self._history)
        self._load_history()

    def _load_history_item(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        self._objective_input.setPlainText(data.get("objective", ""))
        self._workspace_input.setText(data.get("workspace_path", ""))
        self._test_command_input.setText(data.get("test_command", "venv/bin/python -m pytest tests/ -q"))
        if "temperature" in data:
            self._temp_spin.setValue(int(data["temperature"]))
        if "max_tokens" in data:
            self._tokens_spin.setValue(int(data["max_tokens"]))

    def _refresh_agent_profile_selectors(self):
        self._agent_profiles = load_agent_profiles()
        combos = {
            "architect": getattr(self, "_architect_profile_combo", None),
            "coder": getattr(self, "_coder_profile_combo", None),
            "tester": getattr(self, "_tester_profile_combo", None),
        }
        for default_id, combo in combos.items():
            if combo is None:
                continue
            previous = combo.currentData() or default_id
            combo.blockSignals(True)
            combo.clear()
            for profile_id, profile in sorted(self._agent_profiles.items()):
                combo.addItem(f"{profile.get('icon', '')} {profile.get('name', profile_id)}".strip(), profile_id)
            index = combo.findData(previous)
            if index < 0:
                index = combo.findData(default_id)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _launch(self):
        objective = self._objective_input.toPlainText().strip()
        workspace_path = self._workspace_input.text().strip()
        test_command = self._test_command_input.text().strip()
        if not objective or not workspace_path:
            QMessageBox.warning(self, "Swarm Studio", "Objective and workspace path are required.")
            return

        self._reset_run_ui()
        self._save_history_item(objective, workspace_path, test_command)
        self.state.swarm_running = True
        self.state.swarm_last_objective = objective
        self.state.swarm_last_workspace = workspace_path

        hyperparams = {
            "temperature": self._temp_spin.value() / 100.0,
            "max_tokens": self._tokens_spin.value(),
            "candidates_per_task": self._candidates_spin.value(),
            "enable_memory": self._memory_check.isChecked(),
            "enable_specialists": self._specialists_check.isChecked(),
            "enable_critic": self._critic_check.isChecked(),
            "adaptive_concurrency": self._adaptive_check.isChecked(),
            "pause_on_step": self._pause_on_step_check.isChecked(),
            "agent_profiles": {
                "architect": self._architect_profile_combo.currentData() or "architect",
                "coder": self._coder_profile_combo.currentData() or "coder",
                "tester": self._tester_profile_combo.currentData() or "tester",
            },
        }
        self._thread = SwarmOrchestratorThread(workspace_path, objective, test_command, hyperparams)
        self._thread.status_update.connect(self._on_status)
        self._thread.task_plan_created.connect(self._on_plan)
        self._thread.dependency_layers_built.connect(self._on_layers)
        self._thread.layer_started.connect(self._on_layer_started)
        self._thread.layer_finished.connect(self._on_layer_finished)
        self._thread.task_status_changed.connect(self._on_task_status)
        self._thread.verification_started.connect(self._on_verification_started)
        self._thread.proposal_verification_finished.connect(self._on_proposal_verification_finished)
        self._thread.traceback_captured.connect(self._on_traceback)
        self._thread.verification_failed.connect(self._on_verification_failed)
        self._thread.edits_proposed.connect(self._on_edits_proposed)
        self._thread.file_edited.connect(self._on_file_edited)
        self._thread.test_result.connect(self._on_test_result)
        self._thread.finished_swarm.connect(self._on_finished)
        self._thread.coder_token.connect(self._on_coder_token)
        self._thread.candidates_generated.connect(self._on_candidates_generated)
        self._thread.candidate_scored.connect(self._on_candidate_scored)
        self._thread.winner_selected.connect(self._on_winner_selected)
        self._thread.memory_recalled.connect(self._on_memory_recalled)
        self._thread.specialist_review.connect(self._on_specialist_review)
        self._thread.concurrency_adjusted.connect(self._on_concurrency_adjusted)
        self._thread.guidance_injected.connect(self._on_guidance_injected)
        self._thread.swarm_paused.connect(self._on_swarm_paused)
        self._thread.telemetry_update.connect(self._on_telemetry_update)
        self._thread.finished.connect(self._thread.deleteLater)

        self._launch_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._started_at = time.time()
        self._timer.start(250)
        self._thread.start()

    def _reset_run_ui(self):
        self._task_rows.clear()
        self._file_contents.clear()
        self._tracebacks.clear()
        self._layers_tree.clear()
        if self._graph_scene is not None:
            self._graph_scene.clear()
        self._task_nodes.clear()
        self._task_table.setRowCount(0)
        self._status_log.clear()
        self._preview.clear()
        self._traceback_browser.clear()
        self._cherry_pick_list.clear()
        self._cherry_pick_group.setVisible(False)
        self._commit_btn.setEnabled(False)
        self._stream_view.clear()
        self._stream_current_file = None
        self._cognition_log.clear()
        self._active_filepaths = []
        self._progress.setValue(0)
        self._layer_lbl.setText("Layers: 0")
        self._task_lbl.setText("Tasks: 0")
        self._verify_lbl.setText("Verification: idle")
        self._result_banner.setText("Run active.")
        self._result_banner.setStyleSheet("")
        self._tps_chart.reset()
        self._debug_step_btn.setEnabled(False)
        self._debug_resume_btn.setEnabled(False)
        self._debug_active_step_lbl.setText("No task currently paused.")

    def _stop(self):
        if self._thread and self._thread.isRunning():
            self._thread.request_stop()
            self._status_log.append("[Swarm] Stop requested.")

    def _tick(self):
        if self._started_at:
            elapsed = time.time() - self._started_at
            self._runtime_lbl.setText(f"running {elapsed:.1f}s")

    def _on_status(self, message: str):
        self._status_log.append(message)

    def _on_plan(self, plan: dict):
        tasks = plan.get("tasks", [])
        self._task_lbl.setText(f"Tasks: {len(tasks)}")
        for task in tasks:
            self._ensure_task_row(task.get("filepath", ""), "planned", "", task.get("instructions", ""))

    def _on_layers(self, layers: list):
        self._layers_tree.clear()
        total_tasks = sum(len(layer) for layer in layers)
        self._layer_lbl.setText(f"Layers: {len(layers)}")
        self._task_lbl.setText(f"Tasks: {total_tasks}")
        for idx, layer in enumerate(layers, start=1):
            parent = QTreeWidgetItem(self._layers_tree)
            parent.setText(0, f"Layer {idx}: {len(layer)} task(s)")
            parent.setData(0, Qt.ItemDataRole.UserRole, idx)
            for task in layer:
                child = QTreeWidgetItem(parent)
                child.setText(0, task.get("filepath", "unknown"))
                child.setToolTip(0, task.get("instructions", ""))
            parent.setExpanded(True)
        self._render_dependency_graph(layers)

    def _on_layer_started(self, index: int, total: int, tasks: list):
        self._verify_lbl.setText(f"Layer {index}/{total}: coding")
        for task in tasks:
            self._on_task_status(task.get("filepath", ""), "in_progress", f"Layer {index} started")

    def _on_layer_finished(self, index: int, success: bool, summary: str):
        self._verify_lbl.setText(f"Layer {index}: {'verified' if success else 'failed'}")
        self._status_log.append(f"[Layer] {summary}")

    def _on_task_status(self, filepath: str, status: str, detail: str):
        self._ensure_task_row(filepath, status, self._layer_for_file(filepath), detail)
        completed = 0
        total = max(1, len(self._task_rows))
        for row in self._task_rows.values():
            item = self._task_table.item(row, 1)
            if item and item.text() in {"completed", "failed"}:
                completed += 1
        self._progress.setValue(int((completed / total) * 100))
        self._update_graph_node_status(filepath, status)
        if status == "in_progress":
            if filepath not in self._active_filepaths:
                self._active_filepaths.append(filepath)
            if not self._steering_target.text().strip():
                self._steering_target.setText(filepath)
        elif filepath in self._active_filepaths and status in {"completed", "failed", "skipped"}:
            self._active_filepaths.remove(filepath)
            if self._steering_target.text().strip() == filepath:
                self._steering_target.setText(self._active_filepaths[0] if self._active_filepaths else "")

    # ── Swarm 2.0 telemetry ──────────────────────────────────────────────────

    def _log_intel(self, line: str):
        self._cognition_log.appendPlainText(line)

    def _on_candidates_generated(self, filepath: str, count: int):
        self._log_intel(f"[Multiverse] {filepath}: generating {count} candidate solutions...")

    def _on_candidate_scored(self, filepath: str, index: int, score: dict):
        ok = "✓" if score.get("syntax_ok") else "✗"
        self._log_intel(
            f"  candidate {index} [{ok}] score={score.get('total_score')} "
            f"lint={score.get('lint_violations')} diff={score.get('diff_size')} "
            f"align={score.get('signature_alignment')}"
        )

    def _on_winner_selected(self, filepath: str, index: int, reason: str):
        self._log_intel(f"[Multiverse] {filepath}: winner is candidate {index} ({reason})")

    def _on_memory_recalled(self, filepath: str, text: str):
        self._log_intel(f"[Memory] {filepath}: recalled past pattern(s):\n{text}")

    def _on_specialist_review(self, filepath: str, specialist: str, result: dict):
        verdict = result.get("verdict", "?")
        concerns = result.get("concerns", [])
        if concerns:
            self._log_intel(
                f"[{specialist.title()}] {filepath}: verdict={verdict} risk={result.get('risk_score')} — "
                + "; ".join(concerns)
            )
        else:
            self._log_intel(f"[{specialist.title()}] {filepath}: clean (verdict={verdict})")

    def _on_concurrency_adjusted(self, workers: int, reason: str):
        self._log_intel(f"[Concurrency] {workers} parallel workers — {reason}")

    def _on_guidance_injected(self, filepath: str, message: str):
        self._log_intel(f"[Steering] → {filepath}: \"{message}\"")

    def _on_send_guidance(self):
        if not self._thread or not self._thread.isRunning():
            return
        target = self._steering_target.text().strip()
        message = self._steering_input.text().strip()
        if not target or not message:
            return
        self._thread.inject_guidance(target, message)
        self._steering_input.clear()

    # ── Interactive debugger ─────────────────────────────────────────────────

    def _on_debug_pause(self):
        if self._thread and self._thread.isRunning():
            self._thread.pause()
            self._status_log.append("[Debugger] Pause requested — takes effect at the next task boundary.")

    def _on_debug_resume(self):
        if self._thread and self._thread.isRunning():
            self._thread.resume()
        self._debug_step_btn.setEnabled(False)
        self._debug_resume_btn.setEnabled(False)
        self._debug_active_step_lbl.setText("No task currently paused.")
        self._status_log.append("[Debugger] Resumed.")

    def _on_debug_step(self):
        if self._thread and self._thread.isRunning():
            self._thread.step()
        self._debug_step_btn.setEnabled(False)
        self._debug_resume_btn.setEnabled(False)
        self._status_log.append("[Debugger] Stepping one task forward.")

    def _on_swarm_paused(self, task_info: dict):
        filepath = task_info.get("filepath", "")
        instructions = task_info.get("instructions", "")
        self._debug_active_step_lbl.setText(f"Paused before: {filepath}\n{instructions}")
        self._debug_step_btn.setEnabled(True)
        self._debug_resume_btn.setEnabled(True)
        if not self._steering_target.text().strip():
            self._steering_target.setText(filepath)
        self._status_log.append(f"[Debugger] Paused before {filepath}.")

    def _on_telemetry_update(self, payload: dict):
        self._tps_chart.add_sample(
            payload.get("tokens_per_second", 0.0), payload.get("cumulative_tokens", 0)
        )

    def _on_verification_started(self, layer_index: int, command: str):
        self._verify_lbl.setText(f"Layer {layer_index}: verifying")
        self._status_log.append(f"[Tester] Layer {layer_index}: {command}")

    def _on_proposal_verification_finished(self, layer_index: int, passed: bool, trace: str):
        status = "passed" if passed else "failed"
        self._verify_lbl.setText(f"Layer {layer_index}: dry-run {status}")
        self._status_log.append(f"[Tester] Layer {layer_index} dry-run {status} before approval.")
        if trace:
            key = f"Layer {layer_index} dry-run"
            self._tracebacks[key] = trace
            if not passed:
                self._traceback_browser.setHtml(self._format_traceback_html(trace, key))

    def _on_traceback(self, key: str, trace: str):
        self._tracebacks[key] = trace
        self._traceback_browser.setHtml(self._format_traceback_html(trace, key))

    def _on_file_edited(self, filepath: str, content: str):
        self._file_contents[filepath] = content
        self._ensure_task_row(filepath, "written", self._layer_for_file(filepath), "File content written")
        self._preview.setPlainText(content)

    def _on_test_result(self, passed: bool, trace: str):
        if passed:
            self._traceback_browser.setHtml(
                '<div style="font-family:Monospace,monospace;padding:8px;color:#4CAF50;">Verification passed.</div>'
            )
        else:
            self._traceback_browser.setHtml(self._format_traceback_html(trace))

    def _on_finished(self, success: bool, summary: str):
        self.state.swarm_running = False
        self._timer.stop()
        self._runtime_lbl.setText("idle")
        self._launch_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setValue(100 if success else self._progress.value())
        self._result_banner.setText(summary)
        if success:
            self._result_banner.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self._result_banner.setStyleSheet("color: #FF5C7A; font-weight: bold;")
        self._thread = None

    def _on_coder_token(self, filepath: str, token: str):
        # Set header on first token for this file
        current_header = getattr(self, '_stream_current_file', None)
        if current_header != filepath:
            self._stream_current_file = filepath
            self._stream_view.appendPlainText(f"\n── {filepath} ──")
        self._stream_view.moveCursor(QTextCursor.MoveOperation.End)
        self._stream_view.insertPlainText(token)

    def _ensure_task_row(self, filepath: str, status: str, layer: str, detail: str):
        if not filepath:
            return
        if filepath not in self._task_rows:
            row = self._task_table.rowCount()
            self._task_table.insertRow(row)
            self._task_rows[filepath] = row
            self._task_table.setItem(row, 0, QTableWidgetItem(filepath))
            self._task_table.setItem(row, 1, QTableWidgetItem(status))
            self._task_table.setItem(row, 2, QTableWidgetItem(layer))
            self._task_table.setItem(row, 3, QTableWidgetItem(detail))
        else:
            row = self._task_rows[filepath]
            self._task_table.item(row, 1).setText(status)
            self._task_table.item(row, 2).setText(layer)
            self._task_table.item(row, 3).setText(detail)
        self._task_table.resizeColumnsToContents()

    def _render_dependency_graph(self, layers: list[list[dict]]) -> None:
        """Build a node-link graph from dependency layers into _graph_scene."""
        if self._graph_scene is None:
            return
        self._graph_scene.clear()
        self._task_nodes.clear()

        node_w, node_h = 160, 36
        h_gap, v_gap = 60, 14
        layer_step = node_w + h_gap

        status_colors = {
            "planned": QColor("#1E1E3C"),
            "in_progress": QColor("#7A4800"),
            "written": QColor("#005A4A"),
            "completed": QColor("#174430"),
            "failed": QColor("#5A0020"),
        }
        border_colors = {
            "planned": QColor("#35356E"),
            "in_progress": QColor("#FFB400"),
            "written": QColor("#00C2A0"),
            "completed": QColor("#2DD4A0"),
            "failed": QColor("#FF3366"),
        }
        text_color = QColor("#C8C8E0")
        layer_centers: list[list[tuple[str, float, float]]] = []

        for layer_idx, layer_tasks in enumerate(layers):
            x = layer_idx * layer_step
            centers = []
            total_h = len(layer_tasks) * (node_h + v_gap) - v_gap
            y_start = -total_h / 2

            for task_idx, task in enumerate(layer_tasks):
                filepath = task.get("filepath", "")
                if not filepath:
                    continue
                label = filepath.split("/")[-1] if "/" in filepath else filepath
                y = y_start + task_idx * (node_h + v_gap)

                rect = QGraphicsRectItem(QRectF(x, y, node_w, node_h))
                rect.setBrush(QBrush(status_colors["planned"]))
                rect.setPen(QPen(border_colors["planned"], 1.5))
                rect.setToolTip(filepath)
                self._graph_scene.addItem(rect)
                self._task_nodes[filepath] = rect

                text = self._graph_scene.addText(
                    label if len(label) <= 20 else label[:18] + "...",
                    QFont("Monospace", 7),
                )
                text.setDefaultTextColor(text_color)
                text_rect = text.boundingRect()
                text.setPos(
                    x + (node_w - text_rect.width()) / 2,
                    y + (node_h - text_rect.height()) / 2,
                )
                text.setZValue(1)

                centers.append((filepath, x + node_w / 2, y + node_h / 2))

            layer_centers.append(centers)

        edge_pen = QPen(QColor("#2A2A50"), 1, Qt.PenStyle.DashLine)
        for i in range(1, len(layer_centers)):
            src_x_right = (i - 1) * layer_step + node_w
            dst_x_left = i * layer_step
            for _a, _cx_a, cy_a in layer_centers[i - 1]:
                for _b, _cx_b, cy_b in layer_centers[i]:
                    line = QGraphicsLineItem(src_x_right, cy_a, dst_x_left, cy_b)
                    line.setPen(edge_pen)
                    line.setZValue(-1)
                    self._graph_scene.addItem(line)

        if self._graph_scene.items():
            self._graph_view.fitInView(
                self._graph_scene.itemsBoundingRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def _update_graph_node_status(self, filepath: str, status: str) -> None:
        node = self._task_nodes.get(filepath)
        if node is None:
            return
        status_fill = {
            "planned": QColor("#1E1E3C"),
            "in_progress": QColor("#7A4800"),
            "written": QColor("#005A4A"),
            "completed": QColor("#174430"),
            "failed": QColor("#5A0020"),
        }
        status_border = {
            "planned": QColor("#35356E"),
            "in_progress": QColor("#FFB400"),
            "written": QColor("#00C2A0"),
            "completed": QColor("#2DD4A0"),
            "failed": QColor("#FF3366"),
        }
        node.setBrush(QBrush(status_fill.get(status, status_fill["planned"])))
        node.setPen(QPen(status_border.get(status, status_border["planned"]), 1.5))

    def _layer_for_file(self, filepath: str) -> str:
        for idx in range(self._layers_tree.topLevelItemCount()):
            parent = self._layers_tree.topLevelItem(idx)
            layer_num = parent.data(0, Qt.ItemDataRole.UserRole)
            for child_idx in range(parent.childCount()):
                if parent.child(child_idx).text(0) == filepath:
                    return str(layer_num)
        return ""

    def _sync_selection_preview(self):
        rows = self._task_table.selectionModel().selectedRows() if self._task_table.selectionModel() else []
        if not rows:
            return
        row = rows[0].row()
        filepath_item = self._task_table.item(row, 0)
        if not filepath_item:
            return
        filepath = filepath_item.text()
        self._preview.setPlainText(self._file_contents.get(filepath, "No file content captured yet."))
        trace = (
            self._tracebacks.get(filepath)
            or self._tracebacks.get(f"Layer {self._layer_for_file(filepath)}", "")
        )
        if trace:
            self._traceback_browser.setHtml(self._format_traceback_html(trace, filepath))
        else:
            self._traceback_browser.clear()

    # ── Cherry-pick helpers ──────────────────────────────────────────────────

    def _on_edits_proposed(self, edits: list):
        self._cherry_pick_list.clear()
        for edit in edits:
            item = QListWidgetItem(edit["filepath"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, edit["content"])
            self._cherry_pick_list.addItem(item)
        self._commit_btn.setEnabled(True)
        self._cherry_pick_group.setVisible(True)
        self._status_log.append("[Swarm] Edits proposed — review and commit to proceed.")

    def _on_cherry_pick_item_clicked(self, item: QListWidgetItem):
        content = item.data(Qt.ItemDataRole.UserRole)
        if content:
            self._preview.setPlainText(content)

    def _cherry_select_all(self):
        for i in range(self._cherry_pick_list.count()):
            self._cherry_pick_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _cherry_select_none(self):
        for i in range(self._cherry_pick_list.count()):
            self._cherry_pick_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _on_commit_edits(self):
        if not self._thread:
            return
        selected = [
            self._cherry_pick_list.item(i).text()
            for i in range(self._cherry_pick_list.count())
            if self._cherry_pick_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        skipped = self._cherry_pick_list.count() - len(selected)
        self._thread.commit_selected_edits(selected)
        self._commit_btn.setEnabled(False)
        self._cherry_pick_group.setVisible(False)
        msg = f"[Swarm] Committed {len(selected)} edit(s)"
        if skipped:
            msg += f", skipped {skipped}"
        self._status_log.append(msg + ".")

    # ── Verification traceback viewer ────────────────────────────────────────

    def _on_verification_failed(self, context: str, traceback_text: str):
        self._traceback_browser.setHtml(self._format_traceback_html(traceback_text, context))

    def _format_traceback_html(self, trace: str, context: str = "") -> str:
        import html as _html
        _exc_starts = (
            "Traceback", "Error", "Exception", "SyntaxError", "TypeError",
            "ValueError", "KeyError", "IndexError", "AttributeError",
            "NameError", "ImportError", "AssertionError", "JSONDecodeError",
            "# SYNTAX",
        )
        parts = [
            '<div style="font-family:Monospace,monospace;font-size:9pt;'
            'background:#0A0A14;padding:8px;color:#C0C0D0;">'
        ]
        if context:
            parts.append(f'<b style="color:#FFB400;">[{_html.escape(context)}]</b><br/>')
        for line in trace.splitlines():
            stripped = line.strip()
            escaped = _html.escape(line)
            if stripped.startswith("File ") and ("line " in stripped or '", line' in stripped):
                parts.append(f'<span style="color:#7FDBFF;">{escaped}</span><br/>')
            elif any(stripped.startswith(p) for p in _exc_starts):
                parts.append(f'<b style="color:#FF5C7A;">{escaped}</b><br/>')
            elif stripped.startswith("^") or "~~~" in stripped:
                parts.append(f'<span style="color:#FF9900;">{escaped}</span><br/>')
            else:
                parts.append(f'{escaped}<br/>')
        parts.append("</div>")
        return "".join(parts)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.request_stop()
            self._thread.wait()
        super().closeEvent(event)
