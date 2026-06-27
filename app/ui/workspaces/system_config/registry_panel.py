from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QMessageBox, QScrollArea, QProgressBar, QDialog,
)

from app.engine import config_store
from app.ui.themes import MONO
from .download_threads import DownloadThread, QuantizationDialog, QuantizationThread

logger = logging.getLogger("karl.system_config")

class RegistryPanelMixin:
    def _on_quant_done(self, out_path: str):
        self._quant_progress_bar.setValue(100)
        self._quant_progress_bar.setVisible(False)
        self._quant_btn.setEnabled(True)
        self._quant_cancel_btn.setEnabled(False)
        self._quantizer_thread = None
        self._scan_models(force=True)
        self._quant_status_lbl.setText(
            f"<span style='color:#2DD4A0;'>Done — {os.path.basename(out_path)} saved to data/models/</span>"
        )
        self._quant_status_lbl.setTextFormat(Qt.TextFormat.RichText)
        QMessageBox.information(
            self, "Quantization Complete",
            f"Quantized model saved:\n{out_path}"
        )


    def _build_registry_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("registry-scroll")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("registry-content")
        self._registry_layout = QVBoxLayout(scroll_content)
        self._registry_layout.setContentsMargins(0, 0, 0, 0)
        self._registry_layout.setSpacing(10)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        self._progress_panel = QWidget()
        self._progress_panel.setObjectName("panel")
        self._progress_panel.setVisible(False)
        p_layout = QHBoxLayout(self._progress_panel)
        p_layout.setContentsMargins(12, 8, 12, 8)
        p_layout.setSpacing(10)
        
        self._download_status_lbl = QLabel("Downloading...")
        p_layout.addWidget(self._download_status_lbl, 1)
        
        self._download_bar = QProgressBar()
        self._download_bar.setRange(0, 100)
        self._download_bar.setValue(0)
        self._download_bar.setFixedHeight(12)
        p_layout.addWidget(self._download_bar, 2)
        
        self._cancel_download_btn = QPushButton("Cancel")
        self._cancel_download_btn.setObjectName("btn-danger")
        self._cancel_download_btn.clicked.connect(self._cancel_download)
        p_layout.addWidget(self._cancel_download_btn)
        
        layout.addWidget(self._progress_panel)
        
        self._populate_registry()
        return w


    def _load_registry(self):
        self._registry = list(config_store.get_model_registry())

        if not self._registry:
            self._registry = [
                {
                    "tier": 1,
                    "name": "DeepSeek-R1-Distill-Qwen-1.5B Q4_K_M",
                    "filename": "deepseek-r1-1.5b.gguf",
                    "min_ram_gb": 3.0,
                    "min_vram_gb": 0.0,
                    "min_storage_gb": 1.5,
                    "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
                    "n_ctx": 4096
                },
                {
                    "tier": 2,
                    "name": "DeepSeek-R1-Distill-Qwen-7B Q4_K_M",
                    "filename": "deepseek-r1-7b.gguf",
                    "min_ram_gb": 8.0,
                    "min_vram_gb": 0.0,
                    "min_storage_gb": 5.0,
                    "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
                    "n_ctx": 8192
                },
                {
                    "tier": 2,
                    "name": "DeepSeek-R1-Distill-Llama-8B Q4_K_M",
                    "filename": "deepseek-r1-llama-8b.gguf",
                    "min_ram_gb": 8.0,
                    "min_vram_gb": 0.0,
                    "min_storage_gb": 5.5,
                    "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Llama-8B-GGUF/resolve/main/DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf",
                    "n_ctx": 8192
                },
                {
                    "tier": 3,
                    "name": "DeepSeek-R1-Distill-Qwen-14B Q4_K_M",
                    "filename": "deepseek-r1-14b.gguf",
                    "min_ram_gb": 16.0,
                    "min_vram_gb": 0.0,
                    "min_storage_gb": 10.0,
                    "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
                    "n_ctx": 16384
                },
                {
                    "tier": 4,
                    "name": "DeepSeek-R1-Distill-Llama-70B Q4_K_M",
                    "filename": "deepseek-r1-70b.gguf",
                    "min_ram_gb": 48.0,
                    "min_vram_gb": 0.0,
                    "min_storage_gb": 42.0,
                    "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF/resolve/main/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf",
                    "n_ctx": 32768
                }
            ]


    def _get_active_model_name(self) -> str:
        active_name = self.state.model_name or "none"
        if active_name == "none":
            from app.engine import config_store
            data = config_store.read_json(config_store.ACTIVE_MODEL_PATH, default=None)
            if isinstance(data, dict):
                active_name = data.get("filename") or "none"
        return active_name


    def _populate_registry(self):
        while self._registry_layout.count():
            item = self._registry_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
                
        active_name = self._get_active_model_name()
        models_dir = "data/models"
        
        for item in self._registry:
            tier = item.get("tier", 1)
            name = item.get("name", "Unknown")
            filename = item.get("filename", "")
            n_ctx = item.get("n_ctx", 4096)
            min_ram = item.get("min_ram_gb", 3.0)
            min_storage = item.get("min_storage_gb", 1.5)
            url = item.get("url", "")
            
            card = QWidget()
            card.setObjectName("panel")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 12, 12, 12)
            c_layout.setSpacing(6)
            
            header = QWidget()
            h_layout = QHBoxLayout(header)
            h_layout.setContentsMargins(0, 0, 0, 0)
            lbl_title = QLabel(f"Tier {tier}: {name}")
            lbl_title.setObjectName("lbl-accent")
            lbl_title.setStyleSheet("font-weight: bold; font-size: 10.5pt;")
            h_layout.addWidget(lbl_title, 1)
            
            file_path = os.path.join(models_dir, filename)
            is_downloaded = os.path.exists(file_path)
            is_active = (filename == active_name)
            
            btn = QPushButton()
            quant_btn = None
            
            if is_active:
                btn.setText("Active")
                btn.setEnabled(False)
                btn.setStyleSheet("background-color: rgba(45, 212, 160, 0.15); color: #2DD4A0; border: 1px solid rgba(45, 212, 160, 0.4); border-radius: 4px; font-weight: bold; padding: 5px 14px;")
            elif is_downloaded:
                btn.setText("Activate")
                btn.clicked.connect(lambda checked, f=filename: self._activate_registry_model(f))
                btn.setStyleSheet("background-color: rgba(0, 194, 255, 0.1); color: #00C2FF; border: 1px solid rgba(0, 194, 255, 0.35); border-radius: 4px; padding: 5px 14px;")
                
                # If downloaded and precision is FP16, add Quantize button
                # We'll infer FP16 if 'FP16' is in the name or filename
                if "FP16" in name.upper() or "FP16" in filename.upper() or item.get("precision") == "FP16":
                    quant_btn = QPushButton("Quantize")
                    quant_btn.setStyleSheet("background-color: rgba(240, 176, 48, 0.1); color: #F0B030; border: 1px solid rgba(240, 176, 48, 0.35); border-radius: 4px; padding: 5px 14px;")
                    quant_btn.clicked.connect(lambda checked, f=filename, n=name: self._on_quantize_clicked(f, n))
            else:
                btn.setText("Download")
                btn.setObjectName("btn-primary")
                btn.setStyleSheet("padding: 5px 14px;")
                btn.clicked.connect(lambda checked, u=url, f=filename: self._start_download(u, f))
                
            if quant_btn:
                h_layout.addWidget(quant_btn)
            h_layout.addWidget(btn)
            c_layout.addWidget(header)
            
            meta = QLabel(
                f"Context size: <b>{n_ctx:,}</b> tokens &middot; "
                f"RAM: <b>&ge; {min_ram} GB</b> &middot; "
                f"Storage: <b>&ge; {min_storage} GB</b> &middot; "
                f"Filename: <span style='font-family:{MONO}; font-size:8.5pt;'>{filename}</span>"
            )
            meta.setObjectName("lbl-muted")
            meta.setWordWrap(True)
            meta.setTextFormat(Qt.TextFormat.RichText)
            c_layout.addWidget(meta)
            
            self._registry_layout.addWidget(card)
            
        self._registry_layout.addStretch(1)


    def _on_quantize_clicked(self, filename: str, model_name: str):
        src_path = os.path.join("data", "models", filename)
        
        dialog = QuantizationDialog(model_name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fmt = dialog.selected_format()
            
            # Suggest output name: model-name-Q4_K_M.gguf
            base = os.path.splitext(filename)[0]
            out_filename = f"{base}-{fmt}.gguf"
            out_path = os.path.join("data", "models", out_filename)
            
            # Show progress overlay in the registry tab
            self._progress_panel.setVisible(True)
            self._download_status_lbl.setText("Compiling custom GGUF weights...")
            self._download_bar.setValue(0)
            self._set_ui_enabled_for_download(False)
            
            thread = QuantizationThread(src_path, out_path, fmt)
            self._active_threads.add(thread)
            thread.finished.connect(lambda: self._active_threads.discard(thread))
            thread.finished.connect(thread.deleteLater)
            
            thread.progress.connect(self._on_download_progress)
            thread.log.connect(self._on_download_log)
            thread.done.connect(lambda p: self._on_quant_done(p))
            thread.error.connect(self._on_download_error)
            
            thread.start()


    def _on_quant_done(self, output_path: str):
        self._progress_panel.setVisible(False)
        self._set_ui_enabled_for_download(True)
        filename = os.path.basename(output_path)
        
        # Refresh UI
        self._scan_models(force=True)
        self._populate_registry()
        
        QMessageBox.information(
            self, "Quantization Complete",
            f"Successfully compiled weights to:\n{filename}\n\nYou can now activate this optimized model."
        )


    def _activate_registry_model(self, filename: str):
        from app.engine.model_loader import ModelLoader
        if ModelLoader.is_instance_locked():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Karl — Inference Active",
                "Cannot switch model while inference is active.\n"
                "Stop the current generation first.",
            )
            return
        ModelLoader.reset_instance()
        try:
            path = os.path.join("data", "models", filename)
            ModelLoader.get_instance(model_path=path)
            self.state.model_name = filename

            from app.engine import config_store
            if not config_store.set_active_model(filename):
                raise OSError("Failed to persist data/active_model.json")

            self._scan_models(force=True)
            self._populate_registry()
            
            self._model_path_input.setText(path)
            self._run_model_preflight_checks()
            
            QMessageBox.information(
                self, "Model Activated",
                f"Model '{filename}' has been activated successfully!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Activation Error", f"Failed to activate model: {e}")


    def _start_download(self, url: str, filename: str):
        if self._download_thread and self._download_thread.isRunning():
            QMessageBox.warning(self, "Download In Progress", "A download is already running.")
            return
            
        target_path = os.path.join("data", "models", filename)
        
        self._progress_panel.setVisible(True)
        self._download_status_lbl.setText(f"Downloading {filename}...")
        self._download_bar.setValue(0)
        self._set_ui_enabled_for_download(False)
        
        self._download_thread = DownloadThread(url, target_path)
        self._active_threads.add(self._download_thread)
        self._download_thread.finished.connect(
            lambda t=self._download_thread: self._active_threads.discard(t)
        )
        self._download_thread.finished.connect(self._download_thread.deleteLater)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.speed.connect(self._on_download_speed)
        self._download_thread.done.connect(lambda: self._on_download_done(filename))
        self._download_thread.error.connect(self._on_download_error)
        self._download_thread.log.connect(self._on_download_log)
        self._download_thread.start()


    def _cancel_download(self):
        if self._download_thread and self._download_thread.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Download", "Are you sure you want to cancel the download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._download_thread.cancel()


    def _set_ui_enabled_for_download(self, enabled: bool):
        for i in range(self._registry_layout.count()):
            item = self._registry_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                for btn in card.findChildren(QPushButton):
                    if btn.text() != "Active":
                        btn.setEnabled(enabled)


    def _on_download_progress(self, percent: int):
        self._download_bar.setValue(percent)


    def _on_download_speed(self, speed_str: str):
        status_text = self._download_status_lbl.text().split(" (")[0]
        self._download_status_lbl.setText(f"{status_text} ({speed_str})")


    def _on_download_log(self, text: str):
        self._download_status_lbl.setText(f"{text}")


    def _on_download_error(self, err_msg: str):
        self._progress_panel.setVisible(False)
        self._set_ui_enabled_for_download(True)
        QMessageBox.critical(self, "Download Error", f"An error occurred during download:\n{err_msg}")
        self._download_thread = None


    def _on_download_done(self, filename: str):
        self._progress_panel.setVisible(False)
        self._set_ui_enabled_for_download(True)
        self._activate_registry_model(filename)
        self._download_thread = None

    # ── defaults tab ──────────────────────────────────────────────────────────

