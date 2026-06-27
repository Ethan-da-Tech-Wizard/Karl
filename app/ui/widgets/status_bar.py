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
        self._ctx_lbl     = _lbl("", self)
        self._speculative_lbl = _lbl("", self)
        self._load_stats_lbl = _lbl("", self)   # Load: Xs | VRAM: Y GB/s
        self._ram_lbl     = _lbl("", self)

        self._bridge_dot = QLabel("●")
        self._bridge_dot.setObjectName("lbl-muted")
        self._bridge_dot.setFixedWidth(12)

        self._bridge_lbl  = _lbl("VS Code: offline", self)
        # Compatibility for bridge tests and older callers that still refer to
        # this indicator as the VS Code label.
        self._vscode_lbl = self._bridge_lbl

        self._load_stats_sep = _sep(self)

        for w in (
            self._model_lbl, _sep(self),
            self._adapter_lbl, _sep(self),
            self._state_lbl, _sep(self),
            self._ctx_lbl,
            self._speculative_lbl,
            self._load_stats_sep,
            self._load_stats_lbl,
        ):
            layout.addWidget(w)

        # Keep the separator and stats label invisible until stats arrive
        self._load_stats_sep.setVisible(False)
        self._load_stats_lbl.setVisible(False)

        self._thermal_lbl = QLabel("⚠️ GPU Overheated (Throttling)", self)
        self._thermal_lbl.setStyleSheet(
            "color: #FF3B30; font-weight: bold;"
        )
        self._thermal_lbl.setVisible(False)
        self._thermal_blink_on = True

        self._thermal_timer = QTimer(self)
        self._thermal_timer.setInterval(600)
        self._thermal_timer.timeout.connect(self._toggle_thermal_visibility)

        layout.addStretch()
        layout.addWidget(self._thermal_lbl)
        layout.addWidget(_sep(self))
        layout.addWidget(self._ram_lbl)
        layout.addWidget(_sep(self))
        layout.addWidget(self._bridge_dot)
        layout.addWidget(self._bridge_lbl)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._tick)
        self._poll_timer.start(4000)
        self._tick()

    # ── internal ──────────────────────────────────────────────────────────────

    def _toggle_thermal_visibility(self):
        self._thermal_blink_on = not self._thermal_blink_on
        color = "#FF3B30" if self._thermal_blink_on else "#7A1A14"
        self._thermal_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

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
        try:
            from core.hardware_scout import get_hardware_profile

            hw = get_hardware_profile()
            thermal = any(
                "Thermal Throttling Active" in gpu.get("alerts", [])
                for gpu in hw.get("gpu_list", [])
            )
            self._set_thermal_warning(thermal)
        except Exception:
            pass

    # ── public API ────────────────────────────────────────────────────────────

    def set_thermal_throttling(self, active: bool) -> None:
        """Show/hide the blinking GPU thermal warning. Also callable externally."""
        self._set_thermal_warning(active)

    def _set_thermal_warning(self, active: bool) -> None:
        if active:
            self._thermal_lbl.setVisible(True)
            if not self._thermal_timer.isActive():
                self._thermal_blink_on = True
                self._thermal_lbl.setStyleSheet("color: #FF3B30; font-weight: bold;")
                self._thermal_timer.start()
        else:
            self._thermal_timer.stop()
            self._thermal_lbl.setVisible(False)
            self._thermal_blink_on = True
            self._thermal_lbl.setStyleSheet("color: #FF3B30; font-weight: bold;")

    def set_model(self, name: str):
        self._model_lbl.setText(f"● {name}")
        self._model_lbl.setObjectName("lbl-accent")
        self._model_lbl.style().unpolish(self._model_lbl)
        self._model_lbl.style().polish(self._model_lbl)

    def set_adapter(self, name: str | None):
        self._adapter_lbl.setText(f"⬡ {name}" if name else "")

    def set_speculative_active(self, active: bool):
        self._speculative_lbl.setText("[Speculative Active]" if active else "")
        self._speculative_lbl.setObjectName("lbl-accent" if active else "lbl-muted")
        self._speculative_lbl.style().unpolish(self._speculative_lbl)
        self._speculative_lbl.style().polish(self._speculative_lbl)

    def set_state(self, text: str, active: bool = False):
        self._state_lbl.setText(text)
        obj = "lbl-accent" if active else "lbl-muted"
        self._state_lbl.setObjectName(obj)
        self._state_lbl.style().unpolish(self._state_lbl)
        self._state_lbl.style().polish(self._state_lbl)

    def set_context_stats(self, total: int, hist: int, rag: int, budget: int):
        self._ctx_lbl.setText(f"ctx {total:,} / {budget:,}")
        if total > 0.9 * budget:
            self._ctx_lbl.setObjectName("lbl-danger")
        elif total > 0.7 * budget:
            self._ctx_lbl.setObjectName("lbl-warning")
        else:
            self._ctx_lbl.setObjectName("lbl-muted")
        self._ctx_lbl.style().unpolish(self._ctx_lbl)
        self._ctx_lbl.style().polish(self._ctx_lbl)
        self._ctx_lbl.setToolTip(f"Context breakdown:\n- System/Prompt: {total-hist-rag:,}\n- History: {hist:,}\n- RAG: {rag:,}")

    def set_load_stats(
        self,
        latency_s: float | None,
        bandwidth_gbs: float | None,
    ) -> None:
        """
        Display GGUF load latency and PCIe VRAM bandwidth in the status bar.

        Color coding for bandwidth (PCIe Gen reference):
          ≥ 15 GB/s — normal (Gen3/Gen4 x16, healthy)
          8 – 15 GB/s — orange warning (Gen3 x8 / Gen2 x16 — moderate bottleneck)
          < 8 GB/s  — red warning  (severely throttled lane)

        Calling with (None, None) hides the slot.
        """
        if latency_s is None:
            self._load_stats_sep.setVisible(False)
            self._load_stats_lbl.setVisible(False)
            return

        # Build display text
        lat_str = f"{latency_s:.1f}s"
        if bandwidth_gbs is not None:
            text = f"Load: {lat_str} | VRAM: {bandwidth_gbs:.1f} GB/s"
        else:
            text = f"Load: {lat_str}"
        self._load_stats_lbl.setText(text)

        # Bandwidth colour coding
        if bandwidth_gbs is None:
            # No CUDA — use muted style, no colour warning
            self._load_stats_lbl.setStyleSheet("")
            self._load_stats_lbl.setObjectName("lbl-muted")
            self._load_stats_lbl.setToolTip("No CUDA device detected.")
        elif bandwidth_gbs < 8.0:
            # Severely throttled PCIe lane — likely Gen2 x8 or shared slot
            self._load_stats_lbl.setStyleSheet("color: #FF5C7A;")
            self._load_stats_lbl.setToolTip(
                f"PCIe bottleneck: {bandwidth_gbs:.1f} GB/s — severely limited lane "
                "(< 8 GB/s). Token generation may be significantly throttled.\n"
                "Check PCIe slot assignment and lane configuration in BIOS."
            )
        elif bandwidth_gbs < 15.0:
            # Moderate bottleneck — Gen3 x8 or Gen2 x16
            self._load_stats_lbl.setStyleSheet("color: #F0B030;")
            self._load_stats_lbl.setToolTip(
                f"PCIe bottleneck: {bandwidth_gbs:.1f} GB/s — moderate lane limitation "
                "(< 15 GB/s, Gen3 x8 / Gen2 x16 territory).\n"
                "Inference throughput may be bandwidth-constrained on large models."
            )
        else:
            # Healthy PCIe bandwidth — Gen3/Gen4 x16
            self._load_stats_lbl.setStyleSheet("")
            self._load_stats_lbl.setObjectName("lbl-muted")
            self._load_stats_lbl.setToolTip(
                f"PCIe bandwidth: {bandwidth_gbs:.1f} GB/s — healthy (Gen3/Gen4 x16)."
            )

        self._load_stats_lbl.style().unpolish(self._load_stats_lbl)
        self._load_stats_lbl.style().polish(self._load_stats_lbl)
        self._load_stats_sep.setVisible(True)
        self._load_stats_lbl.setVisible(True)

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
