from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
)

from app.engine import config_store
from app.ui.themes import THEMES, get_theme_colors

logger = logging.getLogger("karl.system_config")

class AppearanceRuntimeMixin:
    def _on_control_changed(self):
        # Update sliders numeric indicators
        gs = self._glow_strength_slider.value() / 10.0
        ai = self._animation_intensity_slider.value() / 10.0
        self._glow_strength_val_lbl.setText(f"{gs:.1f}x")
        self._animation_intensity_val_lbl.setText(f"{ai:.1f}x")

        # Also sync reduced motion check in defaults tab
        self._reduced_motion_check.blockSignals(True)
        self._reduced_motion_check.setChecked(self._reduced_motion_check_app.isChecked())
        self._reduced_motion_check.blockSignals(False)

        # Debounce: slider drags fire valueChanged per tick; recompiling and
        # re-applying the app stylesheet on every tick stutters the drag.
        # Labels above update live, the theme applies once the drag settles.
        if not hasattr(self, "_theme_apply_timer"):
            from PyQt6.QtCore import QTimer
            self._theme_apply_timer = QTimer(self)
            self._theme_apply_timer.setSingleShot(True)
            self._theme_apply_timer.setInterval(120)
            self._theme_apply_timer.timeout.connect(self._apply_active_theme)
        self._theme_apply_timer.start()



    def _apply_active_theme(self):
        # Read from controls
        theme_preset = self._theme_preset_combo.currentText()
        layout_preset = self._layout_preset_combo.currentText()
        glow_enabled = self._glow_enabled_check.isChecked()
        reduced_motion = self._reduced_motion_check_app.isChecked()
        glow_strength = self._glow_strength_slider.value() / 10.0
        animation_intensity = self._animation_intensity_slider.value() / 10.0
        custom_accent = self._active_custom_accent

        # Write to state
        self.state.theme_preset = theme_preset
        self.state.layout_preset = layout_preset
        self.state.glow_enabled = glow_enabled
        self.state.reduced_motion = reduced_motion
        self.state.glow_strength = glow_strength
        self.state.animation_intensity = animation_intensity
        self.state.custom_accent = custom_accent

        # Trigger QApplication stylesheet compilation & reload
        self.appearance_changed.emit()

        # Update preview card elements
        self._preview_card.update_style()
        self._check_icon_preview.update()
        self._cross_icon_preview.update()
        self._update_swatches()



    def _update_swatches(self):
        # Clear existing swatches
        while self._swatches_layout.count():
            item = self._swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Generate colors for current state
        colors = get_theme_colors(self.state)
        swatch_keys = [
            ("accent", "ACCENT"),
            ("accent_dark", "ALT"),
            ("bg_surface", "SURFACE"),
            ("bg_deep", "DEEP"),
            ("text_hi", "TEXT")
        ]
        
        for key, label in swatch_keys:
            hex_val = colors.get(key, "#000000")
            
            swatch_unit = QWidget()
            su_layout = QVBoxLayout(swatch_unit)
            su_layout.setContentsMargins(0, 0, 0, 0)
            su_layout.setSpacing(2)
            
            color_box = QLabel()
            color_box.setFixedSize(36, 24)
            color_box.setStyleSheet(
                f"background-color: {hex_val}; border: 1px solid {colors.get('border', '#35356E')}; border-radius: 3px;"
            )
            color_box.setToolTip(f"{label}: {hex_val}")
            
            lbl_text = QLabel(label)
            lbl_text.setStyleSheet("font-size: 7.5pt; font-weight: bold; text-align: center;")
            lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_text.setObjectName("lbl-muted")
            
            su_layout.addWidget(color_box, alignment=Qt.AlignmentFlag.AlignCenter)
            su_layout.addWidget(lbl_text, alignment=Qt.AlignmentFlag.AlignCenter)
            
            self._swatches_layout.addWidget(swatch_unit)



    def _update_theme_gallery(self):
        if not hasattr(self, "_theme_gallery_layout"):
            return
        # The 20 cards only differ by which one carries the ACTIVE marker;
        # skip the full rebuild when the selection hasn't changed.
        selected_now = self._theme_preset_combo.currentText()
        if (getattr(self, "_gallery_built_for", None) == selected_now
                and self._theme_gallery_layout.count() > 0):
            return
        self._gallery_built_for = selected_now
        while self._theme_gallery_layout.count():
            item = self._theme_gallery_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected = self._theme_preset_combo.currentText()
        for name, data in THEMES.items():
            border = data.get("border_hi", "#35356E")
            accent = data.get("accent", "#00E5FF")
            accent_alt = data.get("accent_alt", "#0099AA")
            bg_deep = data.get("bg_deep", "#020205")
            bg_surface = data.get("bg_surface", "#0D0D1B")
            bg_raised = data.get("bg_raised", "#14142D")
            text_hi = data.get("text_hi", "#F0F5FF")
            text_mid = data.get("text_mid", "#A0AEC0")

            card = QWidget()
            card.setObjectName("panel")
            card.setStyleSheet(
                f"QWidget#panel {{ background-color: {bg_surface}; border: 1px solid {border}; border-radius: 6px; }}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(6)

            header = QWidget()
            hl = QHBoxLayout(header)
            hl.setContentsMargins(0, 0, 0, 0)
            title = QLabel(name + ("  ACTIVE" if name == selected else ""))
            title.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 9.5pt;")
            hl.addWidget(title, 1)
            apply_btn = QPushButton("Apply")
            apply_btn.setObjectName("btn-primary" if name == selected else "btn-secondary")
            apply_btn.clicked.connect(lambda _checked=False, n=name: self._apply_theme_preset_from_gallery(n))
            hl.addWidget(apply_btn)
            cl.addWidget(header)

            desc = QLabel(data.get("description", ""))
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {text_mid}; font-size: 8.2pt;")
            cl.addWidget(desc)

            swatch_row = QWidget()
            sl = QHBoxLayout(swatch_row)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setSpacing(5)
            for value, label in (
                (accent, "accent"),
                (accent_alt, "alt"),
                (bg_deep, "deep"),
                (bg_surface, "surface"),
                (bg_raised, "raised"),
                (text_hi, "text"),
            ):
                box = QLabel()
                box.setFixedSize(34, 16)
                box.setToolTip(f"{label}: {value}")
                box.setStyleSheet(f"background-color: {value}; border: 1px solid {border}; border-radius: 3px;")
                sl.addWidget(box)
            sl.addStretch()
            cl.addWidget(swatch_row)
            self._theme_gallery_layout.addWidget(card)

        self._theme_gallery_layout.addStretch(1)



    def _apply_theme_preset_from_gallery(self, name: str):
        idx = self._theme_preset_combo.findText(name)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)



    def _save_appearance_config_silent(self):
        config_store.save_ui_config({
            "theme_preset": self.state.theme_preset,
            "custom_accent": self.state.custom_accent,
            "layout_preset": self.state.layout_preset,
            "reduced_motion": self.state.reduced_motion,
            "glow_enabled": self.state.glow_enabled,
            "animation_intensity": self.state.animation_intensity,
            "glow_strength": self.state.glow_strength,
            "theme_mode": getattr(self.state, "theme_mode", "midnight"),
            "log_rotation_size_mb": getattr(self.state, "log_rotation_size_mb", 10),
            "log_retention_days": getattr(self.state, "log_retention_days", 30),
            "single_session_auth": getattr(self.state, "single_session_auth", False),
            "thermal_protection_enabled": getattr(self.state, "thermal_protection_enabled", True),
            "thermal_protection_threshold": getattr(self.state, "thermal_protection_threshold", 95),
            "engine_mode": getattr(self.state, "engine_mode", "local"),
            "remote_server_url": getattr(self.state, "remote_server_url", ""),
            "remote_auth_token": getattr(self.state, "remote_auth_token", ""),
            "remote_engine_enabled": getattr(self.state, "remote_engine_enabled", False),
            "remote_engine_url": getattr(self.state, "remote_engine_url", "wss://localhost:8080"),
            "remote_engine_token": getattr(self.state, "remote_engine_token", ""),
        })



    def _save_appearance_config(self):
        self._save_appearance_config_silent()
        
        # Delete old config if exists to clean up
        old_path = "data/theme_config.json"
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
                
        QMessageBox.information(
            self, "Settings Saved",
            "Appearance configuration saved successfully to data/ui_config.json."
        )
