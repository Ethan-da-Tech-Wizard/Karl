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

        self._model_lbl  = _lbl("● no model", self)
        self._state_lbl  = _lbl("idle", self)
        self._adapter_lbl = _lbl("", self)
        self._ram_lbl    = _lbl("", self)

        for w in (
            self._model_lbl, _sep(self),
            self._adapter_lbl, _sep(self),
            self._state_lbl,
        ):
            layout.addWidget(w)

        layout.addStretch()
        layout.addWidget(self._ram_lbl)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(4000)
        self._tick()

    def _tick(self):
        try:
            mb = psutil.Process(os.getpid()).memory_info().rss / 1_048_576
            self._ram_lbl.setText(f"{mb:.0f} MB")
        except Exception:
            pass

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
