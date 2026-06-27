import os
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox
)
from app.ui.widgets.glow_panel import GlowPanel

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section-header")
    return lbl


class ExportTab(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        cards = QWidget()
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)

        # SFT Panel
        sft_box = GlowPanel(self.state)
        sft_l = QVBoxLayout(sft_box)
        sft_l.setContentsMargins(16, 16, 16, 16)
        sft_l.setSpacing(12)
        sft_l.addWidget(_section("UNSLOTH / SFT FORMAT"))
        sft_desc = QLabel(
            "Exports curated examples in Unsloth-compatible JSONL format. "
            "Includes instruction-following message traces ideal for Supervised Fine-Tuning (SFT)."
        )
        sft_desc.setObjectName("lbl-muted")
        sft_desc.setWordWrap(True)
        sft_l.addWidget(sft_desc)
        sft_l.addStretch()
        sft_btn = QPushButton("export SFT  →  unsloth_sft.jsonl")
        sft_btn.setObjectName("btn-primary")
        sft_btn.setToolTip("Export curated dataset in Unsloth SFT chat format")
        sft_btn.clicked.connect(lambda: self._export("sft"))
        sft_l.addWidget(sft_btn)
        cards_layout.addWidget(sft_box, 1)

        # DPO Panel
        dpo_box = GlowPanel(self.state)
        dpo_l = QVBoxLayout(dpo_box)
        dpo_l.setContentsMargins(16, 16, 16, 16)
        dpo_l.setSpacing(12)
        dpo_l.addWidget(_section("DPO FORMAT"))
        dpo_desc = QLabel(
            "Exports paired chosen (thumbs-up) vs rejected (thumbs-down) examples. "
            "Requires at least one positive and one negative sample to construct comparison pairs."
        )
        dpo_desc.setObjectName("lbl-muted")
        dpo_desc.setWordWrap(True)
        dpo_l.addWidget(dpo_desc)
        dpo_l.addStretch()
        dpo_btn = QPushButton("export DPO  →  unsloth_dpo.jsonl")
        dpo_btn.setToolTip("Export paired chosen/rejected examples in DPO format")
        dpo_btn.clicked.connect(lambda: self._export("dpo"))
        dpo_l.addWidget(dpo_btn)
        cards_layout.addWidget(dpo_box, 1)

        layout.addWidget(cards, 1)

        self._export_status = QLabel("")
        self._export_status.setObjectName("lbl-mid")
        self._export_status.setWordWrap(True)
        layout.addWidget(self._export_status)

    def _export(self, mode: str):
        # Validation preflight
        curated_file = "data/training/curated.jsonl"
        if not os.path.exists(curated_file) or os.path.getsize(curated_file) == 0:
            QMessageBox.warning(self, "Validation Failed", "The dataset is empty. Curate some examples first.")
            return
            
        try:
            with open(curated_file, "r") as f:
                for line_idx, line in enumerate(f):
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    if "messages" not in obj and "prompt" not in obj:
                        raise ValueError(f"Line {line_idx+1}: Missing both 'messages' and 'prompt' keys.")
        except Exception as e:
            QMessageBox.critical(self, "Dataset Validation Error", f"curated.jsonl format validation failed:\n{e}")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save export", f"unsloth_{mode}.jsonl", "JSONL (*.jsonl)"
        )
        if not path:
            return
        try:
            if mode == "sft":
                out_path = self.state.curator.export_unsloth(path)
                count = sum(1 for line in open(out_path, "r", encoding="utf-8"))
                self._export_status.setText(f"saved {count} SFT examples: {out_path}")
            else:
                out_path = self.state.curator.export_dpo(path)
                count = sum(1 for line in open(out_path, "r", encoding="utf-8"))
                self._export_status.setText(f"saved {count} DPO pairs: {out_path}")
        except Exception as e:
            self._export_status.setText(f"error: {e}")
