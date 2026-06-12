from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer
import psutil
import os


def _lbl(text: str, parent: QWidget) -> QLabel:
    l = QLabel(text, parent)
    l.setObjectName("lbl-muted")
    return l


def _sep(parent: QWidget) -> QLabel:
    l = QLabel("·", parent)
    l.setObjectName("lbl-muted")
    return l


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("status-bar")
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        self._model_lbl   = _lbl("● no model", self)
        self._adapter_lbl = _lbl("", self)
        self._state_lbl   = _lbl("idle", self)
        self._vscode_lbl  = _lbl("⇄ VS Code: offline", self)
        self._bridge_lbl  = _lbl("Bridge: offline", self)
        self._ram_lbl     = _lbl("", self)

        for w in (
            self._model_lbl, _sep(self),
            self._adapter_lbl, _sep(self),
            self._state_lbl, _sep(self),
            self._vscode_lbl,
        ):
            layout.addWidget(w)

        layout.addStretch()
        layout.addWidget(self._ram_lbl)
        layout.addWidget(_sep(self))
        layout.addWidget(self._bridge_lbl)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._tick)
        self._poll_timer.start(4000)
        self._tick()

    # ── internal ──────────────────────────────────────────────────────────────

    def _tick(self):
        self._update_ram()
        self._update_bridge()

    def _update_ram(self):
        try:
            mb = psutil.Process(os.getpid()).memory_info().rss / 1_048_576
            self._ram_lbl.setText(f"{mb:.0f} MB")
        except Exception:
            pass

    def _update_bridge(self):
        try:
            from app.engine.websocket_server import WebSocketServerManager
            ws_mgr = WebSocketServerManager._instance
            if ws_mgr is not None and ws_mgr.server is not None:
                if len(ws_mgr.clients) > 0:
                    self._vscode_lbl.setText("⇄ VS Code: connected")
                    self._vscode_lbl.setObjectName("lbl-accent")
                else:
                    self._vscode_lbl.setText("⇄ VS Code: listening")
                    self._vscode_lbl.setObjectName("lbl-muted")
            else:
                self._vscode_lbl.setText("⇄ VS Code: offline")
                self._vscode_lbl.setObjectName("lbl-muted")
            self._vscode_lbl.style().unpolish(self._vscode_lbl)
            self._vscode_lbl.style().polish(self._vscode_lbl)
        except Exception:
            self._vscode_lbl.setText("⇄ VS Code: offline")
            self._vscode_lbl.setObjectName("lbl-muted")
            self._vscode_lbl.style().unpolish(self._vscode_lbl)
            self._vscode_lbl.style().polish(self._vscode_lbl)

    # ── public API ────────────────────────────────────────────────────────────

    def set_model(self, name: str):
        self._model_lbl.setText(f"● {name}")
        self._model_lbl.setObjectName("lbl-accent")
        self._model_lbl.style().unpolish(self._model_lbl)
        self._model_lbl.style().polish(self._model_lbl)

    def set_adapter(self, name: str | None):
        self._adapter_lbl.setText(f"⬡ {name}" if name else "")

    def set_state(self, text: str, active: bool = False):
        self._state_lbl.setText(text)
        obj = "lbl-accent" if active else "lbl-muted"
        self._state_lbl.setObjectName(obj)
        self._state_lbl.style().unpolish(self._state_lbl)
        self._state_lbl.style().polish(self._state_lbl)

    def set_bridge_status(self, state: str, clients: int = 0):
        """Explicitly update the bridge indicator.

        state: 'connected' | 'listening' | 'offline' | 'error'
        """
        if state == "connected":
            text = f"⇄ Bridge: {clients} client{'s' if clients != 1 else ''}"
            obj = "lbl-accent"
        elif state == "listening":
            text = "⇄ Bridge: listening"
            obj = "lbl-muted"
        elif state == "error":
            text = "⇄ Bridge: error"
            obj = "lbl-muted"
        else:
            text = "⇄ Bridge: offline"
            obj = "lbl-muted"
        self._bridge_lbl.setText(text)
        self._bridge_lbl.setObjectName(obj)
        self._bridge_lbl.style().unpolish(self._bridge_lbl)
        self._bridge_lbl.style().polish(self._bridge_lbl)
