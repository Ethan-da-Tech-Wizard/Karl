"""
System — hardware info, model management, generation defaults, about.
"""

from __future__ import annotations

import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QDoubleSpinBox, QSpinBox, QFileDialog,
    QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _row(label: str, widget: QWidget) -> QWidget:
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(12)
    lbl = QLabel(label)
    lbl.setFixedWidth(130)
    lbl.setObjectName("lbl-muted")
    l.addWidget(lbl)
    l.addWidget(widget)
    l.addStretch()
    return w


class SystemConfigWorkspace(QWidget):
    def __init__(self, state, workbench_ref=None, parent=None):
        super().__init__(parent)
        self.state = state
        self._workbench = workbench_ref
        self.setObjectName("workspace-root")
        self._build_ui()
        self._refresh_hardware()

    def set_workbench(self, wb):
        self._workbench = wb

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("System")
        title.setObjectName("lbl-accent")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_model_tab(), "Model")
        tabs.addTab(self._build_params_tab(), "Defaults")
        tabs.addTab(self._build_identity_tab(), "Identity")
        tabs.addTab(self._build_hardware_tab(), "Hardware")
        root.addWidget(tabs, 1)

    # ── model tab ─────────────────────────────────────────────────────────────

    def _build_model_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(_section("ACTIVE MODEL"))

        model_row = QWidget()
        mr = QHBoxLayout(model_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(8)
        self._model_path_input = QLineEdit()
        self._model_path_input.setPlaceholderText("path to .gguf file...")
        mr.addWidget(self._model_path_input, 1)
        browse = QPushButton("browse")
        browse.clicked.connect(self._browse_model)
        mr.addWidget(browse)
        layout.addWidget(model_row)

        load_btn = QPushButton("load model")
        load_btn.setObjectName("btn-primary")
        load_btn.clicked.connect(self._load_model)
        layout.addWidget(load_btn)

        self._model_status = QLabel("")
        self._model_status.setObjectName("lbl-muted")
        self._model_status.setWordWrap(True)
        layout.addWidget(self._model_status)

        layout.addWidget(_hline())
        layout.addWidget(_section("AVAILABLE MODELS"))

        self._model_list = QTextBrowser()
        self._model_list.setFixedHeight(160)
        layout.addWidget(self._model_list)
        self._scan_models()

        layout.addStretch()
        return w

    # ── defaults tab ──────────────────────────────────────────────────────────

    def _build_params_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(_section("GENERATION DEFAULTS"))
        layout.addWidget(QLabel(
            "These apply to Workbench sessions. Each session can override them."
        ))

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.05)
        self._temp_spin.setValue(0.7)
        self._temp_spin.setFixedWidth(90)

        self._topp_spin = QDoubleSpinBox()
        self._topp_spin.setRange(0.0, 1.0)
        self._topp_spin.setSingleStep(0.05)
        self._topp_spin.setValue(0.95)
        self._topp_spin.setFixedWidth(90)

        self._maxtok_spin = QSpinBox()
        self._maxtok_spin.setRange(64, 8192)
        self._maxtok_spin.setSingleStep(128)
        self._maxtok_spin.setValue(2048)
        self._maxtok_spin.setFixedWidth(90)

        for label, widget in (
            ("temperature", self._temp_spin),
            ("top-p",       self._topp_spin),
            ("max tokens",  self._maxtok_spin),
        ):
            layout.addWidget(_row(label, widget))

        apply_btn = QPushButton("apply defaults")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._apply_defaults)
        layout.addWidget(apply_btn)

        layout.addStretch()
        return w

    # ── identity tab ──────────────────────────────────────────────────────────

    def _build_identity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(_section("SYSTEM PROMPT"))
        layout.addWidget(QLabel(
            "This is sent to the model before every conversation."
        ))

        from PyQt6.QtWidgets import QTextEdit
        self._system_edit = QTextEdit()
        self._system_edit.setPlainText(
            "You are Karl, a precise and thoughtful AI assistant. "
            "Reason carefully before responding."
        )
        layout.addWidget(self._system_edit, 1)

        apply_btn = QPushButton("apply system prompt")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._apply_identity)
        layout.addWidget(apply_btn)

        return w

    # ── hardware tab ──────────────────────────────────────────────────────────

    def _build_hardware_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(_section("HARDWARE PROFILE"))

        self._hw_view = QTextBrowser()
        self._hw_view.setFixedHeight(200)
        layout.addWidget(self._hw_view)

        refresh_btn = QPushButton("refresh")
        refresh_btn.clicked.connect(self._refresh_hardware)
        layout.addWidget(refresh_btn)

        layout.addWidget(_hline())
        layout.addWidget(_section("ABOUT"))
        about = QLabel(
            "Karl — Privacy-first LLM Introspection Environment\n"
            "Zero network calls · In-process inference · Immutable trace logs\n"
            "https://github.com/ethan-da-tech-wizard/karl"
        )
        about.setObjectName("lbl-muted")
        about.setWordWrap(True)
        layout.addWidget(about)

        layout.addStretch()
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _refresh_hardware(self):
        from core.hardware_scout import get_hardware_profile
        p = get_hardware_profile()
        lines = [
            f"RAM      {p.get('ram_gb', '?')} GB",
            f"VRAM     {p.get('vram_gb', 'N/A')} GB",
            f"storage  {p.get('storage_gb', '?')} GB free",
        ]
        self._hw_view.setPlainText("\n".join(lines))

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GGUF model", "data/models", "GGUF (*.gguf);;All Files (*)"
        )
        if path:
            self._model_path_input.setText(path)

    def _load_model(self):
        path = self._model_path_input.text().strip()
        if not path:
            self._model_status.setText("enter a model path first")
            return
        if not os.path.exists(path):
            self._model_status.setText(f"file not found: {path}")
            return

        from app.engine.model_loader import ModelLoader
        ModelLoader.reset_instance()
        try:
            ModelLoader.get_instance(model_path=path)
            name = os.path.basename(path)
            self.state.model_name = name
            self._model_status.setText(f"loaded: {name}")
            active = {"filename": name}
            os.makedirs("data", exist_ok=True)
            with open("data/active_model.json", "w") as f:
                json.dump(active, f)
        except Exception as e:
            self._model_status.setText(f"error: {e}")

    def _scan_models(self):
        models_dir = "data/models"
        if not os.path.exists(models_dir):
            self._model_list.setPlainText("data/models/ not found")
            return
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not files:
            self._model_list.setPlainText("no .gguf files in data/models/")
            return
        self._model_list.setPlainText("\n".join(files))

    def _apply_defaults(self):
        if self._workbench:
            self._workbench.set_hyperparams({
                "temperature": self._temp_spin.value(),
                "top_p":       self._topp_spin.value(),
                "max_tokens":  self._maxtok_spin.value(),
            })

    def _apply_identity(self):
        if self._workbench:
            self._workbench.set_system_prompt(
                self._system_edit.toPlainText().strip()
            )
