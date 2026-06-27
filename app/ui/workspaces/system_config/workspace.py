"""
System — hardware info, model management, generation defaults, about.
"""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QTabWidget

from app.engine.quantizer_thread import QuantizerThread

from .appearance_panel import AppearancePanelMixin
from .appearance_runtime import AppearanceRuntimeMixin
from .defaults_panel import DefaultsPanelMixin
from .mcp_panel import McpPanelMixin
from .model_panel import ModelPanelMixin
from .model_preflight import ModelPreflightMixin
from .quantization_panel import QuantizationPanelMixin
from .registry_panel import RegistryPanelMixin
from .vision_hardware_panel import VisionHardwarePanelMixin


logger = logging.getLogger("karl.system_config")


class SystemConfigWorkspace(
    RegistryPanelMixin,
    QuantizationPanelMixin,
    ModelPanelMixin,
    ModelPreflightMixin,
    DefaultsPanelMixin,
    VisionHardwarePanelMixin,
    AppearancePanelMixin,
    AppearanceRuntimeMixin,
    McpPanelMixin,
    QWidget,
):
    """Tabbed system workspace for model, registry, theme, telemetry, and hardware controls."""

    adapter_changed = pyqtSignal(str)
    appearance_changed = pyqtSignal()

    def __init__(self, state, workbench_ref=None, parent=None):
        """Create system config tabs and start live hardware monitoring."""
        super().__init__(parent)
        self.state = state
        self._workbench = workbench_ref
        self._download_thread = None
        self._quantizer_thread: QuantizerThread | None = None
        self._active_threads = set()
        self._active_custom_accent = None
        self._cached_models_list = None
        self._cached_adapters_list = None
        self._load_registry()
        self.setObjectName("workspace-root")
        self._build_ui()
        self._refresh_hardware()
        
        # Start diagnostic hardware monitoring timer
        self._hardware_timer = QTimer(self)
        self._hardware_timer.timeout.connect(self._update_live_hardware)
        self._hardware_timer.start(2000)
        self._update_live_hardware()

    def set_workbench(self, wb):
        self._workbench = wb

    def showEvent(self, event):
        super().showEvent(event)
        self._scan_models(force=False)
        self._scan_adapters(force=False)

        from app.engine import config_store as _cs
        draft_cfg = _cs.get_active_draft_model()
        if hasattr(self, "_speculative_toggle"):
            self._speculative_toggle.setChecked(bool(draft_cfg.get("enabled")))
        if draft_cfg["filename"]:
            draft_path = os.path.join("data", "models", draft_cfg["filename"])
            self._draft_model_input.setText(draft_path)
            if hasattr(self, "_draft_model_combo"):
                idx = self._draft_model_combo.findText(draft_cfg["filename"])
                if idx >= 0:
                    self._draft_model_combo.setCurrentIndex(idx)
            from app.engine.model_loader import ModelLoader
            if ModelLoader.is_speculative():
                self._draft_status.setText(
                    f"<span style='color:#2DD4A0;'>Speculative decoding active — draft: "
                    f"{draft_cfg['filename']}</span>"
                )
                self._draft_status.setTextFormat(Qt.TextFormat.RichText)

        self._refresh_hardware()
        self._run_model_preflight_checks()

    def _build_ui(self):
        """Build the System title and tab set from mixin-provided panels."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("System")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        root.addWidget(title)

        desc = QLabel(
            "Configure model and environment settings. Load or download GGUF models, "
            "manage default generation hyperparameters, active identity prompts, and check hardware resource specs."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px; padding-left: 2px;")
        root.addWidget(desc)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_model_tab(), "Model")
        self._tabs.addTab(self._build_registry_tab(), "Registry")
        self._tabs.addTab(self._build_params_tab(), "Defaults")
        self._tabs.addTab(self._build_identity_tab(), "Identity")
        self._tabs.addTab(self._build_vision_tab(), "Vision")
        self._tabs.addTab(self._build_mcp_tab(), "MCP")
        self._theme_tab = self._build_theme_tab()
        self._tabs.addTab(self._theme_tab, "Theme")
        
        # Inject Observability panel
        from .observability_tab import ObservabilityTab
        self._observability_tab = ObservabilityTab(self.state, self)
        self._tabs.addTab(self._observability_tab, "Observability")

        self._tabs.addTab(self._build_hardware_tab(), "Hardware")
        root.addWidget(self._tabs, 1)

    def show_theme_tab(self):
        if hasattr(self, "_tabs") and hasattr(self, "_theme_tab"):
            self._sync_appearance_controls_from_state()
            self._tabs.setCurrentWidget(self._theme_tab)

    # ── model tab ─────────────────────────────────────────────────────────────

    def _apply_defaults(self):
        from PyQt6.QtWidgets import QMessageBox
        temp = self._temp_spin.value()
        top_p = self._topp_spin.value()
        max_tokens = self._maxtok_spin.value()
        
        if self._workbench:
            self._workbench.set_hyperparams({
                "temperature": temp,
                "top_p": top_p,
                "max_tokens": max_tokens
            })
            QMessageBox.information(
                self, "Defaults Applied",
                f"Generation defaults applied to Workbench:\n"
                f"• Temperature: {temp}\n"
                f"• Top-P: {top_p}\n"
                f"• Max Tokens: {max_tokens}"
            )

    # ── theme tab ─────────────────────────────────────────────────────────────
