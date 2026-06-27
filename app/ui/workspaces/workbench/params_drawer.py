"""Parameters drawer — sliding settings overlay with hyperparams and feedback buttons."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QScrollArea, QLabel,
    QDoubleSpinBox, QSpinBox, QPushButton,
)
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation


def _label(text: str, obj: str = "") -> QLabel:
    lbl = QLabel(text)
    if obj:
        lbl.setObjectName(obj)
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def build_settings_overlay(w) -> None:
    """Build and attach the settings overlay to w._chat_panel.

    Attaches to w: _settings_overlay, _model_combo, _temp_spin, _topp_spin,
    _maxtok_spin, _thumb_btn, _thumb_down_btn, _correct_btn, _new_session_btn.
    """
    w._settings_overlay = QFrame(w._chat_panel)
    w._settings_overlay.setObjectName("settings-overlay")
    w._settings_overlay.setVisible(False)

    state = w.property("modelState") or "idle"
    w._settings_overlay.setProperty("modelState", state)

    main_layout = QVBoxLayout(w._settings_overlay)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    hdr_panel = QWidget()
    hdr_lay = QVBoxLayout(hdr_panel)
    hdr_lay.setContentsMargins(12, 12, 12, 6)
    hdr = QLabel("CONTROL CENTER")
    hdr.setObjectName("settings-overlay-header")
    hdr_lay.addWidget(hdr)
    main_layout.addWidget(hdr_panel)

    scroll = QScrollArea()
    scroll.setObjectName("settings-scroll-area")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet("background: transparent;")

    scroll_content = QWidget()
    scroll_content.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(scroll_content)
    layout.setContentsMargins(12, 6, 12, 12)
    layout.setSpacing(12)

    # ── hyperparams ───────────────────────────────────────────────────────────
    params_grp = QWidget()
    pl = QVBoxLayout(params_grp)
    pl.setContentsMargins(0, 0, 0, 0)
    pl.setSpacing(6)

    pl.addWidget(_label("Active Model", "lbl-muted"))
    from app.ui.widgets.model_combo import ModelComboBox
    w._model_combo = ModelComboBox(w.state, short_labels=True)
    w._model_combo.setToolTip("Select active model and adapter overlay")
    w._model_combo.currentIndexChanged.connect(w._on_model_selected)
    pl.addWidget(w._model_combo)

    pl.addWidget(_label("Temperature", "lbl-muted"))
    w._temp_spin = QDoubleSpinBox()
    w._temp_spin.setRange(0.0, 2.0)
    w._temp_spin.setSingleStep(0.05)
    w._temp_spin.setValue(w._hyperparams["temperature"])
    w._temp_spin.setToolTip("Generation temperature. Lower is deterministic, higher is creative.")
    w._temp_spin.valueChanged.connect(
        lambda v: w._hyperparams.__setitem__("temperature", v)
    )
    pl.addWidget(w._temp_spin)

    pl.addWidget(_label("Top-P", "lbl-muted"))
    w._topp_spin = QDoubleSpinBox()
    w._topp_spin.setRange(0.0, 1.0)
    w._topp_spin.setSingleStep(0.05)
    w._topp_spin.setValue(w._hyperparams["top_p"])
    w._topp_spin.setToolTip("Top-p sampling cutoff.")
    w._topp_spin.valueChanged.connect(
        lambda v: w._hyperparams.__setitem__("top_p", v)
    )
    pl.addWidget(w._topp_spin)

    pl.addWidget(_label("Max Tokens", "lbl-muted"))
    w._maxtok_spin = QSpinBox()
    w._maxtok_spin.setRange(64, 8192)
    w._maxtok_spin.setSingleStep(64)
    w._maxtok_spin.setValue(w._hyperparams["max_tokens"])
    w._maxtok_spin.setToolTip("Maximum number of tokens to generate.")
    w._maxtok_spin.valueChanged.connect(w._on_max_tokens_changed)
    pl.addWidget(w._maxtok_spin)

    layout.addWidget(params_grp)
    layout.addWidget(_hline())

    # ── feedback / actions ────────────────────────────────────────────────────
    fb_grp = QWidget()
    fbl = QVBoxLayout(fb_grp)
    fbl.setContentsMargins(0, 0, 0, 0)
    fbl.setSpacing(8)

    fbl.addWidget(_label("Actions & Feedback", "lbl-muted"))

    w._thumb_btn = QPushButton("✓ Good")
    w._thumb_btn.setObjectName("btn-success")
    w._thumb_btn.setEnabled(False)
    w._thumb_btn.setToolTip("Curate this response as a positive training example")
    w._thumb_btn.clicked.connect(w._on_thumb_up)
    fbl.addWidget(w._thumb_btn)

    w._thumb_down_btn = QPushButton("✗ Bad")
    w._thumb_down_btn.setObjectName("btn-danger")
    w._thumb_down_btn.setEnabled(False)
    w._thumb_down_btn.setToolTip("Flag this response as an incorrect training example")
    w._thumb_down_btn.clicked.connect(w._on_thumb_down)
    fbl.addWidget(w._thumb_down_btn)

    w._correct_btn = QPushButton("✎ Correct")
    w._correct_btn.setObjectName("btn-warning")
    w._correct_btn.setEnabled(False)
    w._correct_btn.setToolTip("Manually edit response to create corrected pair")
    w._correct_btn.clicked.connect(w._on_correct)
    fbl.addWidget(w._correct_btn)

    w._new_session_btn = QPushButton("+ New Session")
    w._new_session_btn.setObjectName("btn-ghost")
    w._new_session_btn.clicked.connect(w._new_session)
    fbl.addWidget(w._new_session_btn)

    layout.addWidget(fb_grp)
    layout.addStretch()

    scroll.setWidget(scroll_content)
    main_layout.addWidget(scroll, 1)


def toggle_settings_overlay(w) -> None:
    """Slide the settings overlay open or closed."""
    if not hasattr(w, "_settings_overlay") or w._settings_overlay is None:
        build_settings_overlay(w)

    visible = not w._settings_overlay.isVisible()

    if visible:
        w._settings_overlay.show()
        w._settings_overlay.raise_()

        parent_width = w._chat_panel.width()
        parent_height = w._chat_panel.height()
        overlay_width = 300

        start_rect = QRect(parent_width, 0, overlay_width, parent_height)
        end_rect = QRect(parent_width - overlay_width, 0, overlay_width, parent_height)
        w._settings_overlay.setGeometry(start_rect)

        if not getattr(w.state, "reduced_motion", False):
            w._settings_anim = QPropertyAnimation(w._settings_overlay, b"geometry")
            w._settings_anim.setDuration(250)
            w._settings_anim.setStartValue(start_rect)
            w._settings_anim.setEndValue(end_rect)
            w._settings_anim.start()
        else:
            w._settings_overlay.setGeometry(end_rect)
    else:
        parent_width = w._chat_panel.width()
        parent_height = w._chat_panel.height()
        overlay_width = 300

        start_rect = w._settings_overlay.geometry()
        end_rect = QRect(parent_width, 0, overlay_width, parent_height)

        if not getattr(w.state, "reduced_motion", False):
            w._settings_anim = QPropertyAnimation(w._settings_overlay, b"geometry")
            w._settings_anim.setDuration(200)
            w._settings_anim.setStartValue(start_rect)
            w._settings_anim.setEndValue(end_rect)
            w._settings_anim.finished.connect(w._settings_overlay.hide)
            w._settings_anim.start()
        else:
            w._settings_overlay.setGeometry(end_rect)
            w._settings_overlay.hide()

    w._update_hud_btn_styles()
