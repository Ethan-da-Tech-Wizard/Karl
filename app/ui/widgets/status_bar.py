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
        self._ram_lbl     = _lbl("", self)
        
        self._bridge_dot = QLabel("●")
        self._bridge_dot.setObjectName("lbl-muted")
        self._bridge_dot.setFixedWidth(12)
        
        self._bridge_lbl  = _lbl("VS Code: offline", self)
        # Compatibility for bridge tests and older callers that still refer to
        # this indicator as the VS Code label.
        self._vscode_lbl = self._bridge_lbl

        for w in (
            self._model_lbl, _sep(self),
            self._adapter_lbl, _sep(self),
            self._state_lbl,
        ):
            layout.addWidget(w)

        layout.addStretch()
        layout.addWidget(self._ram_lbl)
        layout.addWidget(_sep(self))
        layout.addWidget(self._bridge_dot)
        layout.addWidget(self._bridge_lbl)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._tick)
        self._poll_timer.start(4000)
        self._tick()

    # ── internal ──────────────────────────────────────────────────────────────

    def _tick(self):
        try:
            mb = psutil.Process(os.getpid()).memory_info().rss / 1_048_576
            self._ram_lbl.setText(f"{mb:.0f} MB")
        except Exception:
            pass
        try:
            from app.engine.websocket_server import WebSocketServerManager

            manager = WebSocketServerManager._instance
            if manager is None or manager.server is None:
                self.set_bridge_status("offline")
            elif manager.clients:
                self.set_bridge_status("connected", len(manager.clients), manager.get_client_info())
            else:
                self.set_bridge_status("listening")
        except Exception:
            self.set_bridge_status("offline")

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

    def set_bridge_status(self, state: str, clients: int = 0, client_info: list[dict] | None = None):
        """Update the bridge indicator. state: 'connected' | 'listening' | 'offline' | 'error'"""
        dot_color = "#505068" # Grey
        tooltip = "WebSocket Bridge: Offline"

        if state == "connected":
            text = f"VS Code: {clients} client{'s' if clients != 1 else ''}"
            obj = "lbl-accent"
            dot_color = "#00C2FF" # Green/Accent (Active)
            
            if client_info:
                tooltip = "Connected Clients:\n"
                for c in client_info:
                    lat = f"{c['latency_ms']:.1f}ms" if c['latency_ms'] >= 0 else "unknown"
                    tooltip += f"• {c['id']} ({c['ip']}) - Latency: {lat}\n"
            else:
                tooltip = f"Connected: {clients} client(s)"
                
        elif state == "listening":
            text = "VS Code: listening"
            obj = "lbl-muted"
            dot_color = "#FFCC00" # Amber (Awaiting Handshake)
            tooltip = "WebSocket Bridge: Listening for connections..."
            
        elif state == "error":
            text = "VS Code: error"
            obj = "lbl-muted"
            dot_color = "#FF3366" # Red
            tooltip = "WebSocket Bridge: Error occurred"
            
        else:
            text = "VS Code: offline"
            obj = "lbl-muted"
            dot_color = "#505068" # Grey
            tooltip = "WebSocket Bridge: Offline"

        self._bridge_lbl.setText(text)
        self._bridge_lbl.setObjectName(obj)
        self._bridge_lbl.setToolTip(tooltip)
        self._bridge_lbl.style().unpolish(self._bridge_lbl)
        self._bridge_lbl.style().polish(self._bridge_lbl)
        
        self._bridge_dot.setStyleSheet(f"color: {dot_color};")
        self._bridge_dot.setToolTip(tooltip)
