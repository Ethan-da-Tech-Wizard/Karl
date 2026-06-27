import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QLabel, QSpinBox, QDoubleSpinBox, QProgressBar, QCheckBox,
    QLineEdit, QGridLayout, QFrame, QMessageBox
)

from app.ui.widgets.glow_panel import GlowPanel
from app.ui.workspaces.training_studio.threads import AutoTrainThread
from app.engine.model_loader import ModelLoader

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section-header")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class AutoTrainTab(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._active_threads = set()
        self._auto_thread = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Left Column: Configuration
        left_col = GlowPanel(self.state)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_layout.addWidget(_section("FLYWHEEL AUTO-TRAIN CONFIG"))

        # Form layout-like structure
        left_layout.addWidget(QLabel("Target Behavior / Topic:"))
        self._auto_topic_input = QLineEdit()
        self._auto_topic_input.setPlaceholderText("e.g., modular arithmetic, binary search")
        self._auto_topic_input.setToolTip("Enter the specific capability you want Karl to learn")
        left_layout.addWidget(self._auto_topic_input)

        left_layout.addWidget(QLabel("Adapter Save Name:"))
        self._auto_adapter_input = QLineEdit()
        self._auto_adapter_input.setPlaceholderText("e.g., math_specialist")
        self._auto_adapter_input.setToolTip("Save folder name under data/adapters/")
        left_layout.addWidget(self._auto_adapter_input)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)

        # Generate Count
        self._auto_count_spin = QSpinBox()
        self._auto_count_spin.setRange(2, 200)
        self._auto_count_spin.setValue(15)
        self._auto_count_spin.setToolTip("Number of training problems to generate and verify")
        grid.addWidget(QLabel("Examples Count:"), 0, 0)
        grid.addWidget(self._auto_count_spin, 0, 1)

        # Epochs
        self._auto_epochs_spin = QSpinBox()
        self._auto_epochs_spin.setRange(1, 20)
        self._auto_epochs_spin.setValue(3)
        grid.addWidget(QLabel("Epochs:"), 0, 2)
        grid.addWidget(self._auto_epochs_spin, 0, 3)

        # Rank
        self._auto_rank_spin = QSpinBox()
        self._auto_rank_spin.setRange(1, 256)
        self._auto_rank_spin.setValue(16)
        grid.addWidget(QLabel("Rank:"), 1, 0)
        grid.addWidget(self._auto_rank_spin, 1, 1)

        # Alpha
        self._auto_alpha_spin = QSpinBox()
        self._auto_alpha_spin.setRange(1, 512)
        self._auto_alpha_spin.setValue(32)
        grid.addWidget(QLabel("Alpha:"), 1, 2)
        grid.addWidget(self._auto_alpha_spin, 1, 3)

        # LR
        self._auto_lr_spin = QDoubleSpinBox()
        self._auto_lr_spin.setDecimals(6)
        self._auto_lr_spin.setRange(1e-6, 1e-2)
        self._auto_lr_spin.setSingleStep(1e-5)
        self._auto_lr_spin.setValue(2e-4)
        grid.addWidget(QLabel("Learning Rate:"), 2, 0)
        grid.addWidget(self._auto_lr_spin, 2, 1)

        # QLoRA Checkbox
        self._auto_qlora_check = QCheckBox("4-bit QLoRA")
        self._auto_qlora_check.setChecked(True)
        grid.addWidget(self._auto_qlora_check, 2, 2, 1, 2)

        left_layout.addLayout(grid)
        left_layout.addWidget(_hline())

        # Auto Train Button
        self._auto_train_btn = QPushButton("▶ start auto-training flywheel")
        self._auto_train_btn.setObjectName("btn-primary")
        self._auto_train_btn.setFixedHeight(36)
        self._auto_train_btn.clicked.connect(self._begin_auto_training)
        left_layout.addWidget(self._auto_train_btn)

        # Progress bar
        self._auto_progress = QProgressBar()
        self._auto_progress.setVisible(False)
        left_layout.addWidget(self._auto_progress)

        left_layout.addStretch()
        layout.addWidget(left_col, 1)

        # Right Column: Guide & Output Logs
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Guide panel explaining the flywheel
        guide_box = GlowPanel(self.state)
        gl = QVBoxLayout(guide_box)
        gl.setContentsMargins(12, 10, 12, 10)
        
        guide_text = (
            "🚀 <b>One-Click Auto-Train Flywheel:</b><br>"
            "This tab runs Karl's self-improvement flywheel completely autonomously:<br>"
            "1. <b>Synthesizer:</b> Generates synthetic problems for your custom behavior.<br>"
            "2. <b>Solver:</b> Attempts to solve the generated problems.<br>"
            "3. <b>Curator & Sandbox:</b> Verifies solutions in a secure execution sandbox.<br>"
            "4. <b>Self-Reflection:</b> Mistakes trigger an LLM-based debugging correction loop.<br>"
            "5. <b>Training:</b> Custom datasets are created, and SFT LoRA training begins."
        )
        guide_lbl = QLabel(guide_text)
        guide_lbl.setWordWrap(True)
        guide_lbl.setStyleSheet("font-size: 8.5pt; color: #00C2FF; line-height: 1.4;")
        gl.addWidget(guide_lbl)
        right_layout.addWidget(guide_box)

        # Output Logs
        log_box = QWidget()
        log_lay = QVBoxLayout(log_box)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.setSpacing(4)
        log_lay.addWidget(_section("FLYWHEEL AUTO-TRAIN LOGS"))
        self._auto_log = QTextBrowser()
        self._auto_log.setObjectName("reasoning-view")
        self._auto_log.setPlaceholderText("Logs will stream here when auto-training begins...")
        self._auto_log.setStyleSheet("font-family: monospace; font-size: 9pt;")
        log_lay.addWidget(self._auto_log)
        right_layout.addWidget(log_box, 1)

        layout.addWidget(right_col, 1)

    def _begin_auto_training(self):
        topic = self._auto_topic_input.text().strip()
        adapter_name = self._auto_adapter_input.text().strip()
        if not topic:
            self._auto_log.append("Please specify a target behavior/topic.")
            return
        if not adapter_name:
            self._auto_log.append("Please specify an adapter save name.")
            return

        # Sanitize adapter name for file path
        adapter_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', adapter_name)
        self._auto_adapter_input.setText(adapter_name)

        # Release VRAM first
        ModelLoader.reset_instance()

        self._auto_train_btn.setEnabled(False)
        self._auto_progress.setVisible(True)
        self._auto_progress.setRange(0, 0)  # Indeterminate progress bar
        self._auto_log.clear()
        self._auto_log.append("Starting automated flywheel training pipeline...")

        config = {
            "count": self._auto_count_spin.value(),
            "epochs": self._auto_epochs_spin.value(),
            "rank": self._auto_rank_spin.value(),
            "alpha": self._auto_alpha_spin.value(),
            "lr": self._auto_lr_spin.value(),
            "use_qlora": self._auto_qlora_check.isChecked()
        }

        self._auto_thread = AutoTrainThread(topic, adapter_name, config)
        self._active_threads.add(self._auto_thread)
        self._auto_thread.finished.connect(
            lambda t=self._auto_thread: self._active_threads.discard(t)
        )
        self._auto_thread.finished.connect(self._auto_thread.deleteLater)
        self._auto_thread.log.connect(self._on_auto_log)
        self._auto_thread.done.connect(self._on_auto_done)
        self._auto_thread.error.connect(self._on_auto_error)
        self._auto_thread.start()

    def _on_auto_log(self, text: str):
        self._auto_log.append(text)

    def _on_auto_done(self, adapter_name: str):
        self._auto_train_btn.setEnabled(True)
        self._auto_progress.setVisible(False)
        QMessageBox.information(
            self, "Auto-Training Complete",
            f"Auto-training completed successfully!\nAdapter GGUF ready: data/adapters/{adapter_name}/{adapter_name}.gguf"
        )
        self._auto_topic_input.clear()
        self._auto_adapter_input.clear()

    def _on_auto_error(self, msg: str):
        self._auto_train_btn.setEnabled(True)
        self._auto_progress.setVisible(False)
        self._auto_log.append(f"\n[ERROR] Auto-training failed: {msg}")
        QMessageBox.critical(self, "Auto-Training Error", f"Auto-training failed:\n{msg}")
