from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QScrollArea, QComboBox, QColorDialog, QCheckBox, QSlider,
)

from app.engine import config_store
from app.ui.themes import THEMES, get_theme_colors
from app.ui.widgets.symbolic_icon import CheckIcon, CrossIcon
from app.ui.widgets.tracing_panel import TracingPanel
from .common import _hline, _row, _section

logger = logging.getLogger("karl.system_config")

class AppearancePanelMixin:
    def _build_theme_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Left Column: Controls (scrollable in case of small screen)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        ctrl_panel = QWidget()
        ctrl_panel.setObjectName("panel")
        ctrl_layout = QVBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        ctrl_layout.addWidget(_section("VISUAL THEME PRESETS"))

        # Presets Combobox
        self._theme_preset_combo = QComboBox()
        for name in THEMES.keys():
            self._theme_preset_combo.addItem(name)
        self._theme_preset_combo.currentTextChanged.connect(self._on_preset_changed)
        ctrl_layout.addWidget(_row("Preset Palette", self._theme_preset_combo))

        # Preset Description
        self._preset_desc_lbl = QLabel("")
        self._preset_desc_lbl.setObjectName("lbl-muted")
        self._preset_desc_lbl.setWordWrap(True)
        self._preset_desc_lbl.setStyleSheet("font-size: 8.5pt; margin-left: 130px; margin-bottom: 6px;")
        ctrl_layout.addWidget(self._preset_desc_lbl)

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("CUSTOM ACCENT OVERRIDE"))

        # Custom Accent Picker Row
        self._custom_accent_btn = QPushButton("Pick Custom Accent...")
        self._custom_accent_btn.clicked.connect(self._pick_custom_accent)
        
        self._clear_accent_btn = QPushButton("Reset Accent")
        self._clear_accent_btn.clicked.connect(self._reset_custom_accent)
        
        self._accent_color_preview = QLabel()
        self._accent_color_preview.setFixedSize(24, 24)
        self._accent_color_preview.setStyleSheet("border: 1px solid #35356E; border-radius: 4px;")

        accent_layout = QHBoxLayout()
        accent_layout.setSpacing(8)
        accent_layout.addWidget(self._custom_accent_btn, 1)
        accent_layout.addWidget(self._clear_accent_btn)
        accent_layout.addWidget(self._accent_color_preview)
        
        accent_widget = QWidget()
        accent_widget_layout = QHBoxLayout(accent_widget)
        accent_widget_layout.setContentsMargins(0, 0, 0, 0)
        accent_widget_layout.addLayout(accent_layout)
        ctrl_layout.addWidget(_row("Custom Accent", accent_widget))

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("THEME GALLERY"))

        self._theme_gallery = QScrollArea()
        self._theme_gallery.setWidgetResizable(True)
        self._theme_gallery.setFrameShape(QFrame.Shape.NoFrame)
        self._theme_gallery.setMinimumHeight(320)
        self._theme_gallery_content = QWidget()
        self._theme_gallery_layout = QVBoxLayout(self._theme_gallery_content)
        self._theme_gallery_layout.setContentsMargins(0, 0, 0, 0)
        self._theme_gallery_layout.setSpacing(8)
        self._theme_gallery.setWidget(self._theme_gallery_content)
        ctrl_layout.addWidget(self._theme_gallery)

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("LAYOUT DENSITY PRESETS"))

        # Layout density selector
        self._layout_preset_combo = QComboBox()
        self._layout_preset_combo.addItems([
            "Focused Workbench",
            "Research Lab",
            "Training Console",
            "Evaluation Wall",
            "Compact Laptop",
            "Wide Monitor Command",
            "Minimal Distraction",
            "Max Introspection",
            "Knowledge Heavy",
            "Prompt Engineering Lab"
        ])
        self._layout_preset_combo.currentTextChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Layout Density", self._layout_preset_combo))

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("EFFECTS & MOTION SYSTEM"))

        # Glow enabled checkbox
        self._glow_enabled_check = QCheckBox("Enable Glow Effects")
        self._glow_enabled_check.stateChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Edge Glow", self._glow_enabled_check))

        # Glow Strength Slider
        self._glow_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self._glow_strength_slider.setRange(0, 20)
        self._glow_strength_slider.setSingleStep(1)
        self._glow_strength_slider.setPageStep(2)
        self._glow_strength_slider.setValue(10)
        self._glow_strength_slider.valueChanged.connect(self._on_control_changed)
        
        self._glow_strength_val_lbl = QLabel("1.0x")
        self._glow_strength_val_lbl.setFixedWidth(40)
        self._glow_strength_val_lbl.setObjectName("lbl-muted")
        
        glow_row_widget = QWidget()
        gr_layout = QHBoxLayout(glow_row_widget)
        gr_layout.setContentsMargins(0, 0, 0, 0)
        gr_layout.setSpacing(8)
        gr_layout.addWidget(self._glow_strength_slider, 1)
        gr_layout.addWidget(self._glow_strength_val_lbl)
        ctrl_layout.addWidget(_row("Glow Strength", glow_row_widget))

        # Animation Intensity (Speed) Slider
        self._animation_intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self._animation_intensity_slider.setRange(0, 20)
        self._animation_intensity_slider.setSingleStep(1)
        self._animation_intensity_slider.setPageStep(2)
        self._animation_intensity_slider.setValue(10)
        self._animation_intensity_slider.valueChanged.connect(self._on_control_changed)
        
        self._animation_intensity_val_lbl = QLabel("1.0x")
        self._animation_intensity_val_lbl.setFixedWidth(40)
        self._animation_intensity_val_lbl.setObjectName("lbl-muted")
        
        anim_row_widget = QWidget()
        ar_layout = QHBoxLayout(anim_row_widget)
        ar_layout.setContentsMargins(0, 0, 0, 0)
        ar_layout.setSpacing(8)
        ar_layout.addWidget(self._animation_intensity_slider, 1)
        ar_layout.addWidget(self._animation_intensity_val_lbl)
        ctrl_layout.addWidget(_row("Motion Speed", anim_row_widget))

        # Reduced motion checkbox (Disable active glowing animations)
        self._reduced_motion_check_app = QCheckBox("Disable active glowing animations (Reduced Motion)")
        self._reduced_motion_check_app.stateChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Accessibility", self._reduced_motion_check_app))

        # Save & Apply Button
        apply_btn = QPushButton("Save Appearance Config")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._save_appearance_config)
        ctrl_layout.addWidget(apply_btn)

        scroll_layout.addWidget(ctrl_panel)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 3)

        # Right Column: Live Preview Card + Swatches
        preview_col = QWidget()
        pr_layout = QVBoxLayout(preview_col)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        pr_layout.setSpacing(12)

        # Swatches Panel
        swatches_panel = QWidget()
        swatches_panel.setObjectName("panel")
        sp_layout = QVBoxLayout(swatches_panel)
        sp_layout.setContentsMargins(12, 12, 12, 12)
        sp_layout.setSpacing(8)
        sp_layout.addWidget(_section("ACTIVE PALETTE OVERVIEW"))
        
        self._swatches_container = QWidget()
        self._swatches_layout = QHBoxLayout(self._swatches_container)
        self._swatches_layout.setContentsMargins(0, 4, 0, 4)
        self._swatches_layout.setSpacing(6)
        sp_layout.addWidget(self._swatches_container)
        pr_layout.addWidget(swatches_panel)

        # Live Preview Panel using TracingPanel
        self._preview_card = TracingPanel(self.state)
        self._preview_card.set_active(True)
        self._preview_card.setMinimumHeight(280)
        
        card_layout = QVBoxLayout(self._preview_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        
        self._add_preview_elements(card_layout)
        pr_layout.addWidget(self._preview_card, 1)

        layout.addWidget(preview_col, 2)

        # Load active configuration if file exists
        self._load_active_appearance_config()
        
        return w


    def _add_preview_elements(self, card_layout: QVBoxLayout):
        title = QLabel("LIVE PREVIEW")
        title.setObjectName("section-header")
        card_layout.addWidget(title)
        
        desc = QLabel("Realtime mockup card showing active styles.")
        desc.setObjectName("lbl-muted")
        desc.setStyleSheet("font-size: 8pt; margin-bottom: 2px;")
        card_layout.addWidget(desc)
        
        # Primary & Secondary Buttons mockup
        btn_row = QWidget()
        br_layout = QHBoxLayout(btn_row)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(8)
        
        btn_prim = QPushButton("Primary Button")
        btn_prim.setObjectName("btn-primary")
        btn_prim.setFixedHeight(26)
        btn_prim.setStyleSheet("font-size: 8.5pt; padding: 2px 10px;")
        
        btn_sec = QPushButton("Secondary Button")
        btn_sec.setObjectName("btn-secondary")
        btn_sec.setFixedHeight(26)
        btn_sec.setStyleSheet("font-size: 8.5pt; padding: 2px 10px;")
        
        br_layout.addWidget(btn_prim)
        br_layout.addWidget(btn_sec)
        card_layout.addWidget(btn_row)
        
        # Success & Error badges using custom painted icons
        badge_row = QWidget()
        bg_layout = QHBoxLayout(badge_row)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(16)
        
        # Success badge
        succ_widget = QWidget()
        sw_layout = QHBoxLayout(succ_widget)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(4)
        self._check_icon_preview = CheckIcon(self.state, color_role="green", size=14)
        lbl_succ = QLabel("Success Badge")
        lbl_succ.setStyleSheet("color: #00FFAA; font-size: 8.5pt;")
        sw_layout.addWidget(self._check_icon_preview)
        sw_layout.addWidget(lbl_succ)
        
        # Error badge
        err_widget = QWidget()
        ew_layout = QHBoxLayout(err_widget)
        ew_layout.setContentsMargins(0, 0, 0, 0)
        ew_layout.setSpacing(4)
        self._cross_icon_preview = CrossIcon(self.state, color_role="red", size=14)
        lbl_err = QLabel("Error Badge")
        lbl_err.setStyleSheet("color: #FF3366; font-size: 8.5pt;")
        ew_layout.addWidget(self._cross_icon_preview)
        ew_layout.addWidget(lbl_err)
        
        bg_layout.addWidget(succ_widget)
        bg_layout.addWidget(err_widget)
        card_layout.addWidget(badge_row)
        
        # Chat bubbles mockup
        chat_mockup = QWidget()
        cm_layout = QVBoxLayout(chat_mockup)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.setSpacing(6)
        
        # User bubble
        user_bubble = QLabel("How does local introspection work?")
        user_bubble.setStyleSheet(
            "background: rgba(31, 31, 61, 0.3); border: 1px solid rgba(53, 53, 110, 0.4); "
            "border-radius: 4px; padding: 6px; font-size: 8.5pt; color: #F0F5FF;"
        )
        cm_layout.addWidget(user_bubble)
        
        # Assistant bubble
        assistant_bubble = QLabel(
            "Analyzing trace stream...<br/>"
            "<span style='color: #A0AEC0; font-family: monospace; font-size: 8pt;'>"
            "&lt;think&gt;<br/>Reasoning tier 1: verifying model budget context... ok.<br/>&lt;/think&gt;</span><br/>"
            "Introspection processes generation traces in real-time."
        )
        assistant_bubble.setTextFormat(Qt.TextFormat.RichText)
        assistant_bubble.setStyleSheet(
            "background: rgba(13, 13, 27, 0.5); border: 1px solid rgba(31, 31, 61, 0.5); "
            "border-radius: 4px; padding: 6px; font-size: 8.5pt;"
        )
        cm_layout.addWidget(assistant_bubble)
        card_layout.addWidget(chat_mockup)
        
        card_layout.addStretch()


    def _load_active_appearance_config(self):
        config = config_store.get_ui_config()
        theme_preset = config["theme_preset"]
        custom_accent = config["custom_accent"]
        layout_preset = config["layout_preset"]
        reduced_motion = config["reduced_motion"]
        glow_enabled = config["glow_enabled"]
        animation_intensity = config["animation_intensity"]
        glow_strength = config["glow_strength"]
        theme_mode = config.get("theme_mode", "midnight")

        self.state.theme_mode = theme_mode
        if hasattr(self, "_theme_mode_combo"):
            self._theme_mode_combo.blockSignals(True)
            self._theme_mode_combo.setCurrentText(theme_mode)
            self._theme_mode_combo.blockSignals(False)

        self._theme_preset_combo.blockSignals(True)
        idx = self._theme_preset_combo.findText(theme_preset)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)
        self._theme_preset_combo.blockSignals(False)

        self._layout_preset_combo.blockSignals(True)
        idx = self._layout_preset_combo.findText(layout_preset)
        if idx >= 0:
            self._layout_preset_combo.setCurrentIndex(idx)
        self._layout_preset_combo.blockSignals(False)

        self._glow_enabled_check.blockSignals(True)
        self._glow_enabled_check.setChecked(glow_enabled)
        self._glow_enabled_check.blockSignals(False)

        self._reduced_motion_check_app.blockSignals(True)
        self._reduced_motion_check_app.setChecked(reduced_motion)
        self._reduced_motion_check_app.blockSignals(False)

        self._glow_strength_slider.blockSignals(True)
        self._glow_strength_slider.setValue(int(glow_strength * 10))
        self._glow_strength_slider.blockSignals(False)
        self._glow_strength_val_lbl.setText(f"{glow_strength:.1f}x")

        self._animation_intensity_slider.blockSignals(True)
        self._animation_intensity_slider.setValue(int(animation_intensity * 10))
        self._animation_intensity_slider.blockSignals(False)
        self._animation_intensity_val_lbl.setText(f"{animation_intensity:.1f}x")

        self._active_custom_accent = custom_accent
        
        # Initial updates
        self._update_accent_button_text()
        self._on_preset_changed()


    def _sync_appearance_controls_from_state(self):
        theme_preset = getattr(self.state, "theme_preset", "Karl Obsidian Core")
        layout_preset = getattr(self.state, "layout_preset", "Focused Workbench")
        custom_accent = getattr(self.state, "custom_accent", None)
        reduced_motion = getattr(self.state, "reduced_motion", False)
        glow_enabled = getattr(self.state, "glow_enabled", True)
        animation_intensity = float(getattr(self.state, "animation_intensity", 1.0))
        glow_strength = float(getattr(self.state, "glow_strength", 1.0))
        theme_mode = getattr(self.state, "theme_mode", "midnight")

        if hasattr(self, "_theme_mode_combo"):
            self._theme_mode_combo.blockSignals(True)
            self._theme_mode_combo.setCurrentText(theme_mode)
            self._theme_mode_combo.blockSignals(False)

        self._theme_preset_combo.blockSignals(True)
        idx = self._theme_preset_combo.findText(theme_preset)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)
        self._theme_preset_combo.blockSignals(False)

        self._layout_preset_combo.blockSignals(True)
        idx = self._layout_preset_combo.findText(layout_preset)
        if idx >= 0:
            self._layout_preset_combo.setCurrentIndex(idx)
        self._layout_preset_combo.blockSignals(False)

        self._glow_enabled_check.blockSignals(True)
        self._glow_enabled_check.setChecked(glow_enabled)
        self._glow_enabled_check.blockSignals(False)

        self._reduced_motion_check_app.blockSignals(True)
        self._reduced_motion_check_app.setChecked(reduced_motion)
        self._reduced_motion_check_app.blockSignals(False)

        self._glow_strength_slider.blockSignals(True)
        self._glow_strength_slider.setValue(int(glow_strength * 10))
        self._glow_strength_slider.blockSignals(False)
        self._glow_strength_val_lbl.setText(f"{glow_strength:.1f}x")

        self._animation_intensity_slider.blockSignals(True)
        self._animation_intensity_slider.setValue(int(animation_intensity * 10))
        self._animation_intensity_slider.blockSignals(False)
        self._animation_intensity_val_lbl.setText(f"{animation_intensity:.1f}x")

        self._active_custom_accent = custom_accent
        self._update_accent_button_text()
        self._preset_desc_lbl.setText(THEMES.get(theme_preset, {}).get("description", ""))
        self._update_swatches()
        self._update_theme_gallery()


    def _update_accent_button_text(self):
        if self._active_custom_accent:
            self._custom_accent_btn.setText(f"Accent: {self._active_custom_accent}")
            self._accent_color_preview.setStyleSheet(
                f"background-color: {self._active_custom_accent}; border: 1px solid #35356E; border-radius: 4px;"
            )
        else:
            self._custom_accent_btn.setText("Pick Custom Accent...")
            colors = get_theme_colors(self.state)
            accent_default = colors.get("accent", "#00C2FF")
            self._accent_color_preview.setStyleSheet(
                f"background-color: {accent_default}; border: 1px solid #35356E; border-radius: 4px;"
            )


    def _on_preset_changed(self):
        preset_name = self._theme_preset_combo.currentText()
        preset_data = THEMES.get(preset_name, {})
        self._preset_desc_lbl.setText(preset_data.get("description", ""))
        self._update_accent_button_text()
        self._apply_active_theme()
        self._update_theme_gallery()


    def _pick_custom_accent(self):
        preset_name = self._theme_preset_combo.currentText()
        default_color = THEMES.get(preset_name, {}).get("accent", "#00C2FF")
        if self._active_custom_accent:
            default_color = self._active_custom_accent
            
        color = QColorDialog.getColor(QColor(default_color), self, "Select Custom Accent Color")
        if color.isValid():
            self._active_custom_accent = color.name().upper()
            self._update_accent_button_text()
            self._apply_active_theme()


    def _reset_custom_accent(self):
        self._active_custom_accent = None
        self._update_accent_button_text()
        self._apply_active_theme()


