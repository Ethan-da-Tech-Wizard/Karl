from __future__ import annotations

import os
import time
import math
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QFrame, QSplitter, QSpinBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.engine.swarm_orchestrator import SwarmOrchestratorThread


class PhaseChip(QFrame):
    def __init__(self, name: str, label: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.label = label
        self.status = "idle"  # idle, running, done, error
        self.elapsed = 0.0
        self.setObjectName("phase-chip")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.lbl_name = QLabel(self.label, self)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 10pt;")

        self.lbl_status = QLabel("idle", self)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 8.5pt;")

        self.lbl_time = QLabel("", self)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet("font-size: 8pt; color: #888888;")

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_time)

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.update_style()

    def update_style(self, pulse_color=None):
        if self.status == "idle":
            bg = "#1A1A24"
            border = "#2A2A38"
            fg = "#888888"
        elif self.status == "running":
            bg = "#1B2E3C"
            border = pulse_color or "#00C2FF"
            fg = "#00C2FF"
        elif self.status == "done":
            bg = "#1B3520"
            border = "#4CAF50"
            fg = "#4CAF50"
        elif self.status == "error":
            bg = "#351B1B"
            border = "#F44336"
            fg = "#F44336"
        else:
            bg = "#1A1A24"
            border = "#2A2A38"
            fg = "#888888"

        self.setStyleSheet(f"""
            QFrame#phase-chip {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {fg};
                background: transparent;
            }}
        """)
        self.lbl_status.setText(self.status)
        if self.elapsed > 0:
            self.lbl_time.setText(f"{self.elapsed:.1f}s")
        else:
            self.lbl_time.setText("")


class CollapsiblePlanPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.toggle_btn = QPushButton("▶ Implementation Plan")
        self.toggle_btn.setObjectName("btn-ghost")
        self.toggle_btn.setStyleSheet("text-align: left; font-weight: bold; padding: 6px;")
        self.toggle_btn.clicked.connect(self.toggle)

        self.content = QTextEdit(self)
        self.content.setReadOnly(True)
        self.content.setVisible(False)

        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)

    def toggle(self):
        visible = not self.content.isVisible()
        self.content.setVisible(visible)
        self.toggle_btn.setText(f"{'▼' if visible else '▶'} Implementation Plan")


class SwarmWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._thread = None
        self._active_phase = None
        self._current_plan = None
        self._history = []

        # Setup 100ms ticker for phase elapsed times and border pulse
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("Swarm Workspace", self)
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        main_layout.addWidget(title)

        # Splitter for Left, Center, Right panels
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(1)

        # 1. Left Panel (Objective Composer)
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        left_title = QLabel("Objective Composer", self)
        left_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #E0E0E0;")
        left_layout.addWidget(left_title)

        # Multi-line objective input
        self._objective_input = QTextEdit(self)
        self._objective_input.setPlaceholderText("Enter swarm objective (e.g. 'Implement a user login form and write unit tests')")
        self._objective_input.setMinimumHeight(120)
        left_layout.addWidget(self._objective_input, 2)

        # Path input
        path_label = QLabel("Workspace Path:", self)
        path_label.setObjectName("lbl-muted")
        left_layout.addWidget(path_label)
        self._workspace_input = QLineEdit(self)
        self._workspace_input.setPlaceholderText("/path/to/workspace")
        # Populate from AppState last workspace
        self._workspace_input.setText(self.state.swarm_last_workspace)
        left_layout.addWidget(self._workspace_input)

        # Test command
        test_label = QLabel("Test Command:", self)
        test_label.setObjectName("lbl-muted")
        left_layout.addWidget(test_label)
        self._test_command_input = QLineEdit(self)
        self._test_command_input.setPlaceholderText("pytest tests/")
        self._test_command_input.setText("pytest tests/")
        left_layout.addWidget(self._test_command_input)

        # Hyperparams
        hyper_group = QGroupBox("Hyperparameters", self)
        hyper_layout = QHBoxLayout(hyper_group)
        hyper_layout.setSpacing(10)

        temp_lbl = QLabel("Temp:", self)
        self._temp_spin = QSpinBox(self)
        self._temp_spin.setRange(0, 100)
        self._temp_spin.setValue(20)  # default 0.2
        self._temp_spin.setSuffix("%")

        tokens_lbl = QLabel("Max Tokens:", self)
        self._tokens_spin = QSpinBox(self)
        self._tokens_spin.setRange(256, 8192)
        self._tokens_spin.setValue(2048)
        self._tokens_spin.setSingleStep(256)

        hyper_layout.addWidget(temp_lbl)
        hyper_layout.addWidget(self._temp_spin)
        hyper_layout.addWidget(tokens_lbl)
        hyper_layout.addWidget(self._tokens_spin)
        left_layout.addWidget(hyper_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self._launch_btn = QPushButton("Launch", self)
        self._launch_btn.setObjectName("btn-primary")
        self._launch_btn.clicked.connect(self._on_launch)

        self._stop_btn = QPushButton("Stop", self)
        self._stop_btn.setObjectName("btn-danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)

        btn_layout.addWidget(self._launch_btn)
        btn_layout.addWidget(self._stop_btn)
        left_layout.addLayout(btn_layout)

        # Recent objectives list
        recent_label = QLabel("Recent Objectives:", self)
        recent_label.setObjectName("lbl-muted")
        left_layout.addWidget(recent_label)

        self._recent_list = QListWidget(self)
        self._recent_list.itemClicked.connect(self._on_history_clicked)
        left_layout.addWidget(self._recent_list, 1)

        splitter.addWidget(left_widget)

        # 2. Center Panel (Agent Timeline)
        center_widget = QWidget(self)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(8, 0, 8, 0)
        center_layout.setSpacing(10)

        center_title = QLabel("Agent Timeline", self)
        center_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #E0E0E0;")
        center_layout.addWidget(center_title)

        # Chips row
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)
        self._chips = {
            "architect": PhaseChip("architect", "Architect", self),
            "coder": PhaseChip("coder", "Coder", self),
            "tester": PhaseChip("tester", "Tester", self)
        }
        for name in ("architect", "coder", "tester"):
            chips_layout.addWidget(self._chips[name])
        center_layout.addLayout(chips_layout)

        # Status log scroll area
        log_label = QLabel("Live Status Log:", self)
        log_label.setObjectName("lbl-muted")
        center_layout.addWidget(log_label)

        self._status_log = QTextEdit(self)
        self._status_log.setReadOnly(True)
        self._status_log.setFont(QFont("Monospace", 9))
        self._status_log.setStyleSheet("background-color: #0E0F15; border: 1px solid #1A1A24;")
        center_layout.addWidget(self._status_log, 2)

        # Plan panel
        self._plan_panel = CollapsiblePlanPanel(self)
        center_layout.addWidget(self._plan_panel, 1)

        splitter.addWidget(center_widget)

        # 3. Right Panel (File Edit Tracker)
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        right_title = QLabel("Proposed Edits", self)
        right_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #E0E0E0;")
        right_layout.addWidget(right_title)

        # Proposed edits list
        self._file_list = QListWidget(self)
        self._file_list.setSpacing(4)
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        right_layout.addWidget(self._file_list, 1)

        # Preview area
        preview_label = QLabel("Proposed Content Preview:", self)
        preview_label.setObjectName("lbl-muted")
        right_layout.addWidget(preview_label)

        self._preview_edit = QTextEdit(self)
        self._preview_edit.setReadOnly(True)
        self._preview_edit.setFont(QFont("Monospace", 9))
        self._preview_edit.setStyleSheet("background-color: #0E0F15; border: 1px solid #1A1A24;")
        right_layout.addWidget(self._preview_edit, 2)

        # Informational "Open in editor" label
        self._info_lbl = QLabel("Open in editor (double click to open in editor)", self)
        self._info_lbl.setObjectName("lbl-muted")
        self._info_lbl.setStyleSheet("font-size: 8pt; font-style: italic;")
        right_layout.addWidget(self._info_lbl)

        # Test result banner
        self._test_banner = QLabel(self)
        self._test_banner.setWordWrap(True)
        self._test_banner.setVisible(False)
        right_layout.addWidget(self._test_banner)

        # Summary section
        self._summary_title = QLabel("", self)
        self._summary_text = QLabel("", self)
        self._summary_text.setWordWrap(True)
        self._summary_text.setObjectName("lbl-muted")
        right_layout.addWidget(self._summary_title)
        right_layout.addWidget(self._summary_text)

        splitter.addWidget(right_widget)

        # Layout stretches
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 3)
        main_layout.addWidget(splitter, 1)

    def _load_history(self):
        self._history = self.state.memory.load_swarm_history()
        self._refresh_history_list()

    def _refresh_history_list(self):
        self._recent_list.clear()
        for item in self._history:
            obj = item.get("objective", "")
            # Shorten objective for list display
            disp = obj if len(obj) <= 45 else obj[:42] + "..."
            list_item = QListWidgetItem(disp)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            list_item.setToolTip(obj)
            self._recent_list.addItem(list_item)

    def _add_to_history(self, objective, workspace_path, test_command):
        history_item = {
            "objective": objective,
            "workspace_path": workspace_path,
            "test_command": test_command,
            "temperature": self._temp_spin.value(),
            "max_tokens": self._tokens_spin.value()
        }
        # Filter duplicates
        self._history = [x for x in self._history if x["objective"] != objective]
        self._history.insert(0, history_item)
        self._history = self._history[:10]
        self.state.memory.save_swarm_history(self._history)
        self._refresh_history_list()

    def _on_history_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self._objective_input.setPlainText(data.get("objective", ""))
            self._workspace_input.setText(data.get("workspace_path", ""))
            self._test_command_input.setText(data.get("test_command", "pytest tests/"))
            if "temperature" in data:
                self._temp_spin.setValue(data["temperature"])
            if "max_tokens" in data:
                self._tokens_spin.setValue(data["max_tokens"])

    def _on_tick(self):
        if self._active_phase:
            chip = self._chips.get(self._active_phase)
            if chip:
                chip.elapsed += 0.1

        # Border pulse animation for running chips
        if not self.state.reduced_motion:
            alpha = (math.sin(time.time() * 6) + 1) / 2
            pulse_color = f"rgba(0, 194, 255, {int(50 + 205 * alpha)})"
            for name, chip in self._chips.items():
                if chip.status == "running":
                    chip.update_style(pulse_color)
                else:
                    chip.update_style()
        else:
            for name, chip in self._chips.items():
                chip.update_style()

    def set_active_phase(self, phase_name: str):
        if self._active_phase == phase_name:
            return

        # Complete old phase
        if self._active_phase:
            old_chip = self._chips.get(self._active_phase)
            if old_chip and old_chip.status == "running":
                old_chip.status = "done"
                old_chip.update_style()

        # Set new phase running
        self._active_phase = phase_name
        new_chip = self._chips.get(phase_name)
        if new_chip:
            new_chip.status = "running"
            new_chip.update_style()

    def _on_launch(self):
        objective = self._objective_input.toPlainText().strip()
        workspace_path = self._workspace_input.text().strip()
        test_command = self._test_command_input.text().strip()

        if not objective or not workspace_path:
            QMessageBox.warning(self, "Validation Error", "Objective and Workspace Path are required.")
            return

        # Update AppState
        self.state.swarm_running = True
        self.state.swarm_last_objective = objective
        self.state.swarm_last_workspace = workspace_path

        # Save to history
        self._add_to_history(objective, workspace_path, test_command)

        # UI updates
        self._launch_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_log.clear()
        self._plan_panel.content.clear()
        self._plan_panel.content.setVisible(False)
        self._plan_panel.toggle_btn.setText("▶ Implementation Plan")
        self._file_list.clear()
        self._preview_edit.clear()
        self._test_banner.hide()
        self._summary_title.setText("")
        self._summary_text.setText("")
        self._current_plan = None

        # Reset chips
        for name, chip in self._chips.items():
            chip.status = "idle"
            chip.elapsed = 0.0
            chip.update_style()

        self._active_phase = "architect"
        self._chips["architect"].status = "running"

        # Instantiate Thread
        hyperparams = {
            "temperature": self._temp_spin.value() / 100.0,
            "max_tokens": self._tokens_spin.value()
        }
        self._thread = SwarmOrchestratorThread(
            workspace_path=workspace_path,
            objective=objective,
            test_command=test_command,
            hyperparams=hyperparams
        )
        self._thread.status_update.connect(self._on_status_update)
        self._thread.task_plan_created.connect(self._on_plan_created)
        self._thread.file_edited.connect(self._on_file_edited)
        self._thread.test_result.connect(self._on_test_result)
        self._thread.finished_swarm.connect(self._on_finished_swarm)

        self._timer.start(100)
        self._thread.start()

    def _on_stop(self):
        if self._thread and self._thread.isRunning():
            self._on_status_update("[Swarm] Stop requested by user. Terminating thread...")
            self._thread.request_stop()
            self._thread.wait()
        self._on_finished_swarm(False, "Stopped by user.")

    def _on_status_update(self, message: str):
        self._status_log.append(message)
        # Parse phase transitions
        if "[Architect]" in message:
            self.set_active_phase("architect")
        elif "[Coder]" in message:
            self.set_active_phase("coder")
        elif "[Tester]" in message:
            self.set_active_phase("tester")

    def _on_plan_created(self, plan: dict):
        self._current_plan = plan
        explanation = plan.get("explanation", "")
        tasks = plan.get("tasks", [])

        html = "<div style='font-family: sans-serif; color: #E0E0E0;'>"
        html += "<h3 style='color: #00C2FF; margin-top: 0;'>Architect Plan Summary</h3>"
        html += f"<p><b>Explanation:</b> {explanation}</p>"
        html += "<h4>Proposed Edits:</h4>"
        html += "<ul style='padding-left: 20px;'>"
        for task in tasks:
            filepath = task.get("filepath", "")
            instructions = task.get("instructions", "")
            html += f"<li><b>{filepath}</b>: {instructions}</li>"
        html += "</ul></div>"

        self._plan_panel.content.setHtml(html)
        self._plan_panel.content.setVisible(True)
        self._plan_panel.toggle_btn.setText("▼ Implementation Plan")

    def _on_file_edited(self, filepath: str, content: str):
        # Calculate line delta
        lines_new = len(content.splitlines())
        lines_old = 0
        abs_path = os.path.join(self._workspace_input.text().strip(), filepath)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines_old = len(f.read().splitlines())
            except Exception:
                pass
        delta = lines_new - lines_old
        delta_str = f"+{delta}" if delta >= 0 else f"{delta}"

        # Determine summary
        summary = "File modified by Coder Agent."
        if self._current_plan:
            for task in self._current_plan.get("tasks", []):
                if task.get("filepath") == filepath:
                    summary = task.get("instructions", "")
                    if len(summary) > 60:
                        summary = summary[:57] + "..."
                    break

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, (filepath, content))
        item.setText(f"📄 {filepath}  [{delta_str} lines]\n   {summary}")
        self._file_list.addItem(item)

        # Highlight/select first added item
        if self._file_list.count() == 1:
            self._file_list.setCurrentRow(0)

    def _on_file_selected(self, current, previous):
        if not current:
            self._preview_edit.clear()
            return
        filepath, content = current.data(Qt.ItemDataRole.UserRole)
        self._preview_edit.setPlainText(content)

    def _on_test_result(self, passed: bool, trace: str):
        self._test_banner.setVisible(True)
        if passed:
            self._test_banner.setText("✓ Tests passed successfully!")
            self._test_banner.setStyleSheet("""
                background-color: #1B3520;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            """)
        else:
            first_lines = "\n".join(trace.splitlines()[:10])
            if len(trace.splitlines()) > 10:
                first_lines += "\n..."
            self._test_banner.setText(f"✗ Tests failed:\n{first_lines}")
            self._test_banner.setStyleSheet("""
                background-color: #351B1B;
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
            """)

    def _on_finished_swarm(self, success: bool, summary: str):
        self.state.swarm_running = False
        self._launch_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._timer.stop()

        # Update active chip status
        if self._active_phase:
            chip = self._chips.get(self._active_phase)
            if chip:
                chip.status = "done" if success else "error"
                chip.update_style()
        self._active_phase = None

        self._summary_title.setText("Swarm Completed Successfully" if success else "Swarm Execution Failed")
        self._summary_title.setStyleSheet(f"font-weight: bold; font-size: 11pt; color: {'#4CAF50' if success else '#F44336'}; margin-top: 8px;")
        self._summary_text.setText(summary)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.request_stop()
            self._thread.wait()
        super().closeEvent(event)
