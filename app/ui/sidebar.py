from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

_ITEMS = [
    ("◈", "Workbench",  0),
    ("⊕", "Prompt Lab", 1),
    ("⊞", "Knowledge",  2),
    ("⬡", "Training",   3),
    ("◎", "Eval",       4),
    ("≡", "System",     5),
    ("ℹ", "Docs",       6),
]


class _SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("sidebar-btn")
        self.setFixedSize(56, 62)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{icon}\n{label}")
        self.setFont(QFont("JetBrains Mono, Consolas, monospace", 7))

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QWidget):
    workspace_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(56)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)

        logo = QLabel("K", self)
        logo.setObjectName("sidebar-logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedHeight(44)
        layout.addWidget(logo)

        tooltips = {
            0: "Workbench (Main Chat Space)",
            1: "Prompt Lab (A/B testing & tokenization)",
            2: "Knowledge Base (RAG context & source ingestion)",
            3: "Training Studio (LoRA/QLoRA fine-tuning & curator)",
            4: "Eval Suite (Automated model benchmarking)",
            5: "System Config (Hardware readout & model loader settings)",
            6: "Documentation Guide (How to utilize tools)",
        }
        self._buttons: list[_SidebarButton] = []
        for icon, label, idx in _ITEMS:
            btn = _SidebarButton(icon, label, idx, self)
            btn.setToolTip(tooltips.get(idx, ""))
            btn.clicked.connect(lambda _checked, i=idx: self._select(i))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._buttons.append(btn)

        layout.addStretch()
        self._select(0)

    def _select(self, index: int):
        for btn in self._buttons:
            btn.set_active(btn.index == index)
        self.workspace_changed.emit(index)

    def select(self, index: int):
        self._select(index)
