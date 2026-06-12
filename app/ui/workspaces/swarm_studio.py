from __future__ import annotations

import os
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.engine.swarm_orchestrator import SwarmOrchestratorThread


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

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._build_ui()
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
        root.addWidget(splitter, 1)

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
        return panel

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

        layout.addWidget(QLabel("File Preview"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Monospace", 9))
        layout.addWidget(self._preview, 2)

        layout.addWidget(QLabel("Traceback / Verification Detail"))
        self._traceback = QTextEdit()
        self._traceback.setReadOnly(True)
        self._traceback.setFont(QFont("Monospace", 8))
        layout.addWidget(self._traceback, 2)

        self._result_banner = QLabel("No run active.")
        self._result_banner.setWordWrap(True)
        self._result_banner.setObjectName("lbl-muted")
        layout.addWidget(self._result_banner)
        return panel

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
        }
        self._thread = SwarmOrchestratorThread(workspace_path, objective, test_command, hyperparams)
        self._thread.status_update.connect(self._on_status)
        self._thread.task_plan_created.connect(self._on_plan)
        self._thread.dependency_layers_built.connect(self._on_layers)
        self._thread.layer_started.connect(self._on_layer_started)
        self._thread.layer_finished.connect(self._on_layer_finished)
        self._thread.task_status_changed.connect(self._on_task_status)
        self._thread.verification_started.connect(self._on_verification_started)
        self._thread.traceback_captured.connect(self._on_traceback)
        self._thread.file_edited.connect(self._on_file_edited)
        self._thread.test_result.connect(self._on_test_result)
        self._thread.finished_swarm.connect(self._on_finished)
        self._thread.coder_token.connect(self._on_coder_token)
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
        self._traceback.clear()
        self._stream_view.clear()
        self._stream_current_file = None
        self._progress.setValue(0)
        self._layer_lbl.setText("Layers: 0")
        self._task_lbl.setText("Tasks: 0")
        self._verify_lbl.setText("Verification: idle")
        self._result_banner.setText("Run active.")
        self._result_banner.setStyleSheet("")

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

    def _on_verification_started(self, layer_index: int, command: str):
        self._verify_lbl.setText(f"Layer {layer_index}: verifying")
        self._status_log.append(f"[Tester] Layer {layer_index}: {command}")

    def _on_traceback(self, key: str, trace: str):
        self._tracebacks[key] = trace
        self._traceback.setPlainText(trace)

    def _on_file_edited(self, filepath: str, content: str):
        self._file_contents[filepath] = content
        self._ensure_task_row(filepath, "written", self._layer_for_file(filepath), "File content written")
        self._preview.setPlainText(content)

    def _on_test_result(self, passed: bool, trace: str):
        if passed:
            self._traceback.setPlainText("Verification passed.")
        else:
            self._traceback.setPlainText(trace)

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
        self._traceback.setPlainText(
            self._tracebacks.get(filepath)
            or self._tracebacks.get(f"Layer {self._layer_for_file(filepath)}", "")
        )

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.request_stop()
            self._thread.wait()
        super().closeEvent(event)
