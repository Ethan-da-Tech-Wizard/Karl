from __future__ import annotations

import html
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QLabel, QSpinBox, QMessageBox, QProgressBar,
    QComboBox, QCheckBox, QLineEdit,
)

from app.ui.themes import MONO
from app.vision.vision_model_loader import (
    VisionModelLoader,
    installed_vision_models,
    set_active_vision_model,
)
from .common import _section

logger = logging.getLogger("karl.system_config")

class VisionHardwarePanelMixin:
    def _build_vision_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        runtime_panel = QWidget()
        runtime_panel.setObjectName("panel")
        rp = QVBoxLayout(runtime_panel)
        rp.setContentsMargins(12, 12, 12, 12)
        rp.setSpacing(8)
        rp.addWidget(_section("VISION RUNTIME"))

        desc = QLabel(
            "Karl vision stays offline. OCR can run immediately when Tesseract is installed; "
            "pixel-level image description requires a local GGUF vision model plus its matching projector."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        rp.addWidget(desc)

        self._vision_runtime_status = QLabel("")
        self._vision_runtime_status.setObjectName("lbl-muted")
        self._vision_runtime_status.setWordWrap(True)
        rp.addWidget(self._vision_runtime_status)

        model_row = QWidget()
        mr = QHBoxLayout(model_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(8)
        self._vision_model_combo = QComboBox()
        mr.addWidget(self._vision_model_combo, 1)

        active_btn = QPushButton("set active")
        active_btn.setObjectName("btn-secondary")
        active_btn.clicked.connect(self._set_active_vision_model_from_combo)
        mr.addWidget(active_btn)

        load_btn = QPushButton("load now")
        load_btn.setObjectName("btn-primary")
        load_btn.clicked.connect(self._load_active_vision_model)
        mr.addWidget(load_btn)

        reset_btn = QPushButton("reset")
        reset_btn.setObjectName("btn-ghost")
        reset_btn.clicked.connect(self._reset_vision_runtime)
        mr.addWidget(reset_btn)
        rp.addWidget(model_row)

        layout.addWidget(runtime_panel)

        registry_panel = QWidget()
        registry_panel.setObjectName("panel")
        vp = QVBoxLayout(registry_panel)
        vp.setContentsMargins(12, 12, 12, 12)
        vp.setSpacing(8)
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(_section("LOCAL VISION MODEL REGISTRY"))
        refresh_btn = QPushButton("refresh")
        refresh_btn.setObjectName("btn-ghost")
        refresh_btn.clicked.connect(self._refresh_vision_status)
        hl.addWidget(refresh_btn)
        vp.addWidget(header)

        self._vision_registry_view = QTextBrowser()
        self._vision_registry_view.setMinimumHeight(260)
        vp.addWidget(self._vision_registry_view, 1)
        layout.addWidget(registry_panel, 1)

        self._refresh_vision_status()
        return w


    def _refresh_vision_status(self):
        if not hasattr(self, "_vision_runtime_status"):
            return

        status = VisionModelLoader.status()
        backend = "available" if status["backend_available"] else "blocked"
        loaded = "loaded" if status["loaded"] else "not loaded"
        active = status.get("active_name") or "none"
        lines = [
            f"Backend: {backend}",
            f"Runtime: {loaded}",
            f"Active model: {active}",
        ]
        if status.get("backend_error"):
            lines.append(f"Backend detail: {status['backend_error']}")
        if status.get("last_error"):
            lines.append(f"Last error: {status['last_error']}")
        self._vision_runtime_status.setText("\n".join(lines))

        current = self._vision_model_combo.currentData()
        self._vision_model_combo.blockSignals(True)
        self._vision_model_combo.clear()
        rows = installed_vision_models()
        for row in rows:
            ready = row.get("model_installed") and row.get("projector_installed")
            suffix = "ready" if ready else "missing files"
            self._vision_model_combo.addItem(f"{row['name']} ({suffix})", row["id"])
        if current:
            idx = self._vision_model_combo.findData(current)
            if idx >= 0:
                self._vision_model_combo.setCurrentIndex(idx)
        self._vision_model_combo.blockSignals(False)

        html_rows = []
        for row in rows:
            model_state = "present" if row.get("model_installed") else "missing"
            projector_state = "present" if row.get("projector_installed") else "missing"
            html_rows.append(
                "<div style='margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.08);'>"
                f"<b style='color:#00C2FF;'>{html.escape(row['name'])}</b><br/>"
                f"<span style='color:#9090A8;'>Family:</span> {html.escape(row['family'])} &middot; "
                f"<span style='color:#9090A8;'>Context:</span> {int(row['n_ctx']):,}<br/>"
                f"<span style='color:#9090A8;'>Model:</span> {html.escape(row['model_path'])} "
                f"<b>{model_state}</b><br/>"
                f"<span style='color:#9090A8;'>Projector:</span> {html.escape(row['projector_path'])} "
                f"<b>{projector_state}</b><br/>"
                f"<span style='color:#9090A8;'>RAM:</span> &ge; {row['min_ram_gb']} GB &middot; "
                f"<span style='color:#9090A8;'>VRAM:</span> &ge; {row['min_vram_gb']} GB<br/>"
                f"<span style='color:#B8F7FF;'>{html.escape(row.get('strengths', ''))}</span><br/>"
                f"<span style='color:#9090A8;'>{html.escape(row.get('notes', ''))}</span>"
                "</div>"
            )
        self._vision_registry_view.setHtml(
            f"<div style='font-family:{MONO}; font-size:9pt; line-height:1.45;'>"
            + "".join(html_rows or ["No registry entries found."])
            + "</div>"
        )


    def _set_active_vision_model_from_combo(self):
        model_id = self._vision_model_combo.currentData()
        if not model_id:
            return
        set_active_vision_model(model_id)
        VisionModelLoader.reset()
        self._refresh_vision_status()
        QMessageBox.information(self, "Vision Model Selected", f"Active vision model set to {model_id}.")


    def _load_active_vision_model(self):
        model_id = self._vision_model_combo.currentData()
        VisionModelLoader.load(model_id=model_id)
        self._refresh_vision_status()


    def _reset_vision_runtime(self):
        VisionModelLoader.reset()
        self._refresh_vision_status()

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
        hwp_layout.setContentsMargins(16, 16, 16, 16)
        hwp_layout.setSpacing(12)

        hwp_layout.addWidget(_section("HARDWARE PROFILE & METERS"))

        # CPU meter
        cpu_row = QWidget()
        cpu_l = QHBoxLayout(cpu_row)
        cpu_l.setContentsMargins(0, 0, 0, 0)
        cpu_lbl = QLabel("CPU Load:")
        cpu_lbl.setFixedWidth(100)
        cpu_lbl.setObjectName("lbl-muted")
        self._cpu_progress = QProgressBar()
        self._cpu_progress.setRange(0, 100)
        self._cpu_progress.setValue(0)
        self._cpu_progress.setFixedHeight(14)
        cpu_l.addWidget(cpu_lbl)
        cpu_l.addWidget(self._cpu_progress)
        hwp_layout.addWidget(cpu_row)

        # RAM meter
        ram_row = QWidget()
        ram_l = QHBoxLayout(ram_row)
        ram_l.setContentsMargins(0, 0, 0, 0)
        ram_lbl = QLabel("Memory:")
        ram_lbl.setFixedWidth(100)
        ram_lbl.setObjectName("lbl-muted")
        self._ram_progress = QProgressBar()
        self._ram_progress.setRange(0, 100)
        self._ram_progress.setValue(0)
        self._ram_progress.setFixedHeight(14)
        ram_l.addWidget(ram_lbl)
        ram_l.addWidget(self._ram_progress)
        hwp_layout.addWidget(ram_row)
        
        # Disk Space meter
        disk_row = QWidget()
        disk_l = QHBoxLayout(disk_row)
        disk_l.setContentsMargins(0, 0, 0, 0)
        disk_lbl = QLabel("Disk Free:")
        disk_lbl.setFixedWidth(100)
        disk_lbl.setObjectName("lbl-muted")
        self._disk_progress = QProgressBar()
        self._disk_progress.setRange(0, 100)
        self._disk_progress.setValue(0)
        self._disk_progress.setFixedHeight(14)
        disk_l.addWidget(disk_lbl)
        disk_l.addWidget(self._disk_progress)
        hwp_layout.addWidget(disk_row)

        self._hw_view = QTextBrowser()
        self._hw_view.setFixedHeight(120)
        hwp_layout.addWidget(self._hw_view)

        refresh_btn = QPushButton("refresh profiles")
        refresh_btn.setToolTip("Re-scout RAM, VRAM, and storage specifications")
        refresh_btn.clicked.connect(self._refresh_hardware)
        hwp_layout.addWidget(refresh_btn)

        layout.addWidget(hw_panel)

        engine_panel = QWidget()
        engine_panel.setObjectName("panel")
        ep_layout = QVBoxLayout(engine_panel)
        ep_layout.setContentsMargins(16, 16, 16, 16)
        ep_layout.setSpacing(10)
        ep_layout.addWidget(_section("REMOTE MODEL OFFLOADING"))

        self._remote_engine_check = QCheckBox("Remote Engine Mode")
        self._remote_engine_check.setChecked(
            bool(getattr(self.state, "remote_engine_enabled", False))
            or getattr(self.state, "engine_mode", "local") == "remote"
        )
        self._remote_engine_check.stateChanged.connect(self._on_engine_config_changed)
        ep_layout.addWidget(self._remote_engine_check)

        url_row = QWidget()
        url_lay = QHBoxLayout(url_row)
        url_lay.setContentsMargins(0, 0, 0, 0)
        url_lbl = QLabel("Remote Server URL:")
        url_lbl.setObjectName("lbl-muted")
        url_lbl.setFixedWidth(180)
        url_lay.addWidget(url_lbl)
        self._remote_url_input = QLineEdit()
        self._remote_url_input.setPlaceholderText("wss://localhost:8080")
        self._remote_url_input.setText(
            getattr(self.state, "remote_engine_url", "")
            or getattr(self.state, "remote_server_url", "")
            or "wss://localhost:8080"
        )
        self._remote_url_input.editingFinished.connect(self._on_engine_config_changed)
        url_lay.addWidget(self._remote_url_input, 1)
        ep_layout.addWidget(url_row)

        token_row = QWidget()
        token_lay = QHBoxLayout(token_row)
        token_lay.setContentsMargins(0, 0, 0, 0)
        token_lbl = QLabel("Auth Token:")
        token_lbl.setObjectName("lbl-muted")
        token_lbl.setFixedWidth(180)
        token_lay.addWidget(token_lbl)
        self._remote_token_input = QLineEdit()
        self._remote_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._remote_token_input.setPlaceholderText("bridge token or password")
        self._remote_token_input.setText(
            getattr(self.state, "remote_engine_token", "")
            or getattr(self.state, "remote_auth_token", "")
        )
        self._remote_token_input.editingFinished.connect(self._on_engine_config_changed)
        token_lay.addWidget(self._remote_token_input, 1)
        ep_layout.addWidget(token_row)

        self._remote_status_label = QLabel("")
        self._remote_status_label.setObjectName("lbl-muted")
        self._remote_status_label.setWordWrap(True)
        ep_layout.addWidget(self._remote_status_label)
        self._sync_engine_controls_enabled()

        layout.addWidget(engine_panel)

        # Thermal Protection Settings Panel
        thermal_panel = QWidget()
        thermal_panel.setObjectName("panel")
        tp_layout = QVBoxLayout(thermal_panel)
        tp_layout.setContentsMargins(16, 16, 16, 16)
        tp_layout.setSpacing(10)

        tp_layout.addWidget(_section("THERMAL PROTECTION SETTINGS"))

        self._thermal_protection_check = QCheckBox("Enable Thermal Protection")
        self._thermal_protection_check.setChecked(getattr(self.state, "thermal_protection_enabled", True))
        self._thermal_protection_check.stateChanged.connect(self._on_thermal_protection_enabled_changed)
        tp_layout.addWidget(self._thermal_protection_check)

        threshold_row = QWidget()
        tr_lay = QHBoxLayout(threshold_row)
        tr_lay.setContentsMargins(0, 0, 0, 0)
        tr_lbl = QLabel("Protection Threshold (°C):")
        tr_lbl.setObjectName("lbl-muted")
        tr_lbl.setFixedWidth(180)
        tr_lay.addWidget(tr_lbl)
        self._thermal_threshold_spin = QSpinBox()
        self._thermal_threshold_spin.setRange(70, 105)
        self._thermal_threshold_spin.setValue(getattr(self.state, "thermal_protection_threshold", 95))
        self._thermal_threshold_spin.setFixedWidth(80)
        self._thermal_threshold_spin.valueChanged.connect(self._on_thermal_threshold_changed)
        tr_lay.addWidget(self._thermal_threshold_spin)
        tr_lay.addStretch()
        tp_layout.addWidget(threshold_row)

        layout.addWidget(thermal_panel)

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


    def _update_live_hardware(self):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            
            self._cpu_progress.setValue(int(cpu))
            self._cpu_progress.setFormat(f"%p% ({cpu:.1f}%)")
            
            self._ram_progress.setValue(int(mem.percent))
            used_gb = mem.used / 1_073_741_824
            total_gb = mem.total / 1_073_741_824
            self._ram_progress.setFormat(f"%p% ({used_gb:.1f} GB / {total_gb:.1f} GB)")
            
            # Disk space
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            self._disk_progress.setValue(int(100 - free_percent))
            free_gb = free / 1_073_741_824
            total_gb = total / 1_073_741_824
            self._disk_progress.setFormat(f"{free_gb:.1f} GB free ({free_percent:.1f}%)")
        except Exception as e:
            logger.warning(f"Error updating live hardware meters: {e}")


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
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>RAM</span>"
            f"<span style='font-size:11pt; color:#00C2FF; font-weight:bold;'>{ram} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB</span></span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>VRAM</span>"
            f"<span style='font-size:11pt; color:#2DD4A0; font-weight:bold;'>{vram_str}</span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>STORAGE</span>"
            f"<span style='font-size:11pt; color:#F0B030; font-weight:bold;'>{storage} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB free</span></span>"
            f"</div>"
            f"</div>"
        )
        self._hw_view.setHtml(html_content)


    def _on_engine_config_changed(self, *_args):
        enabled = bool(self._remote_engine_check.isChecked()) if hasattr(self, "_remote_engine_check") else False
        mode = "remote" if enabled else "local"
        url = self._remote_url_input.text().strip() if hasattr(self, "_remote_url_input") else "wss://localhost:8080"
        token = self._remote_token_input.text() if hasattr(self, "_remote_token_input") else ""
        self.state.engine_mode = mode
        self.state.remote_server_url = url
        self.state.remote_auth_token = token
        self.state.remote_engine_enabled = enabled
        self.state.remote_engine_url = url
        self.state.remote_engine_token = token
        from app.engine import config_store
        config_store.set_remote_engine_config(enabled, url, token)
        self._sync_engine_controls_enabled()


    def _sync_engine_controls_enabled(self):
        if not hasattr(self, "_remote_engine_check"):
            return
        remote = self._remote_engine_check.isChecked()
        self._remote_url_input.setEnabled(remote)
        self._remote_token_input.setEnabled(remote)
        if remote:
            self._remote_status_label.setText(
                "Remote mode forwards prompts and generation parameters over JSON-RPC. "
                "Private LAN WSS endpoints may use self-signed certificates."
            )
        else:
            self._remote_status_label.setText("Local mode loads GGUF models with llama-cpp-python on this machine.")
