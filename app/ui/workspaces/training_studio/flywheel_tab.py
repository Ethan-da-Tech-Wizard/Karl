import os
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QTextBrowser, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.workspaces.training_studio.threads import _FlywheelStatsThread

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section-header")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class FlywheelTab(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._active_threads = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header_row = QWidget()
        hl = QHBoxLayout(header_row)
        hl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Self-Improvement Flywheel")
        lbl.setObjectName("lbl-accent")
        hl.addWidget(lbl)
        hl.addStretch()
        self._flywheel_refresh_btn = QPushButton("Refresh")
        self._flywheel_refresh_btn.setObjectName("btn-ghost")
        self._flywheel_refresh_btn.clicked.connect(self.load_stats)
        hl.addWidget(self._flywheel_refresh_btn)
        layout.addWidget(header_row)

        pipeline_lbl = QLabel(
            "Interactions  →  Feedback  →  Training Data  →  Eval Score  →  Export"
        )
        pipeline_lbl.setObjectName("lbl-muted")
        pipeline_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pipeline_lbl)

        # Cards row
        cards = QWidget()
        cl = QHBoxLayout(cards)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)

        self._fw_interactions = self._flywheel_card(
            "Interactions", ["traces_total", "sessions_saved", "last_session"]
        )
        self._fw_feedback = self._flywheel_card(
            "Feedback", ["thumbs_up", "thumbs_down", "corrections"]
        )
        self._fw_data = self._flywheel_card(
            "Training Data", ["sft_examples", "dpo_pairs", "last_export"]
        )
        # Add SFT and DPO export buttons directly inside the Training Data card
        btn_lay_data = QHBoxLayout()
        btn_lay_data.setSpacing(6)
        card_export_sft = QPushButton("Export SFT")
        card_export_sft.setObjectName("btn-primary")
        card_export_sft.clicked.connect(self._flywheel_export_sft)
        card_export_dpo = QPushButton("Export DPO")
        card_export_dpo.setObjectName("btn-secondary")
        card_export_dpo.clicked.connect(self._flywheel_export_dpo)
        btn_lay_data.addWidget(card_export_sft)
        btn_lay_data.addWidget(card_export_dpo)
        self._fw_data.layout().insertLayout(self._fw_data.layout().count() - 1, btn_lay_data)

        self._fw_eval = self._flywheel_card(
            "Eval Score", ["eval_score", "eval_dataset", "eval_date"]
        )
        # Add Run Eval button inside the Eval Score card
        btn_lay_eval = QHBoxLayout()
        card_run_eval = QPushButton("Run Eval")
        card_run_eval.setObjectName("btn-primary")
        card_run_eval.clicked.connect(self._flywheel_goto_eval)
        btn_lay_eval.addWidget(card_run_eval)
        self._fw_eval.layout().insertLayout(self._fw_eval.layout().count() - 1, btn_lay_eval)

        # Export & Preview Card
        self._fw_export_card = QFrame()
        self._fw_export_card.setObjectName("panel")
        ec_lay = QVBoxLayout(self._fw_export_card)
        ec_lay.setContentsMargins(10, 10, 10, 10)
        ec_lay.setSpacing(6)

        export_title = QLabel("EXPORT & PREVIEW")
        export_title.setObjectName("section-header")
        ec_lay.addWidget(export_title)
        ec_lay.addWidget(_hline())

        open_folder_btn = QPushButton("Open training folder")
        open_folder_btn.setObjectName("btn-primary")
        open_folder_btn.clicked.connect(self._open_training_folder)
        ec_lay.addWidget(open_folder_btn)

        preview_title = QLabel("Last Export Preview:")
        preview_title.setObjectName("lbl-muted")
        preview_title.setStyleSheet("font-size: 8pt; font-weight: bold;")
        ec_lay.addWidget(preview_title)

        self._sft_preview = QTextBrowser()
        preview_font = QFont("Monospace")
        preview_font.setPointSizeF(8.5)
        self._sft_preview.setFont(preview_font)
        self._sft_preview.setStyleSheet("background-color: #0E0F15; border: 1px solid #1A1A24;")
        self._sft_preview.setPlaceholderText("No recent SFT exports found.")
        ec_lay.addWidget(self._sft_preview, 1)

        for card in (self._fw_interactions, self._fw_feedback, self._fw_data, self._fw_eval, self._fw_export_card):
            cl.addWidget(card, 1)

        layout.addWidget(cards)

        self._fw_status_lbl = QLabel("")
        self._fw_status_lbl.setObjectName("lbl-muted")
        layout.addWidget(self._fw_status_lbl)

        layout.addStretch()

    def _flywheel_card(self, title: str, field_ids: list) -> QWidget:
        card = QFrame()
        card.setObjectName("panel")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(6)

        title_lbl = QLabel(title.upper())
        title_lbl.setObjectName("section-header")
        cl.addWidget(title_lbl)
        cl.addWidget(_hline())

        self._fw_fields = getattr(self, "_fw_fields", {})
        for fid in field_ids:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(4)
            name_lbl = QLabel(fid.replace("_", " ").title() + ":")
            name_lbl.setObjectName("lbl-muted")
            name_lbl.setFixedWidth(100)
            val_lbl = QLabel("—")
            val_lbl.setObjectName("lbl-accent" if fid in ("traces_total", "thumbs_up", "sft_examples", "eval_score") else "")
            rl.addWidget(name_lbl)
            rl.addWidget(val_lbl, 1)
            cl.addWidget(row)
            self._fw_fields[fid] = val_lbl

        cl.addStretch()
        return card

    def load_stats(self):
        self._fw_status_lbl.setText("Loading stats...")
        self._flywheel_refresh_btn.setEnabled(False)
        t = _FlywheelStatsThread()
        t.stats_ready.connect(self._apply_flywheel_stats)
        t.finished.connect(lambda: self._flywheel_refresh_btn.setEnabled(True))
        t.finished.connect(t.deleteLater)
        self._active_threads.add(t)
        t.finished.connect(lambda: self._active_threads.discard(t))
        t.start()

    def _apply_flywheel_stats(self, stats: dict):
        fields = getattr(self, "_fw_fields", {})
        for fid, val in stats.items():
            if fid in fields:
                fields[fid].setText(str(val))

        # Apply preview content
        if "last_sft_content" in stats:
            self._sft_preview.setPlainText(stats["last_sft_content"])

        self._fw_status_lbl.setText("Stats loaded.")

    def _flywheel_export_sft(self):
        self._export("sft")
        self.load_stats()

    def _flywheel_export_dpo(self):
        self._export("dpo")
        self.load_stats()

    def _open_training_folder(self):
        import subprocess
        try:
            path = os.path.abspath("data/training")
            os.makedirs(path, exist_ok=True)
            subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open folder: {e}")

    def _flywheel_goto_eval(self):
        try:
            main_win = self.window()
            if hasattr(main_win, "_sidebar"):
                main_win._sidebar.select(5)
        except Exception:
            pass

    def _export(self, mode: str):
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
                QMessageBox.information(self, "Export Successful", f"Saved {count} SFT examples to:\n{out_path}")
            else:
                out_path = self.state.curator.export_dpo(path)
                count = sum(1 for line in open(out_path, "r", encoding="utf-8"))
                QMessageBox.information(self, "Export Successful", f"Saved {count} DPO pairs to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")
