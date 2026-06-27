"""HUD toolbar — panel visibility toggles and status indicator row."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton


def build_hud_toolbar(w) -> None:
    """Populate w._hud_toolbar with the HUD toggle buttons."""
    tb = w._hud_toolbar
    tbl = QHBoxLayout(tb)
    tbl.setContentsMargins(10, 4, 10, 4)
    tbl.setSpacing(10)

    lbl = QLabel("HUD:")
    lbl.setStyleSheet("font-size: 8pt; font-weight: bold; color: #6A7B95; letter-spacing: 1.5px;")
    tbl.addWidget(lbl)

    w._hud_sessions_btn = QPushButton("Sessions")
    w._hud_sessions_btn.setObjectName("hud-btn")
    w._hud_sessions_btn.setCheckable(True)
    w._hud_sessions_btn.setChecked(w._sessions_dock.isVisible())
    w._hud_sessions_btn.clicked.connect(w._toggle_sessions)
    tbl.addWidget(w._hud_sessions_btn)

    w._hud_reasoning_btn = QPushButton("Reasoning")
    w._hud_reasoning_btn.setObjectName("hud-btn")
    w._hud_reasoning_btn.setCheckable(True)
    w._hud_reasoning_btn.setChecked(w._reasoning_dock.isVisible())
    w._hud_reasoning_btn.clicked.connect(w._toggle_reasoning)
    tbl.addWidget(w._hud_reasoning_btn)

    w._hud_rag_btn = QPushButton("RAG Sources")
    w._hud_rag_btn.setObjectName("hud-btn")
    w._hud_rag_btn.setCheckable(True)
    w._hud_rag_btn.setChecked(w._rag_sources_view.isVisible())
    w._hud_rag_btn.clicked.connect(w._toggle_rag_hud)
    tbl.addWidget(w._hud_rag_btn)

    w._hud_context_btn = QPushButton("Context HUD")
    w._hud_context_btn.setObjectName("hud-btn")
    w._hud_context_btn.setCheckable(True)
    w._hud_context_btn.setChecked(w._context_bar.isVisible())
    w._hud_context_btn.clicked.connect(w._toggle_context_hud)
    tbl.addWidget(w._hud_context_btn)

    w._hud_settings_btn = QPushButton("Settings")
    w._hud_settings_btn.setObjectName("hud-btn")
    w._hud_settings_btn.setCheckable(True)
    w._hud_settings_btn.setChecked(False)
    w._hud_settings_btn.clicked.connect(w._toggle_settings_overlay)
    tbl.addWidget(w._hud_settings_btn)

    tbl.addStretch()

    w._hud_master_btn = QPushButton("Hide All HUDs")
    w._hud_master_btn.setObjectName("hud-btn")
    w._hud_master_btn.clicked.connect(w._toggle_all_huds)
    tbl.addWidget(w._hud_master_btn)

    w._hud_help_btn = QPushButton("?")
    w._hud_help_btn.setObjectName("hud-btn")
    w._hud_help_btn.setFixedWidth(28)
    w._hud_help_btn.setToolTip("Keyboard shortcuts  (?)")
    w._hud_help_btn.setAccessibleName("Show keyboard shortcuts")
    w._hud_help_btn.clicked.connect(w._toggle_shortcuts_overlay)
    tbl.addWidget(w._hud_help_btn)

    w._sessions_dock.visibilityChanged.connect(lambda _: update_hud_btn_styles(w))
    w._reasoning_dock.visibilityChanged.connect(lambda _: update_hud_btn_styles(w))

    update_hud_btn_styles(w)


# ── toggle functions ──────────────────────────────────────────────────────────

def update_hud_btn_styles(w) -> None:
    settings_visible = (
        getattr(w, "_settings_overlay", None) is not None
        and w._settings_overlay.isVisible()
    )
    for btn, val in [
        (getattr(w, "_hud_sessions_btn", None), w._sessions_dock.isVisible()),
        (getattr(w, "_hud_reasoning_btn", None), w._reasoning_dock.isVisible()),
        (getattr(w, "_hud_rag_btn", None), w._rag_sources_view.isVisible()),
        (getattr(w, "_hud_context_btn", None), w._context_bar.isVisible()),
        (getattr(w, "_hud_settings_btn", None), settings_visible),
    ]:
        if btn:
            btn.blockSignals(True)
            btn.setChecked(val)
            btn.setProperty("active", "true" if val else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.blockSignals(False)


def toggle_rag_hud(w) -> None:
    visible = not w._rag_sources_view.isVisible()
    w._rag_sources_view.setVisible(visible)
    update_hud_btn_styles(w)


def toggle_context_hud(w) -> None:
    visible = not w._context_bar.isVisible()
    w._context_bar.setVisible(visible)
    if hasattr(w, "_token_row"):
        w._token_row.setVisible(visible)
    update_hud_btn_styles(w)


def toggle_all_huds(w) -> None:
    any_visible = (
        w._sessions_dock.isVisible()
        or w._reasoning_dock.isVisible()
        or w._rag_sources_view.isVisible()
        or w._context_bar.isVisible()
    )
    target_visible = not any_visible

    w._sessions_dock.setVisible(target_visible)
    w._reasoning_dock.setVisible(target_visible)
    w._rag_sources_view.setVisible(target_visible)
    w._context_bar.setVisible(target_visible)
    if hasattr(w, "_token_row"):
        w._token_row.setVisible(target_visible)

    update_hud_btn_styles(w)
    w._hud_master_btn.setText("Hide All HUDs" if target_visible else "Show All HUDs")
