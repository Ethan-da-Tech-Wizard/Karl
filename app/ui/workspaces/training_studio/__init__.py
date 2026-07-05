from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget

from app.ui.workspaces.training_studio.flywheel_tab import FlywheelTab
from app.ui.workspaces.training_studio.dataset_tab import DatasetTab
from app.ui.workspaces.training_studio.export_tab import ExportTab
from app.ui.workspaces.training_studio.train_tab import TrainTab
from app.ui.workspaces.training_studio.auto_train_tab import AutoTrainTab
from app.ui.workspaces.training_studio.mini_gpt_tab import MiniGptTab
from app.ui.workspaces.training_studio.threads import AutoTrainThread

class TrainingStudioWorkspace(QWidget):
    """AI Lab workspace for curation, export, LoRA, and flywheel flows."""

    def __init__(self, state, parent=None):
        """Create training tabs and bind dataset refresh signals."""
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._build_ui()

    def _build_ui(self):
        """Build the AI Lab title, stats row, and tab controller."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title_row = QWidget()
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("AI Lab")
        lbl.setObjectName("lbl-accent")
        tr.addWidget(lbl)
        tr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("lbl-muted")
        tr.addWidget(self._stats_lbl)
        root.addWidget(title_row)

        desc = QLabel(
            "Build and improve local models with curated feedback, SFT/DPO export, "
            "LoRA/QLoRA adapters, Auto-Train, and the Mini-GPT sandbox."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px; padding-left: 2px;")
        root.addWidget(desc)

        self.flywheel_tab = FlywheelTab(self.state)
        self.dataset_tab = DatasetTab(self.state)
        self.export_tab = ExportTab(self.state)
        self.train_tab = TrainTab(self.state)
        self.auto_train_tab = AutoTrainTab(self.state)
        self.mini_gpt_tab = MiniGptTab(self.state)

        # Wire communication signals
        self.dataset_tab.dataset_changed.connect(self._refresh)

        tabs = QTabWidget()
        tabs.addTab(self.flywheel_tab, "Flywheel")
        tabs.addTab(self.dataset_tab, "Dataset")
        tabs.addTab(self.export_tab, "Export")
        tabs.addTab(self.train_tab, "Train")
        tabs.addTab(self.auto_train_tab, "Auto-Train")
        tabs.addTab(self.mini_gpt_tab, "Mini-GPT Sandbox")
        tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs = tabs
        root.addWidget(tabs, 1)

        self._refresh()

    def _on_tab_changed(self, idx: int):
        if idx == 0:  # Flywheel tab
            self.flywheel_tab.load_stats()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        stats = self.state.curator.get_stats()
        self._stats_lbl.setText(
            f"<b>{stats['total']}</b> examples  &middot;  "
            f"<span style='color:#2DD4A0;'><b>{stats['thumbs_up']}</b> good</span>  &middot;  "
            f"<span style='color:#F0B030;'><b>{stats['corrected']}</b> corrected</span>"
        )
        self.dataset_tab.refresh()
        self.train_tab.refresh()
