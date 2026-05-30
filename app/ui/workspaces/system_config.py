"""
System — hardware info, model management, generation defaults, about.
"""

from __future__ import annotations

import json
import os
import html

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QDoubleSpinBox, QSpinBox, QFileDialog,
    QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt

from app.ui.themes import MONO


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _row(label_text: str, widget: QWidget) -> QWidget:
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 2, 0, 2)
    l.setSpacing(12)
    lbl = QLabel(label_text)
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
        root.setSpacing(12)

        title = QLabel("System")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
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
        layout.setSpacing(12)

        # Active Model Panel
        active_panel = QWidget()
        active_panel.setObjectName("panel")
        ap_layout = QVBoxLayout(active_panel)
        ap_layout.setContentsMargins(12, 12, 12, 12)
        ap_layout.setSpacing(8)

        ap_layout.addWidget(_section("ACTIVE MODEL"))

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
        ap_layout.addWidget(model_row)

        load_btn = QPushButton("load model")
        load_btn.setObjectName("btn-primary")
        load_btn.clicked.connect(self._load_model)
        ap_layout.addWidget(load_btn)

        self._model_status = QLabel("")
        self._model_status.setObjectName("lbl-muted")
        self._model_status.setWordWrap(True)
        ap_layout.addWidget(self._model_status)
        
        layout.addWidget(active_panel)

        # Available Models Panel
        available_panel = QWidget()
        available_panel.setObjectName("panel")
        avp_layout = QVBoxLayout(available_panel)
        avp_layout.setContentsMargins(12, 12, 12, 12)
        avp_layout.setSpacing(8)

        avp_layout.addWidget(_section("AVAILABLE MODELS"))

        self._model_list = QTextBrowser()
        self._model_list.setFixedHeight(160)
        self._model_list.setPlaceholderText("scanning data/models/...")
        self._model_list.setTextFormat(Qt.TextFormat.RichText)
        avp_layout.addWidget(self._model_list)
        self._scan_models()

        layout.addWidget(available_panel)
        layout.addStretch()
        return w

    # ── defaults tab ──────────────────────────────────────────────────────────

    def _build_params_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        params_panel = QWidget()
        params_panel.setObjectName("panel")
        pp_layout = QVBoxLayout(params_panel)
        pp_layout.setContentsMargins(12, 12, 12, 12)
        pp_layout.setSpacing(10)

        pp_layout.addWidget(_section("GENERATION DEFAULTS"))
        
        desc = QLabel(
            "These apply as defaults to new Workbench sessions. Each session can override them."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        pp_layout.addWidget(desc)

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
            ("Temperature", self._temp_spin),
            ("Top-P",       self._topp_spin),
            ("Max Tokens",  self._maxtok_spin),
        ):
            pp_layout.addWidget(_row(label, widget))

        apply_btn = QPushButton("apply defaults")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._apply_defaults)
        pp_layout.addWidget(apply_btn)

        layout.addWidget(params_panel)
        layout.addStretch()
        return w

    # ── identity tab ──────────────────────────────────────────────────────────

    def _build_identity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        identity_panel = QWidget()
        identity_panel.setObjectName("panel")
        ip_layout = QVBoxLayout(identity_panel)
        ip_layout.setContentsMargins(12, 12, 12, 12)
        ip_layout.setSpacing(8)

        ip_layout.addWidget(_section("SYSTEM PROMPT"))
        
        desc = QLabel(
            "This prompt defines Karl's persona and is sent before every conversation."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        ip_layout.addWidget(desc)

        from PyQt6.QtWidgets import QTextEdit
        self._system_edit = QTextEdit()
        self._system_edit.setPlainText(
            "You are Karl, a precise and thoughtful AI assistant. "
            "Reason carefully before responding."
        )
        ip_layout.addWidget(self._system_edit, 1)

        apply_btn = QPushButton("apply system prompt")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._apply_identity)
        ip_layout.addWidget(apply_btn)

        layout.addWidget(identity_panel, 1)
        return w

    # ── hardware tab ──────────────────────────────────────────────────────────

    def _build_hardware_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Hardware Panel
        hw_panel = QWidget()
        hw_panel.setObjectName("panel")
        hwp_layout = QVBoxLayout(hw_panel)
        hwp_layout.setContentsMargins(12, 12, 12, 12)
        hwp_layout.setSpacing(8)

        hwp_layout.addWidget(_section("HARDWARE PROFILE"))

        self._hw_view = QTextBrowser()
        self._hw_view.setFixedHeight(130)
        self._hw_view.setTextFormat(Qt.TextFormat.RichText)
        hwp_layout.addWidget(self._hw_view)

        refresh_btn = QPushButton("refresh hardware")
        refresh_btn.clicked.connect(self._refresh_hardware)
        hwp_layout.addWidget(refresh_btn)

        layout.addWidget(hw_panel)

        # About Panel
        about_panel = QWidget()
        about_panel.setObjectName("panel")
        ap_layout = QVBoxLayout(about_panel)
        ap_layout.setContentsMargins(12, 12, 12, 12)
        ap_layout.setSpacing(8)

        ap_layout.addWidget(_section("ABOUT KARL"))
        
        about = QLabel(
            "Karl &mdash; Privacy-first Offline LLM Introspection Environment<br/>"
            "Zero network calls &middot; In-process inference &middot; Immutable trace logs<br/>"
            "<a href='https://github.com/ethan-da-tech-wizard/karl' style='color:#00C2FF; text-decoration:none;'>https://github.com/ethan-da-tech-wizard/karl</a>"
        )
        about.setObjectName("lbl-muted")
        about.setWordWrap(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setOpenExternalLinks(True)
        ap_layout.addWidget(about)

        layout.addWidget(about_panel)
        layout.addStretch()
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _refresh_hardware(self):
        from core.hardware_scout import get_hardware_profile
        p = get_hardware_profile()
        
        ram = p.get('ram_gb', '?')
        vram = p.get('vram_gb', 'N/A')
        storage = p.get('storage_gb', '?')
        
        if isinstance(vram, (int, float)):
            vram_str = f"{vram:.1f} GB"
        else:
            vram_str = str(vram)
            
        html_content = (
            f"<div style='font-family:{MONO}; color:#E4E4F0; line-height:1.6;'>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:100px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>RAM</span>"
            f"<span style='font-size:11pt; color:#00C2FF; font-weight:bold;'>{ram} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB</span></span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:100px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>VRAM</span>"
            f"<span style='font-size:11pt; color:#2DD4A0; font-weight:bold;'>{vram_str}</span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:100px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>STORAGE</span>"
            f"<span style='font-size:11pt; color:#F0B030; font-weight:bold;'>{storage} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB free</span></span>"
            f"</div>"
            f"</div>"
        )
        self._hw_view.setHtml(html_content)

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
            self._scan_models() # Refresh list to reflect loaded active model
            active = {"filename": name}
            os.makedirs("data", exist_ok=True)
            with open("data/active_model.json", "w") as f:
                json.dump(active, f)
        except Exception as e:
            self._model_status.setText(f"error: {e}")

    def _scan_models(self):
        models_dir = "data/models"
        if not os.path.exists(models_dir):
            self._model_list.setHtml("<span style='color:#F05050;'>data/models/ not found</span>")
            return
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not files:
            self._model_list.setHtml("<span style='color:#505068;'>no .gguf models in data/models/</span>")
            return
        
        active_name = self.state.model_name or "none"
        if active_name == "none":
            # Try to read active model json
            active_path = "data/active_model.json"
            if os.path.exists(active_path):
                try:
                    with open(active_path, "r") as f:
                        active_name = json.load(f).get("filename", "none")
                except Exception:
                    pass

        html_lines = []
        for f in sorted(files):
            path = os.path.join(models_dir, f)
            try:
                size_bytes = os.path.getsize(path)
                size_gb = size_bytes / (1024 * 1024 * 1024)
                size_str = f"{size_gb:.2f} GB"
            except Exception:
                size_str = "unknown size"
                
            is_active = (f == active_name)
            if is_active:
                indicator = "<span style='color:#2DD4A0; font-weight:bold;'>[ACTIVE]</span>"
                bg_style = "background: #161625; border: 1px solid #383850;"
                color_style = "color: #00C2FF; font-weight:bold;"
            else:
                indicator = "<span style='color:#505068;'>[inactive]</span>"
                bg_style = "background: #0D0D16; border: 1px solid #252535;"
                color_style = "color: #E4E4F0;"
                
            html_lines.append(
                f"<div style='margin-bottom:6px; padding:6px 10px; border-radius:4px; {bg_style}'>"
                f"<span style='{color_style}'>{html.escape(f)}</span> &middot; "
                f"<span style='color:#9090A8;'>{size_str}</span> &middot; "
                f"{indicator}"
                f"</div>"
            )
        
        self._model_list.setHtml("".join(html_lines))

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
