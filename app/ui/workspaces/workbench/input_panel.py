"""Input panel — token HUD row, prompt text edit, and controls row."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QCheckBox, QPushButton, QLabel, QProgressBar,
)
from PyQt6.QtCore import Qt

from core.workflows import list_workflows
from app.ui.workspaces.workbench.profiles import AGENT_PROFILES
from app.ui.widgets.symbolic_icon import IconBtn, GearIcon, HamburgerIcon, BrainIcon


def build_input_area(w) -> QWidget:
    """Build the input area widget.

    Attaches to w: _token_row, _token_bar, _token_lbl, _token_remaining_lbl,
    _input, _workflow_combo, _agent_combo, _rag_check, _loop_check,
    _params_toggle, _sessions_toggle, _reasoning_toggle, _model_pill,
    _stop_btn, _send_btn.
    """
    input_container = QFrame()
    input_container.setObjectName("chat-composer")
    input_container.setFixedHeight(124)
    ic_layout = QVBoxLayout(input_container)
    ic_layout.setContentsMargins(10, 8, 10, 8)
    ic_layout.setSpacing(5)

    # ── token budget HUD ──────────────────────────────────────────────────────
    w._token_row = QWidget()
    w._token_row.setObjectName("token-row")
    token_layout = QHBoxLayout(w._token_row)
    token_layout.setContentsMargins(0, 0, 0, 0)
    token_layout.setSpacing(8)

    w._token_lbl = QLabel("0 / 4,096 tokens")
    w._token_lbl.setObjectName("lbl-muted")
    w._token_lbl.setStyleSheet("font-size: 8pt;")

    w._token_remaining_lbl = QLabel("free 4,096")
    w._token_remaining_lbl.setObjectName("lbl-muted")
    w._token_remaining_lbl.setStyleSheet("font-size: 8pt;")

    w._token_bar = QProgressBar()
    w._token_bar.setObjectName("token-budget-bar")
    w._token_bar.setFixedHeight(6)
    w._token_bar.setTextVisible(False)
    w._token_bar.setRange(0, 100)
    w._token_bar.setValue(0)

    token_layout.addWidget(w._token_bar, 1)
    token_layout.addWidget(w._token_lbl)
    token_layout.addWidget(w._token_remaining_lbl)
    ic_layout.addWidget(w._token_row)

    # ── prompt input ──────────────────────────────────────────────────────────
    w._input = QTextEdit()
    w._input.setPlaceholderText("Ask Karl...")
    w._input.setFixedHeight(58)
    w._input.installEventFilter(w)
    w._input.textChanged.connect(w._update_token_budget)
    ic_layout.addWidget(w._input)

    # ── controls row ──────────────────────────────────────────────────────────
    ctrl = QWidget()
    ctrl_layout = QHBoxLayout(ctrl)
    ctrl_layout.setContentsMargins(0, 0, 0, 0)
    ctrl_layout.setSpacing(8)

    w._workflow_combo = QComboBox()
    w._workflow_combo.setFixedWidth(150)
    w._workflow_combo.setToolTip("Active prompt generation workflow template")
    for name, label in list_workflows():
        w._workflow_combo.addItem(label, name)
    default_idx = w._workflow_combo.findData("general_chat")
    if default_idx >= 0:
        w._workflow_combo.setCurrentIndex(default_idx)
    ctrl_layout.addWidget(w._workflow_combo)

    w._agent_combo = QComboBox()
    w._agent_combo.setFixedWidth(120)
    w._agent_combo.setToolTip("Select Karl's active workbench agent profile")
    for key, data in AGENT_PROFILES.items():
        w._agent_combo.addItem(data["label"], key)
        idx = w._agent_combo.count() - 1
        w._agent_combo.setItemData(idx, data["description"], Qt.ItemDataRole.ToolTipRole)
    w._agent_combo.currentIndexChanged.connect(w._on_agent_selected)
    ctrl_layout.addWidget(w._agent_combo)

    w._rag_check = QCheckBox("RAG")
    w._rag_check.setToolTip("Inject relevant knowledge base context into prompt")
    w._rag_check.toggled.connect(w._update_expert_strip)
    ctrl_layout.addWidget(w._rag_check)

    w._loop_check = QCheckBox("Loop")
    w._loop_check.setToolTip("Run generation in an autonomous iterative agentic loop")
    w._loop_check.toggled.connect(w._update_expert_strip)
    ctrl_layout.addWidget(w._loop_check)

    w._params_toggle = IconBtn(GearIcon, w.state, tooltip="Toggle Settings drawer")
    w._params_toggle.clicked.connect(w._toggle_settings_overlay)
    ctrl_layout.addWidget(w._params_toggle)

    w._sessions_toggle = IconBtn(HamburgerIcon, w.state, tooltip="Toggle Sessions panel")
    w._sessions_toggle.clicked.connect(w._toggle_sessions)
    ctrl_layout.addWidget(w._sessions_toggle)

    w._reasoning_toggle = IconBtn(BrainIcon, w.state, tooltip="Toggle Reasoning panel")
    w._reasoning_toggle.clicked.connect(w._toggle_reasoning)
    ctrl_layout.addWidget(w._reasoning_toggle)

    ctrl_layout.addStretch()

    w._model_pill = QLabel("")
    w._model_pill.setObjectName("model-pill")
    w._model_pill.setFixedWidth(0)
    w._model_pill.setToolTip("Active base model and adapter overlay")
    ctrl_layout.addWidget(w._model_pill)

    w._stop_btn = QPushButton("■ stop")
    w._stop_btn.setObjectName("btn-danger")
    w._stop_btn.setFixedWidth(76)
    w._stop_btn.setEnabled(False)
    w._stop_btn.setToolTip("Interrupt the active generation thread")
    w._stop_btn.clicked.connect(w._stop)
    ctrl_layout.addWidget(w._stop_btn)

    w._send_btn = QPushButton("send ↵")
    w._send_btn.setObjectName("btn-primary")
    w._send_btn.setFixedWidth(86)
    w._send_btn.setToolTip("Send prompt to Karl (Ctrl+Enter)")
    w._send_btn.clicked.connect(w._send)
    ctrl_layout.addWidget(w._send_btn)

    ic_layout.addWidget(ctrl)
    return input_container
