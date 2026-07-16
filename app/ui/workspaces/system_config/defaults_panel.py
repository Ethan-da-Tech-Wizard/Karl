from __future__ import annotations

import logging
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QInputDialog, QMessageBox,
)

from .common import _hline, _row, _section
from core.default_prompts import DEFAULT_SYSTEM_PROMPT, load_prompt_presets, save_user_preset, delete_user_preset

logger = logging.getLogger("karl.system_config")

class DefaultsPanelMixin:
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

        # Settings Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        search_lbl = QLabel("Search Settings:")
        search_lbl.setObjectName("lbl-muted")
        search_lbl.setStyleSheet("font-size: 8.5pt;")
        self._settings_search_input = QLineEdit()
        self._settings_search_input.setPlaceholderText("type to filter settings...")
        self._settings_search_input.textChanged.connect(self._on_settings_search_changed)
        search_layout.addWidget(search_lbl)
        search_layout.addWidget(self._settings_search_input)
        pp_layout.addLayout(search_layout)
        pp_layout.addWidget(_hline())

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

        self._reduced_motion_check = QCheckBox("Disable active glowing animations")
        self._reduced_motion_check.setChecked(getattr(self.state, "reduced_motion", False))
        self._reduced_motion_check.stateChanged.connect(self._on_reduced_motion_changed)

        self._settings_rows = []
        
        row1 = _row("Temperature", self._temp_spin)
        self._settings_rows.append(("Temperature", row1))
        pp_layout.addWidget(row1)

        row2 = _row("Top-P", self._topp_spin)
        self._settings_rows.append(("Top-P", row2))
        pp_layout.addWidget(row2)

        row3 = _row("Max Tokens", self._maxtok_spin)
        self._settings_rows.append(("Max Tokens", row3))
        pp_layout.addWidget(row3)

        row4 = _row("Accessibility", self._reduced_motion_check)
        self._settings_rows.append(("Accessibility", row4))
        pp_layout.addWidget(row4)

        # Theme Mode settings row
        self._theme_mode_combo = QComboBox()
        self._theme_mode_combo.addItems(["midnight", "slate", "ember"])
        self._theme_mode_combo.setCurrentText(getattr(self.state, "theme_mode", "midnight"))
        self._theme_mode_combo.currentTextChanged.connect(self._on_theme_mode_changed)
        self._theme_mode_combo.setFixedWidth(120)

        row5 = _row("Theme", self._theme_mode_combo)
        self._settings_rows.append(("Theme", row5))
        pp_layout.addWidget(row5)

        self._log_rotation_spin = QSpinBox()
        self._log_rotation_spin.setRange(1, 500)
        self._log_rotation_spin.setSingleStep(5)
        self._log_rotation_spin.setValue(getattr(self.state, "log_rotation_size_mb", 10))
        self._log_rotation_spin.setFixedWidth(90)
        self._log_rotation_spin.valueChanged.connect(self._on_log_rotation_changed)

        row6 = _row("Log Size Limit (MB)", self._log_rotation_spin)
        self._settings_rows.append(("Log Size Limit (MB)", row6))
        pp_layout.addWidget(row6)

        self._log_retention_spin = QSpinBox()
        self._log_retention_spin.setRange(1, 365)
        self._log_retention_spin.setSingleStep(5)
        self._log_retention_spin.setValue(getattr(self.state, "log_retention_days", 30))
        self._log_retention_spin.setFixedWidth(90)
        self._log_retention_spin.valueChanged.connect(self._on_log_retention_changed)

        row7 = _row("Log Retention (Days)", self._log_retention_spin)
        self._settings_rows.append(("Log Retention (Days)", row7))
        pp_layout.addWidget(row7)

        pp_layout.addWidget(_hline())
        pp_layout.addWidget(_section("SECURITY"))

        self._single_session_auth_check = QCheckBox("Enforce Single-Session Authorization")
        self._single_session_auth_check.setChecked(getattr(self.state, "single_session_auth", False))
        self._single_session_auth_check.setToolTip(
            "Wipe cached bridge token from OS keychain immediately upon exiting the application."
        )
        self._single_session_auth_check.stateChanged.connect(self._on_single_session_auth_changed)

        row8 = _row("Session Security", self._single_session_auth_check)
        self._settings_rows.append(("Session Security", row8))
        pp_layout.addWidget(row8)

        apply_btn = QPushButton("apply defaults")
        apply_btn.setObjectName("btn-primary")
        apply_btn.setToolTip("Save and apply default generation limits")
        apply_btn.clicked.connect(self._apply_defaults)
        pp_layout.addWidget(apply_btn)

        layout.addWidget(params_panel)
        layout.addStretch()
        return w


    def _on_reduced_motion_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked.value or state)
        self.state.reduced_motion = is_checked
        if hasattr(self, "_reduced_motion_check_app"):
            self._reduced_motion_check_app.blockSignals(True)
            self._reduced_motion_check_app.setChecked(is_checked)
            self._reduced_motion_check_app.blockSignals(False)
        self._apply_active_theme()
        self._save_appearance_config_silent()


    def _on_theme_mode_changed(self, text: str):
        self.state.theme_mode = text
        from app.ui import themes
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(themes.get_theme_stylesheet(self.state))
        self._save_appearance_config_silent()


    def _on_log_rotation_changed(self, val):
        self.state.log_rotation_size_mb = val
        self._save_appearance_config_silent()


    def _on_log_retention_changed(self, val):
        self.state.log_retention_days = val
        self._save_appearance_config_silent()


    def _on_single_session_auth_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked.value or state is True)
        self.state.single_session_auth = is_checked
        self._save_appearance_config_silent()


    def _on_thermal_protection_enabled_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked.value or state is True)
        self.state.thermal_protection_enabled = is_checked
        self._save_appearance_config_silent()


    def _on_thermal_threshold_changed(self, val: int):
        self.state.thermal_protection_threshold = val
        self._save_appearance_config_silent()

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

        # ── Presets row ────────────────────────────────────────────────────────
        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)

        presets_lbl = QLabel("Preset:")
        presets_lbl.setObjectName("lbl-muted")
        presets_lbl.setStyleSheet("font-size: 8.5pt;")
        presets_lbl.setFixedWidth(44)
        presets_row.addWidget(presets_lbl)

        self._preset_combo = QComboBox()
        self._preset_combo.setToolTip("Load a named system prompt into the editor below")
        self._preset_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._preset_combo.setMinimumWidth(160)
        self._reload_preset_combo()
        presets_row.addWidget(self._preset_combo, 1)

        load_preset_btn = QPushButton("load")
        load_preset_btn.setObjectName("btn-ghost")
        load_preset_btn.setFixedWidth(52)
        load_preset_btn.setToolTip("Load selected preset into the editor (does not apply immediately)")
        load_preset_btn.clicked.connect(self._on_load_preset)
        presets_row.addWidget(load_preset_btn)

        save_preset_btn = QPushButton("save as…")
        save_preset_btn.setObjectName("btn-ghost")
        save_preset_btn.setFixedWidth(72)
        save_preset_btn.setToolTip("Save the current editor text as a new named preset")
        save_preset_btn.clicked.connect(self._on_save_preset)
        presets_row.addWidget(save_preset_btn)

        self._delete_preset_btn = QPushButton("delete")
        self._delete_preset_btn.setObjectName("btn-danger")
        self._delete_preset_btn.setFixedWidth(56)
        self._delete_preset_btn.setToolTip("Delete the selected user-defined preset (built-ins are protected)")
        self._delete_preset_btn.clicked.connect(self._on_delete_preset)
        presets_row.addWidget(self._delete_preset_btn)

        ip_layout.addLayout(presets_row)

        # Preset description label
        self._preset_desc_lbl = QLabel("")
        self._preset_desc_lbl.setObjectName("lbl-muted")
        self._preset_desc_lbl.setWordWrap(True)
        self._preset_desc_lbl.setStyleSheet("font-size: 8pt; font-style: italic;")
        ip_layout.addWidget(self._preset_desc_lbl)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        # Trigger once to populate description for the initial selection
        self._on_preset_combo_changed(self._preset_combo.currentIndex())

        ip_layout.addWidget(_hline())

        from PyQt6.QtWidgets import QTextEdit
        self._system_edit = QTextEdit()
        self._system_edit.setToolTip(
            "System prompt active during generation. Determines Karl's personality and guidelines."
        )
        # Load currently-active prompt (persisted or default)
        from app.engine import config_store as _cs
        stored = _cs.get_ui_config().get("workbench_system_prompt", "")
        self._system_edit.setPlainText(stored if stored.strip() else DEFAULT_SYSTEM_PROMPT)
        ip_layout.addWidget(self._system_edit, 1)

        apply_btn = QPushButton("apply system prompt")
        apply_btn.setObjectName("btn-primary")
        apply_btn.setToolTip("Apply this system prompt to all future generations in this session")
        apply_btn.clicked.connect(self._apply_identity)
        ip_layout.addWidget(apply_btn)

        layout.addWidget(identity_panel, 1)
        return w

    # ── vision tab ────────────────────────────────────────────────────────────

    def _reload_preset_combo(self) -> None:
        """Rebuild the Presets combo box from the current merged preset dict."""
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._presets_data: dict = load_prompt_presets()
        built_in_keys = [k for k in self._presets_data if k.startswith("_")]
        user_keys = [k for k in self._presets_data if not k.startswith("_")]

        for key in built_in_keys:
            label = self._presets_data[key].get("label", key)
            self._preset_combo.addItem(label, userData=key)

        if user_keys:
            self._preset_combo.insertSeparator(len(built_in_keys))
            for key in user_keys:
                label = self._presets_data[key].get("label", key)
                self._preset_combo.addItem(f"★ {label}", userData=key)

        self._preset_combo.blockSignals(False)
        self._update_delete_btn_state()

    def _on_preset_combo_changed(self, index: int) -> None:
        """Update the description label when the combo selection changes."""
        if not hasattr(self, "_presets_data"):
            return
        key = self._preset_combo.itemData(index)
        if key and key in self._presets_data:
            desc = self._presets_data[key].get("description", "")
            self._preset_desc_lbl.setText(desc)
        else:
            self._preset_desc_lbl.setText("")
        self._update_delete_btn_state()

    def _update_delete_btn_state(self) -> None:
        """Enable Delete only for user-defined presets (non-underscore keys)."""
        if not hasattr(self, "_delete_preset_btn"):
            return
        idx = self._preset_combo.currentIndex()
        key = self._preset_combo.itemData(idx) if idx >= 0 else None
        is_user = isinstance(key, str) and not key.startswith("_")
        self._delete_preset_btn.setEnabled(is_user)

    def _on_load_preset(self) -> None:
        """Load the selected preset text into the editor."""
        idx = self._preset_combo.currentIndex()
        key = self._preset_combo.itemData(idx)
        if not key or not hasattr(self, "_presets_data"):
            return
        entry = self._presets_data.get(key, {})
        prompt = entry.get("prompt", "")
        if prompt and hasattr(self, "_system_edit"):
            self._system_edit.setPlainText(prompt)

    def _on_save_preset(self) -> None:
        """Save the current editor text as a new user preset."""
        if not hasattr(self, "_system_edit"):
            return
        text = self._system_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Prompt", "Cannot save an empty system prompt as a preset.")
            return
        label, ok = QInputDialog.getText(
            self, "Save Preset", "Preset name:",
        )
        if not ok or not label.strip():
            return
        label = label.strip()
        # Generate a safe key from the label
        key = re.sub(r"[^a-z0-9_]", "_", label.lower()).strip("_") or "custom_preset"
        # Avoid collision with built-in keys
        if key.startswith("_"):
            key = key.lstrip("_")
        desc, ok2 = QInputDialog.getText(
            self, "Save Preset", "Short description (optional):",
        )
        if not ok2:
            desc = ""
        if save_user_preset(key, label, desc.strip(), text):
            self._reload_preset_combo()
            # Select the newly saved preset
            for i in range(self._preset_combo.count()):
                if self._preset_combo.itemData(i) == key:
                    self._preset_combo.setCurrentIndex(i)
                    break
        else:
            QMessageBox.critical(self, "Save Failed", f"Could not save preset '{label}'. Check logs.")

    def _on_delete_preset(self) -> None:
        """Delete the selected user preset after confirmation."""
        idx = self._preset_combo.currentIndex()
        key = self._preset_combo.itemData(idx)
        if not key or key.startswith("_"):
            return
        entry = self._presets_data.get(key, {})
        label = entry.get("label", key)
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{label}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if delete_user_preset(key):
            self._reload_preset_combo()
        else:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete preset '{label}'. Check logs.")

    def _apply_identity(self):
        self.state.set_workbench_system_prompt.emit(
            self._system_edit.toPlainText().strip()
        )


    def _on_settings_search_changed(self, text: str):
        query = text.strip().lower()
        for label, row_widget in self._settings_rows:
            if not query or query in label.lower():
                row_widget.setVisible(True)
            else:
                row_widget.setVisible(False)


