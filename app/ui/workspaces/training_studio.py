"""
Training Studio — curated dataset management and LoRA/QLoRA export.

Tabs:
  Dataset   — browse, filter, delete curated examples
  Export    — export to Unsloth SFT / DPO format
  Train     — configure and run LoRA / QLoRA (requires peft + trl)
"""

from __future__ import annotations

import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTextBrowser, QLabel, QListWidget,
    QListWidgetItem, QFrame, QFileDialog, QMessageBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit,
    QProgressBar, QCheckBox,
)
from PyQt6.QtCore import Qt


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class TrainingStudioWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title_row = QWidget()
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Training Studio")
        lbl.setObjectName("lbl-accent")
        tr.addWidget(lbl)
        tr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("lbl-muted")
        tr.addWidget(self._stats_lbl)
        root.addWidget(title_row)

        tabs = QTabWidget()
        tabs.addTab(self._build_dataset_tab(), "Dataset")
        tabs.addTab(self._build_export_tab(), "Export")
        tabs.addTab(self._build_train_tab(), "Train")
        root.addWidget(tabs, 1)

        self._refresh()

    # ── dataset tab ──────────────────────────────────────────────────────────

    def _build_dataset_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        ll.addWidget(_section("EXAMPLES"))

        self._example_list = QListWidget()
        self._example_list.currentRowChanged.connect(self._on_example_selected)
        ll.addWidget(self._example_list, 1)

        del_btn = QPushButton("delete selected")
        del_btn.setObjectName("btn-danger")
        del_btn.clicked.connect(self._delete_selected)
        ll.addWidget(del_btn)

        layout.addWidget(left, 1)

        # detail
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        rl.addWidget(_section("PREVIEW"))

        self._detail_view = QTextBrowser()
        self._detail_view.setPlaceholderText("Select an example to preview.")
        rl.addWidget(self._detail_view, 1)

        layout.addWidget(right, 2)
        return w

    # ── export tab ────────────────────────────────────────────────────────────

    def _build_export_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(_section("UNSLOTH / SFT FORMAT"))
        layout.addWidget(QLabel(
            "Exports curated examples in Unsloth-compatible JSONL.\n"
            "Fields: instruction, input, output, source, timestamp."
        ))

        sft_btn = QPushButton("export SFT  →  unsloth_sft.jsonl")
        sft_btn.setObjectName("btn-primary")
        sft_btn.clicked.connect(lambda: self._export("sft"))
        layout.addWidget(sft_btn)

        layout.addWidget(_hline())
        layout.addWidget(_section("DPO FORMAT"))
        layout.addWidget(QLabel(
            "Exports thumbs-up (chosen) vs thumbs-down (rejected) pairs.\n"
            "Requires at least one example of each type."
        ))

        dpo_btn = QPushButton("export DPO  →  unsloth_dpo.jsonl")
        dpo_btn.setObjectName("btn-primary")
        dpo_btn.clicked.connect(lambda: self._export("dpo"))
        layout.addWidget(dpo_btn)

        layout.addStretch()
        self._export_status = QLabel("")
        self._export_status.setObjectName("lbl-mid")
        self._export_status.setWordWrap(True)
        layout.addWidget(self._export_status)

        return w

    # ── train tab ─────────────────────────────────────────────────────────────

    def _build_train_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # dependency check
        self._deps_lbl = QLabel("")
        self._deps_lbl.setObjectName("lbl-muted")
        self._deps_lbl.setWordWrap(True)
        layout.addWidget(self._deps_lbl)
        self._check_deps()

        layout.addWidget(_hline())
        layout.addWidget(_section("LORA CONFIG"))

        # config grid
        cfg = QWidget()
        cfg_l = QHBoxLayout(cfg)
        cfg_l.setContentsMargins(0, 0, 0, 0)
        cfg_l.setSpacing(20)

        def _row(label: str, widget: QWidget) -> QWidget:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            rl.addWidget(QLabel(label))
            rl.addWidget(widget)
            rl.addStretch()
            return row

        self._rank_spin = QSpinBox()
        self._rank_spin.setRange(1, 256)
        self._rank_spin.setValue(16)
        self._rank_spin.setFixedWidth(80)

        self._alpha_spin = QSpinBox()
        self._alpha_spin.setRange(1, 512)
        self._alpha_spin.setValue(32)
        self._alpha_spin.setFixedWidth(80)

        self._dropout_spin = QDoubleSpinBox()
        self._dropout_spin.setRange(0.0, 0.5)
        self._dropout_spin.setSingleStep(0.05)
        self._dropout_spin.setValue(0.05)
        self._dropout_spin.setFixedWidth(80)

        self._lr_spin = QDoubleSpinBox()
        self._lr_spin.setDecimals(6)
        self._lr_spin.setRange(1e-6, 1e-2)
        self._lr_spin.setSingleStep(1e-5)
        self._lr_spin.setValue(2e-4)
        self._lr_spin.setFixedWidth(100)

        self._epochs_spin = QSpinBox()
        self._epochs_spin.setRange(1, 20)
        self._epochs_spin.setValue(3)
        self._epochs_spin.setFixedWidth(80)

        self._qlora_check = QCheckBox("4-bit QLoRA  (requires bitsandbytes)")
        self._qlora_check.setChecked(False)

        for row in (
            _row("rank",    self._rank_spin),
            _row("alpha",   self._alpha_spin),
            _row("dropout", self._dropout_spin),
            _row("lr",      self._lr_spin),
            _row("epochs",  self._epochs_spin),
        ):
            layout.addWidget(row)

        layout.addWidget(self._qlora_check)
        layout.addWidget(_hline())

        self._adapter_name_input = QLineEdit()
        self._adapter_name_input.setPlaceholderText("adapter name (saved to data/adapters/)")
        layout.addWidget(self._adapter_name_input)

        self._train_btn = QPushButton("▶ begin training")
        self._train_btn.setObjectName("btn-primary")
        self._train_btn.clicked.connect(self._begin_training)
        layout.addWidget(self._train_btn)

        self._train_progress = QProgressBar()
        self._train_progress.setVisible(False)
        layout.addWidget(self._train_progress)

        self._train_log = QTextBrowser()
        self._train_log.setFixedHeight(120)
        self._train_log.setPlaceholderText("training log...")
        layout.addWidget(self._train_log)

        layout.addStretch()
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _refresh(self):
        stats = self.state.curator.get_stats()
        self._stats_lbl.setText(
            f"{stats['total']} examples  ·  "
            f"{stats['thumbs_up']} good  ·  "
            f"{stats['corrected']} corrected"
        )
        self._example_list.clear()
        for ex in self.state.curator.get_all_examples():
            source = ex.get("source", "unknown")
            preview = ex.get("instruction", "")[:60]
            item = QListWidgetItem(f"[{source}]  {preview}")
            self._example_list.addItem(item)

    def _on_example_selected(self, row: int):
        if row < 0:
            return
        examples = self.state.curator.get_all_examples()
        if row >= len(examples):
            return
        ex = examples[row]
        self._detail_view.setPlainText(json.dumps(ex, indent=2, ensure_ascii=False))

    def _delete_selected(self):
        row = self._example_list.currentRow()
        if row < 0:
            return
        reply = QMessageBox.question(
            self, "Delete example", "Delete this example?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.state.curator.delete_example(row)
            self._refresh()

    def _export(self, mode: str):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save export", f"unsloth_{mode}.jsonl", "JSONL (*.jsonl)"
        )
        if not path:
            return
        try:
            if mode == "sft":
                out_path = self.state.curator.export_unsloth(path)
            else:
                out_path = self._export_dpo(path)
            self._export_status.setText(f"saved: {out_path}")
        except Exception as e:
            self._export_status.setText(f"error: {e}")

    def _export_dpo(self, path: str) -> str:
        examples = self.state.curator.get_all_examples()
        chosen   = [e for e in examples if e.get("source") == "thumbs_up"]
        rejected = [e for e in examples if e.get("source") == "thumbs_down"]

        pairs = []
        for c, r in zip(chosen, rejected):
            pairs.append({
                "prompt":   c.get("instruction", ""),
                "chosen":   c.get("output", ""),
                "rejected": r.get("output", ""),
            })

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for p in pairs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        return path

    def _check_deps(self):
        missing = []
        for pkg in ("peft", "trl", "transformers"):
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if missing:
            self._deps_lbl.setText(
                f"In-app training requires: {', '.join(missing)}\n"
                f"Install with:  pip install {' '.join(missing)}"
            )
            self._deps_lbl.setObjectName("lbl-red")
        else:
            self._deps_lbl.setText("✓ training dependencies available")
            self._deps_lbl.setObjectName("lbl-green")

    def _begin_training(self):
        try:
            import peft  # noqa
            import trl   # noqa
        except ImportError:
            self._train_log.append("install peft and trl before training.")
            return

        adapter_name = self._adapter_name_input.text().strip()
        if not adapter_name:
            self._train_log.append("set an adapter name first.")
            return

        examples = self.state.curator.get_all_examples()
        if len(examples) < 5:
            self._train_log.append(
                f"need at least 5 examples (have {len(examples)}). "
                "curate more in the workbench."
            )
            return

        self._train_log.append(
            f"training with {len(examples)} examples · "
            f"rank={self._rank_spin.value()} · "
            f"alpha={self._alpha_spin.value()} · "
            f"lr={self._lr_spin.value():.2e} · "
            f"epochs={self._epochs_spin.value()}"
        )
        self._train_log.append(
            "NOTE: in-app LoRA training requires the HuggingFace model weights, "
            "not just the GGUF file. Place the HF model in data/hf_models/ and "
            "this will be implemented in the next release."
        )
