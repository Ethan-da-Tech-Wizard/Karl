from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

_ITEMS = [
    ("◈", "Workbench",  0),
    ("⊕", "Prompt Lab", 1),
    ("⊞", "Knowledge",  2),
    ("◇", "Vision",     3),
    ("⬡", "AI Lab",     4),
    ("◎", "Eval",       5),
    ("☄", "Swarm",      6),
    ("≡", "System",     7),
    ("▤", "Codex",      8),
    ("⟳", "Flywheel",    9),
]


class _SidebarButton(QPushButton):
    """Fixed-size accessible workspace navigation button."""

    def __init__(self, icon: str, label: str, index: int, parent=None):
        """Create a sidebar button for one workspace index."""
        super().__init__(parent)
        self.index = index
        self._icon = icon
        self._label = label
        self.setObjectName("sidebar-btn")
        self.setFixedSize(56, 62)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{icon}\n{label}")
        self.setFont(QFont("JetBrains Mono, Consolas, monospace", 7))
        self.setAccessibleName(f"Workspace Navigator: {label}")
        self.setAccessibleDescription(f"Switch active view to the {label} workspace")

    def set_compact(self, compact: bool):
        """Switch between label and icon-only presentation for narrow windows."""
        if compact:
            self.setText(self._icon)
            self.setFixedSize(48, 50)
            self.setFont(QFont("JetBrains Mono, Consolas, monospace", 12))
        else:
            self.setText(f"{self._icon}\n{self._label}")
            self.setFixedSize(56, 62)
            self.setFont(QFont("JetBrains Mono, Consolas, monospace", 7))

    def set_active(self, active: bool):
        """Set the active dynamic QSS property and force a style refresh."""
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QWidget):
    """Vertical workspace navigator that emits selected stack indexes."""

    workspace_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        """Build the ten-workspace navigator and select Workbench."""
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
            3: "Vision Workbench (Saved images, OCR, and screenshot reasoning)",
            4: "AI Lab (Flywheel, LoRA/QLoRA training, and Mini-GPT sandbox)",
            5: "Eval Suite (Automated model benchmarking)",
            6: "Swarm Studio (dependency layers, task states, verification, and tracebacks)",
            7: "System Config (Hardware readout & model loader settings)",
            8: "Codex (Prompt taxonomy & information guide)",
            9: "Flywheel Studio (Telemetry & fine-tuning loop metrics)",
        }
        self._buttons: list[_SidebarButton] = []
        self._compact = False
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
        """Programmatically select a workspace index."""
        self._select(index)

    def set_compact(self, compact: bool):
        """Use icon-only navigation when the app is too narrow for labels."""
        if self._compact == compact:
            return
        self._compact = compact
        self.setFixedWidth(48 if compact else 56)
        for btn in self._buttons:
            btn.set_compact(compact)
