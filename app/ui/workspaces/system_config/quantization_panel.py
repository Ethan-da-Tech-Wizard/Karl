from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)

from app.engine.quantizer_thread import QuantizerThread

logger = logging.getLogger("karl.system_config")

class QuantizationPanelMixin:
    def _browse_quant_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select source GGUF", "data/models", "GGUF (*.gguf);;All Files (*)"
        )
        if path:
            self._quant_src_input.setText(path)
            # Auto-suggest output filename if field is empty
            if not self._quant_out_input.text().strip():
                base = os.path.splitext(os.path.basename(path))[0]
                fmt  = self._quant_format_combo.currentText()
                self._quant_out_input.setText(f"{base}-{fmt}.gguf")



    def _start_quantize(self):
        if self._quantizer_thread and self._quantizer_thread.isRunning():
            QMessageBox.warning(self, "Quantization Running", "A quantization job is already in progress.")
            return

        src = self._quant_src_input.text().strip()
        out_name = self._quant_out_input.text().strip()
        fmt = self._quant_format_combo.currentText()

        if not src:
            QMessageBox.warning(self, "Missing Input", "Select a source GGUF file first.")
            return
        if not os.path.isfile(src):
            QMessageBox.warning(self, "File Not Found", f"Source file not found:\n{src}")
            return
        if not out_name:
            QMessageBox.warning(self, "Missing Output", "Enter an output filename.")
            return

        # Resolve output to data/models/ if a bare filename was given
        if not os.path.dirname(out_name):
            out_path = os.path.join("data", "models", out_name)
        else:
            out_path = out_name

        self._quant_status_lbl.setText(f"Starting {fmt} quantization…")
        self._quant_progress_bar.setValue(0)
        self._quant_progress_bar.setVisible(True)
        self._quant_btn.setEnabled(False)
        self._quant_cancel_btn.setEnabled(True)

        self._quantizer_thread = QuantizerThread(
            input_path=src,
            output_path=out_path,
            target_format=fmt,
        )
        self._active_threads.add(self._quantizer_thread)
        self._quantizer_thread.finished.connect(
            lambda t=self._quantizer_thread: self._active_threads.discard(t)
        )
        self._quantizer_thread.finished.connect(self._quantizer_thread.deleteLater)
        self._quantizer_thread.progress.connect(self._on_quant_progress)
        self._quantizer_thread.done.connect(self._on_quant_done)
        self._quantizer_thread.error.connect(self._on_quant_error)
        self._quantizer_thread.start()



    def _cancel_quantize(self):
        if self._quantizer_thread and self._quantizer_thread.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Quantization",
                "Cancel the running quantization job?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._quantizer_thread.cancel()
                self._quant_status_lbl.setText("Cancellation requested…")



    def _on_quant_progress(self, pct: int):
        self._quant_progress_bar.setValue(pct)
        self._quant_status_lbl.setText(f"Quantizing… {pct}%")



    def _on_quant_error(self, msg: str):
        self._quant_progress_bar.setVisible(False)
        self._quant_btn.setEnabled(True)
        self._quant_cancel_btn.setEnabled(False)
        self._quantizer_thread = None
        self._quant_status_lbl.setText(
            f"<span style='color:#FF5C7A;'>Error: {msg[:120]}</span>"
        )
        self._quant_status_lbl.setTextFormat(Qt.TextFormat.RichText)
        QMessageBox.critical(self, "Quantization Failed", msg)

    # ── registry tab ──────────────────────────────────────────────────────────


