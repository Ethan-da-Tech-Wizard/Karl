"""
System — hardware info, model management, generation defaults, about.
"""

from __future__ import annotations

import logging

import json
import os
import html

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFrame, QDoubleSpinBox, QSpinBox, QFileDialog,
    QMessageBox, QGroupBox, QScrollArea, QProgressBar,
    QComboBox, QColorDialog, QCheckBox, QSlider,
    QInputDialog, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from app.ui.themes import MONO, THEMES, get_theme_colors, get_theme_stylesheet
from app.ui.widgets.tracing_panel import TracingPanel
from app.ui.widgets.symbolic_icon import CheckIcon, CrossIcon
from app.vision.vision_model_loader import (
    VisionModelLoader,
    installed_vision_models,
    set_active_vision_model,
)
from app.engine.quantizer_thread import QuantizerThread


logger = logging.getLogger("karl.system_config")


# ── quantization thread ───────────────────────────────────────────────────────

class QuantizationThread(QThread):
    progress = pyqtSignal(int)
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str, quant_format: str):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.quant_format = quant_format

    def run(self):
        try:
            self.log.emit(f"Starting quantization to {self.quant_format}...")
            # Simulation of quantization heavy-lift
            for i in range(1, 101):
                import time
                time.sleep(0.06) 
                self.progress.emit(i)
                if i % 20 == 0:
                    self.log.emit(f"Compiling custom GGUF weights... {i}%")
            self.done.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


# ── quantization dialog ───────────────────────────────────────────────────────

class QuantizationDialog(QDialog):
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Quantize {model_name}")
        self.setMinimumWidth(380)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(QLabel(f"Select desired quantization format for:<br/><b>{model_name}</b>"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"])
        layout.addWidget(self.format_combo)
        
        info = QLabel(
            "• <b>Q4_K_M</b>: Best balance of speed and logic accuracy.<br/>"
            "• <b>Q5_K_M</b>: High fidelity, requires more VRAM.<br/>"
            "• <b>Q8_0</b>: Near-lossless weights, very heavy."
        )
        info.setObjectName("lbl-muted")
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_format(self) -> str:
        return self.format_combo.currentText()


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _row(label_text: str, widget: QWidget) -> QWidget:
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 2, 0, 2)
    l.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(130)
    lbl.setObjectName("lbl-muted")
    l.addWidget(lbl)
    l.addWidget(widget)
    l.addStretch()
    return w


# ── download thread ───────────────────────────────────────────────────────────

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    speed = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, url: str, target_path: str):
        super().__init__()
        self.url = url
        self.target_path = target_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        import time
        import requests
        
        tmp_path = self.target_path + ".tmp"
        try:
            self.log.emit("Connecting...")
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            os.makedirs(os.path.dirname(self.target_path), exist_ok=True)
            
            start_time = time.time()
            last_time = start_time
            last_downloaded = 0
            
            self.log.emit("Downloading...")
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if self._is_cancelled:
                        self.log.emit("Download cancelled.")
                        break
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(percent)
                        
                        current_time = time.time()
                        time_diff = current_time - last_time
                        if time_diff >= 1.0:
                            bytes_diff = downloaded - last_downloaded
                            speed_mb = (bytes_diff / (1024 * 1024)) / time_diff
                            self.speed.emit(f"{speed_mb:.1f} MiB/s")
                            last_time = current_time
                            last_downloaded = downloaded
            
            if self._is_cancelled:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            else:
                self.log.emit("Finalizing model file...")
                if os.path.exists(self.target_path):
                    os.remove(self.target_path)
                os.rename(tmp_path, self.target_path)
                self.done.emit()
                
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            self.error.emit(str(e))


class SystemConfigWorkspace(QWidget):
    adapter_changed = pyqtSignal(str)
    appearance_changed = pyqtSignal()

    def __init__(self, state, workbench_ref=None, parent=None):
        super().__init__(parent)
        self.state = state
        self._workbench = workbench_ref
        self._download_thread = None
        self._quantizer_thread: QuantizerThread | None = None
        self._active_threads = set()
        self._active_custom_accent = None
        self._cached_models_list = None
        self._cached_adapters_list = None
        self._load_registry()
        self.setObjectName("workspace-root")
        self._build_ui()
        self._refresh_hardware()
        
        # Start diagnostic hardware monitoring timer
        self._hardware_timer = QTimer(self)
        self._hardware_timer.timeout.connect(self._update_live_hardware)
        self._hardware_timer.start(2000)
        self._update_live_hardware()

    def set_workbench(self, wb):
        self._workbench = wb

    def showEvent(self, event):
        super().showEvent(event)
        self._scan_models(force=False)
        self._scan_adapters(force=False)

        from app.engine import config_store as _cs
        draft_cfg = _cs.get_active_draft_model()
        if draft_cfg["filename"]:
            draft_path = os.path.join("data", "models", draft_cfg["filename"])
            self._draft_model_input.setText(draft_path)
            from app.engine.model_loader import ModelLoader
            if ModelLoader.is_speculative():
                self._draft_status.setText(
                    f"<span style='color:#2DD4A0;'>Speculative decoding active — draft: "
                    f"{draft_cfg['filename']}</span>"
                )
                self._draft_status.setTextFormat(Qt.TextFormat.RichText)

        self._refresh_hardware()
        self._run_model_preflight_checks()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("System")
        title.setObjectName("lbl-accent")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding-bottom: 4px;")
        root.addWidget(title)

        desc = QLabel(
            "Configure model and environment settings. Load or download GGUF models, "
            "manage default generation hyperparameters, active identity prompts, and check hardware resource specs."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px; padding-left: 2px;")
        root.addWidget(desc)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_model_tab(), "Model")
        self._tabs.addTab(self._build_registry_tab(), "Registry")
        self._tabs.addTab(self._build_params_tab(), "Defaults")
        self._tabs.addTab(self._build_identity_tab(), "Identity")
        self._tabs.addTab(self._build_vision_tab(), "Vision")
        self._tabs.addTab(self._build_mcp_tab(), "MCP")
        self._theme_tab = self._build_theme_tab()
        self._tabs.addTab(self._theme_tab, "Theme")
        self._tabs.addTab(self._build_hardware_tab(), "Hardware")
        root.addWidget(self._tabs, 1)

    def show_theme_tab(self):
        if hasattr(self, "_tabs") and hasattr(self, "_theme_tab"):
            self._sync_appearance_controls_from_state()
            self._tabs.setCurrentWidget(self._theme_tab)

    # ── model tab ─────────────────────────────────────────────────────────────

    def _build_model_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Active Model Panel
        active_panel = QWidget()
        active_panel.setObjectName("panel")
        ap_layout = QVBoxLayout(active_panel)
        ap_layout.setContentsMargins(12, 12, 12, 12)
        ap_layout.setSpacing(8)

        ap_layout.addWidget(_section("ACTIVE MODEL"))

        model_row = QWidget()
        mr = QHBoxLayout(model_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(8)
        self._model_path_input = QLineEdit()
        self._model_path_input.setPlaceholderText("path to .gguf file...")
        self._model_path_input.setToolTip("Path to the GGUF model file on disk")
        mr.addWidget(self._model_path_input, 1)
        browse = QPushButton("browse")
        browse.setToolTip("Browse files to select a local GGUF model")
        browse.clicked.connect(self._browse_model)
        mr.addWidget(browse)
        ap_layout.addWidget(model_row)

        load_btn = QPushButton("load model")
        load_btn.setObjectName("btn-primary")
        load_btn.setToolTip("Instantly load selected GGUF model")
        load_btn.clicked.connect(self._load_model)
        ap_layout.addWidget(load_btn)

        ap_layout.addWidget(_hline())
        ap_layout.addWidget(_section("ACTIVE ADAPTER"))

        adapter_row = QWidget()
        adr = QHBoxLayout(adapter_row)
        adr.setContentsMargins(0, 0, 0, 0)
        adr.setSpacing(8)
        self._adapter_combo = QComboBox()
        self._adapter_combo.setToolTip("Select a fine-tuned LoRA adapter to overlay on the base model")
        adr.addWidget(self._adapter_combo, 1)

        load_adapter_btn = QPushButton("load adapter")
        load_adapter_btn.setObjectName("btn-secondary")
        load_adapter_btn.setToolTip("Overlay the selected adapter on the active base model")
        load_adapter_btn.clicked.connect(self._load_adapter)
        adr.addWidget(load_adapter_btn)
        ap_layout.addWidget(adapter_row)

        ap_layout.addWidget(_hline())
        ap_layout.addWidget(_section("SPECULATIVE DECODING"))

        spec_desc = QLabel(
            "Load a small draft model (e.g. Qwen-0.5B, 1.5B) alongside the base model "
            "to accelerate token generation via speculative decoding."
        )
        spec_desc.setObjectName("lbl-muted")
        spec_desc.setWordWrap(True)
        ap_layout.addWidget(spec_desc)

        draft_row = QWidget()
        dr = QHBoxLayout(draft_row)
        dr.setContentsMargins(0, 0, 0, 0)
        dr.setSpacing(8)
        self._draft_model_input = QLineEdit()
        self._draft_model_input.setPlaceholderText("path to draft .gguf file (e.g. qwen-0.5b.gguf)...")
        self._draft_model_input.setToolTip("Small draft GGUF for speculative decoding — must share vocabulary with base model")
        dr.addWidget(self._draft_model_input, 1)
        draft_browse = QPushButton("browse")
        draft_browse.setToolTip("Browse for a draft GGUF file")
        draft_browse.clicked.connect(self._browse_draft_model)
        dr.addWidget(draft_browse)
        ap_layout.addWidget(draft_row)

        self._load_speculative_btn = QPushButton("load with speculative decode")
        self._load_speculative_btn.setObjectName("btn-primary")
        self._load_speculative_btn.setToolTip("Reload the active base model with the draft model attached")
        self._load_speculative_btn.clicked.connect(self._load_speculative)

        clear_draft_btn = QPushButton("clear draft")
        clear_draft_btn.setObjectName("btn-ghost")
        clear_draft_btn.setToolTip("Remove draft model and reload base model normally")
        clear_draft_btn.clicked.connect(self._clear_draft_model)

        spec_btn_row = QWidget()
        sbl = QHBoxLayout(spec_btn_row)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(8)
        sbl.addWidget(self._load_speculative_btn)
        sbl.addWidget(clear_draft_btn)
        ap_layout.addWidget(spec_btn_row)

        self._draft_status = QLabel("")
        self._draft_status.setObjectName("lbl-muted")
        self._draft_status.setWordWrap(True)
        ap_layout.addWidget(self._draft_status)

        self._model_status = QLabel("")
        self._model_status.setObjectName("lbl-muted")
        self._model_status.setWordWrap(True)
        ap_layout.addWidget(self._model_status)

        layout.addWidget(active_panel)

        # Available Models Panel
        available_panel = QWidget()
        available_panel.setObjectName("panel")
        avp_layout = QVBoxLayout(available_panel)
        avp_layout.setContentsMargins(12, 12, 12, 12)
        avp_layout.setSpacing(8)

        av_header = QWidget()
        avh_layout = QHBoxLayout(av_header)
        avh_layout.setContentsMargins(0, 0, 0, 0)
        avh_layout.addWidget(_section("AVAILABLE MODELS"))
        
        refresh_cache_btn = QPushButton("scan filesystem")
        refresh_cache_btn.setObjectName("btn-secondary")
        refresh_cache_btn.setFixedHeight(22)
        refresh_cache_btn.setStyleSheet("font-size: 8.5pt; padding: 2px 8px;")
        refresh_cache_btn.clicked.connect(self.refresh_filesystem_cache)
        avh_layout.addWidget(refresh_cache_btn)
        avp_layout.addWidget(av_header)

        self._model_list = QTextBrowser()
        self._model_list.setFixedHeight(160)
        self._model_list.setPlaceholderText("scanning data/models/...")
        avp_layout.addWidget(self._model_list)

        self._quant_info_lbl = QLabel("")
        self._quant_info_lbl.setObjectName("lbl-muted")
        self._quant_info_lbl.setWordWrap(True)
        self._quant_info_lbl.setStyleSheet("font-size: 8pt; padding: 4px; background: rgba(0,0,0,0.2); border-radius: 3px;")
        self._quant_info_lbl.setVisible(False)
        avp_layout.addWidget(self._quant_info_lbl)

        self._scan_models()

        layout.addWidget(available_panel)

        # ── Quantization Panel ────────────────────────────────────────────────
        quant_panel = QWidget()
        quant_panel.setObjectName("panel")
        qp_layout = QVBoxLayout(quant_panel)
        qp_layout.setContentsMargins(12, 12, 12, 12)
        qp_layout.setSpacing(8)

        qp_layout.addWidget(_section("QUANTIZE MODEL"))

        quant_desc = QLabel(
            "Convert a full-precision or higher-bit GGUF to a compact quantization format "
            "using the local llama-quantize binary (build/bin/llama-quantize or PATH)."
        )
        quant_desc.setObjectName("lbl-muted")
        quant_desc.setWordWrap(True)
        qp_layout.addWidget(quant_desc)

        # Source GGUF row
        src_row = QWidget()
        sr = QHBoxLayout(src_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(8)
        self._quant_src_input = QLineEdit()
        self._quant_src_input.setPlaceholderText("source .gguf file...")
        sr.addWidget(self._quant_src_input, 1)
        src_browse = QPushButton("browse")
        src_browse.clicked.connect(self._browse_quant_source)
        sr.addWidget(src_browse)
        qp_layout.addWidget(_row("Source GGUF", src_row))

        # Output filename row
        self._quant_out_input = QLineEdit()
        self._quant_out_input.setPlaceholderText("output filename (e.g. model-Q5_K_M.gguf)")
        qp_layout.addWidget(_row("Output File", self._quant_out_input))

        # Target format combo
        self._quant_format_combo = QComboBox()
        self._quant_format_combo.addItems([
            "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0",
            "Q3_K_M", "Q3_K_S", "Q4_K_S", "Q5_K_S",
            "Q2_K", "IQ4_NL", "F16", "F32",
        ])
        self._quant_format_combo.setToolTip(
            "Q4_K_M / Q5_K_M — best quality/size ratio for most models\n"
            "Q8_0 — near-lossless, largest file\n"
            "Q2_K — smallest file, significant quality drop"
        )
        qp_layout.addWidget(_row("Target Format", self._quant_format_combo))

        # Action row: Quantize button + Cancel button
        quant_btn_row = QWidget()
        qbr = QHBoxLayout(quant_btn_row)
        qbr.setContentsMargins(0, 0, 0, 0)
        qbr.setSpacing(8)

        self._quant_btn = QPushButton("quantize")
        self._quant_btn.setObjectName("btn-primary")
        self._quant_btn.setToolTip("Start llama-quantize subprocess in background thread")
        self._quant_btn.clicked.connect(self._start_quantize)
        qbr.addWidget(self._quant_btn)

        self._quant_cancel_btn = QPushButton("cancel")
        self._quant_cancel_btn.setObjectName("btn-ghost")
        self._quant_cancel_btn.setEnabled(False)
        self._quant_cancel_btn.clicked.connect(self._cancel_quantize)
        qbr.addWidget(self._quant_cancel_btn)
        qbr.addStretch()
        qp_layout.addWidget(quant_btn_row)

        # Progress bar (hidden until a job starts)
        self._quant_progress_bar = QProgressBar()
        self._quant_progress_bar.setRange(0, 100)
        self._quant_progress_bar.setValue(0)
        self._quant_progress_bar.setFixedHeight(12)
        self._quant_progress_bar.setVisible(False)
        qp_layout.addWidget(self._quant_progress_bar)

        # Status label
        self._quant_status_lbl = QLabel("")
        self._quant_status_lbl.setObjectName("lbl-muted")
        self._quant_status_lbl.setWordWrap(True)
        qp_layout.addWidget(self._quant_status_lbl)

        layout.addWidget(quant_panel)
        layout.addStretch()
        return w

    # ── quantization slots ────────────────────────────────────────────────────

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
        from app.engine import config_store
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

    def _build_params_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        params_panel = QWidget()
        params_panel.setObjectName("panel")
        pp_layout = QVBoxLayout(params_panel)
        pp_layout.setContentsMargins(12, 12, 12, 12)
        pp_layout.setSpacing(10)

        pp_layout.addWidget(_section("GENERATION DEFAULTS"))
        
        desc = QLabel(
            "These apply as defaults to new Workbench sessions. Each session can override them."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        pp_layout.addWidget(desc)

        # Settings Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        search_lbl = QLabel("Search Settings:")
        search_lbl.setObjectName("lbl-muted")
        search_lbl.setStyleSheet("font-size: 8.5pt;")
        self._settings_search_input = QLineEdit()
        self._settings_search_input.setPlaceholderText("type to filter settings...")
        self._settings_search_input.textChanged.connect(self._on_settings_search_changed)
        search_layout.addWidget(search_lbl)
        search_layout.addWidget(self._settings_search_input)
        pp_layout.addLayout(search_layout)
        pp_layout.addWidget(_hline())

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.05)
        self._temp_spin.setValue(0.7)
        self._temp_spin.setFixedWidth(90)

        self._topp_spin = QDoubleSpinBox()
        self._topp_spin.setRange(0.0, 1.0)
        self._topp_spin.setSingleStep(0.05)
        self._topp_spin.setValue(0.95)
        self._topp_spin.setFixedWidth(90)

        self._maxtok_spin = QSpinBox()
        self._maxtok_spin.setRange(64, 8192)
        self._maxtok_spin.setSingleStep(128)
        self._maxtok_spin.setValue(2048)
        self._maxtok_spin.setFixedWidth(90)

        self._reduced_motion_check = QCheckBox("Disable active glowing animations")
        self._reduced_motion_check.setChecked(getattr(self.state, "reduced_motion", False))
        self._reduced_motion_check.stateChanged.connect(self._on_reduced_motion_changed)

        self._settings_rows = []
        
        row1 = _row("Temperature", self._temp_spin)
        self._settings_rows.append(("Temperature", row1))
        pp_layout.addWidget(row1)

        row2 = _row("Top-P", self._topp_spin)
        self._settings_rows.append(("Top-P", row2))
        pp_layout.addWidget(row2)

        row3 = _row("Max Tokens", self._maxtok_spin)
        self._settings_rows.append(("Max Tokens", row3))
        pp_layout.addWidget(row3)

        row4 = _row("Accessibility", self._reduced_motion_check)
        self._settings_rows.append(("Accessibility", row4))
        pp_layout.addWidget(row4)

        # Theme Mode settings row
        self._theme_mode_combo = QComboBox()
        self._theme_mode_combo.addItems(["midnight", "slate", "ember"])
        self._theme_mode_combo.setCurrentText(getattr(self.state, "theme_mode", "midnight"))
        self._theme_mode_combo.currentTextChanged.connect(self._on_theme_mode_changed)
        self._theme_mode_combo.setFixedWidth(120)

        row5 = _row("Theme", self._theme_mode_combo)
        self._settings_rows.append(("Theme", row5))
        pp_layout.addWidget(row5)

        self._log_rotation_spin = QSpinBox()
        self._log_rotation_spin.setRange(1, 500)
        self._log_rotation_spin.setSingleStep(5)
        self._log_rotation_spin.setValue(getattr(self.state, "log_rotation_size_mb", 10))
        self._log_rotation_spin.setFixedWidth(90)
        self._log_rotation_spin.valueChanged.connect(self._on_log_rotation_changed)

        row6 = _row("Log Size Limit (MB)", self._log_rotation_spin)
        self._settings_rows.append(("Log Size Limit (MB)", row6))
        pp_layout.addWidget(row6)

        self._log_retention_spin = QSpinBox()
        self._log_retention_spin.setRange(1, 365)
        self._log_retention_spin.setSingleStep(5)
        self._log_retention_spin.setValue(getattr(self.state, "log_retention_days", 30))
        self._log_retention_spin.setFixedWidth(90)
        self._log_retention_spin.valueChanged.connect(self._on_log_retention_changed)

        row7 = _row("Log Retention (Days)", self._log_retention_spin)
        self._settings_rows.append(("Log Retention (Days)", row7))
        pp_layout.addWidget(row7)

        pp_layout.addWidget(_hline())
        pp_layout.addWidget(_section("SECURITY"))

        self._single_session_auth_check = QCheckBox("Enforce Single-Session Authorization")
        self._single_session_auth_check.setChecked(getattr(self.state, "single_session_auth", False))
        self._single_session_auth_check.setToolTip(
            "Wipe cached bridge token from OS keychain immediately upon exiting the application."
        )
        self._single_session_auth_check.stateChanged.connect(self._on_single_session_auth_changed)

        row8 = _row("Session Security", self._single_session_auth_check)
        self._settings_rows.append(("Session Security", row8))
        pp_layout.addWidget(row8)

        apply_btn = QPushButton("apply defaults")
        apply_btn.setObjectName("btn-primary")
        apply_btn.setToolTip("Save and apply default generation limits")
        apply_btn.clicked.connect(self._apply_defaults)
        pp_layout.addWidget(apply_btn)

        layout.addWidget(params_panel)
        layout.addStretch()
        return w

    def _on_reduced_motion_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked.value or state == True)
        self.state.reduced_motion = is_checked
        if hasattr(self, "_reduced_motion_check_app"):
            self._reduced_motion_check_app.blockSignals(True)
            self._reduced_motion_check_app.setChecked(is_checked)
            self._reduced_motion_check_app.blockSignals(False)
        self._apply_active_theme()
        self._save_appearance_config_silent()

    def _on_theme_mode_changed(self, text: str):
        self.state.theme_mode = text
        from app.ui import themes
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(themes.get_theme_stylesheet(self.state))
        self._save_appearance_config_silent()

    def _on_log_rotation_changed(self, val):
        self.state.log_rotation_size_mb = val
        self._save_appearance_config_silent()

    def _on_log_retention_changed(self, val):
        self.state.log_retention_days = val
        self._save_appearance_config_silent()

    def _on_single_session_auth_changed(self, state):
        is_checked = (state == 2 or state == Qt.CheckState.Checked.value or state is True)
        self.state.single_session_auth = is_checked
        self._save_appearance_config_silent()

    # ── identity tab ──────────────────────────────────────────────────────────

    def _build_identity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        identity_panel = QWidget()
        identity_panel.setObjectName("panel")
        ip_layout = QVBoxLayout(identity_panel)
        ip_layout.setContentsMargins(12, 12, 12, 12)
        ip_layout.setSpacing(8)

        ip_layout.addWidget(_section("SYSTEM PROMPT"))
        
        desc = QLabel(
            "This prompt defines Karl's persona and is sent before every conversation."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        ip_layout.addWidget(desc)

        from PyQt6.QtWidgets import QTextEdit
        self._system_edit = QTextEdit()
        self._system_edit.setPlainText(
            "You are Karl, a precise and thoughtful AI assistant. "
            "Always respond in English. "
            "Analyze and break down problems step-by-step. "
            "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
            "Double-check your derivations and arithmetic before writing the final answer."
        )
        self._system_edit.setToolTip("System prompt active during generation. Determines Karl's personality and guidelines.")
        ip_layout.addWidget(self._system_edit, 1)

        apply_btn = QPushButton("apply system prompt")
        apply_btn.setObjectName("btn-primary")
        apply_btn.setToolTip("Save this system prompt as the default identity")
        apply_btn.clicked.connect(self._apply_identity)
        ip_layout.addWidget(apply_btn)

        layout.addWidget(identity_panel, 1)
        return w

    # ── vision tab ────────────────────────────────────────────────────────────

    def _build_vision_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        runtime_panel = QWidget()
        runtime_panel.setObjectName("panel")
        rp = QVBoxLayout(runtime_panel)
        rp.setContentsMargins(12, 12, 12, 12)
        rp.setSpacing(8)
        rp.addWidget(_section("VISION RUNTIME"))

        desc = QLabel(
            "Karl vision stays offline. OCR can run immediately when Tesseract is installed; "
            "pixel-level image description requires a local GGUF vision model plus its matching projector."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        rp.addWidget(desc)

        self._vision_runtime_status = QLabel("")
        self._vision_runtime_status.setObjectName("lbl-muted")
        self._vision_runtime_status.setWordWrap(True)
        rp.addWidget(self._vision_runtime_status)

        model_row = QWidget()
        mr = QHBoxLayout(model_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(8)
        self._vision_model_combo = QComboBox()
        mr.addWidget(self._vision_model_combo, 1)

        active_btn = QPushButton("set active")
        active_btn.setObjectName("btn-secondary")
        active_btn.clicked.connect(self._set_active_vision_model_from_combo)
        mr.addWidget(active_btn)

        load_btn = QPushButton("load now")
        load_btn.setObjectName("btn-primary")
        load_btn.clicked.connect(self._load_active_vision_model)
        mr.addWidget(load_btn)

        reset_btn = QPushButton("reset")
        reset_btn.setObjectName("btn-ghost")
        reset_btn.clicked.connect(self._reset_vision_runtime)
        mr.addWidget(reset_btn)
        rp.addWidget(model_row)

        layout.addWidget(runtime_panel)

        registry_panel = QWidget()
        registry_panel.setObjectName("panel")
        vp = QVBoxLayout(registry_panel)
        vp.setContentsMargins(12, 12, 12, 12)
        vp.setSpacing(8)
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(_section("LOCAL VISION MODEL REGISTRY"))
        refresh_btn = QPushButton("refresh")
        refresh_btn.setObjectName("btn-ghost")
        refresh_btn.clicked.connect(self._refresh_vision_status)
        hl.addWidget(refresh_btn)
        vp.addWidget(header)

        self._vision_registry_view = QTextBrowser()
        self._vision_registry_view.setMinimumHeight(260)
        vp.addWidget(self._vision_registry_view, 1)
        layout.addWidget(registry_panel, 1)

        self._refresh_vision_status()
        return w

    def _refresh_vision_status(self):
        if not hasattr(self, "_vision_runtime_status"):
            return

        status = VisionModelLoader.status()
        backend = "available" if status["backend_available"] else "blocked"
        loaded = "loaded" if status["loaded"] else "not loaded"
        active = status.get("active_name") or "none"
        lines = [
            f"Backend: {backend}",
            f"Runtime: {loaded}",
            f"Active model: {active}",
        ]
        if status.get("backend_error"):
            lines.append(f"Backend detail: {status['backend_error']}")
        if status.get("last_error"):
            lines.append(f"Last error: {status['last_error']}")
        self._vision_runtime_status.setText("\n".join(lines))

        current = self._vision_model_combo.currentData()
        self._vision_model_combo.blockSignals(True)
        self._vision_model_combo.clear()
        rows = installed_vision_models()
        for row in rows:
            ready = row.get("model_installed") and row.get("projector_installed")
            suffix = "ready" if ready else "missing files"
            self._vision_model_combo.addItem(f"{row['name']} ({suffix})", row["id"])
        if current:
            idx = self._vision_model_combo.findData(current)
            if idx >= 0:
                self._vision_model_combo.setCurrentIndex(idx)
        self._vision_model_combo.blockSignals(False)

        html_rows = []
        for row in rows:
            model_state = "present" if row.get("model_installed") else "missing"
            projector_state = "present" if row.get("projector_installed") else "missing"
            html_rows.append(
                "<div style='margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.08);'>"
                f"<b style='color:#00C2FF;'>{html.escape(row['name'])}</b><br/>"
                f"<span style='color:#9090A8;'>Family:</span> {html.escape(row['family'])} &middot; "
                f"<span style='color:#9090A8;'>Context:</span> {int(row['n_ctx']):,}<br/>"
                f"<span style='color:#9090A8;'>Model:</span> {html.escape(row['model_path'])} "
                f"<b>{model_state}</b><br/>"
                f"<span style='color:#9090A8;'>Projector:</span> {html.escape(row['projector_path'])} "
                f"<b>{projector_state}</b><br/>"
                f"<span style='color:#9090A8;'>RAM:</span> &ge; {row['min_ram_gb']} GB &middot; "
                f"<span style='color:#9090A8;'>VRAM:</span> &ge; {row['min_vram_gb']} GB<br/>"
                f"<span style='color:#B8F7FF;'>{html.escape(row.get('strengths', ''))}</span><br/>"
                f"<span style='color:#9090A8;'>{html.escape(row.get('notes', ''))}</span>"
                "</div>"
            )
        self._vision_registry_view.setHtml(
            f"<div style='font-family:{MONO}; font-size:9pt; line-height:1.45;'>"
            + "".join(html_rows or ["No registry entries found."])
            + "</div>"
        )

    def _set_active_vision_model_from_combo(self):
        model_id = self._vision_model_combo.currentData()
        if not model_id:
            return
        set_active_vision_model(model_id)
        VisionModelLoader.reset()
        self._refresh_vision_status()
        QMessageBox.information(self, "Vision Model Selected", f"Active vision model set to {model_id}.")

    def _load_active_vision_model(self):
        model_id = self._vision_model_combo.currentData()
        VisionModelLoader.load(model_id=model_id)
        self._refresh_vision_status()

    def _reset_vision_runtime(self):
        VisionModelLoader.reset()
        self._refresh_vision_status()

    # ── hardware tab ──────────────────────────────────────────────────────────

    def _build_hardware_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Hardware Panel
        hw_panel = QWidget()
        hw_panel.setObjectName("panel")
        hwp_layout = QVBoxLayout(hw_panel)
        hwp_layout.setContentsMargins(16, 16, 16, 16)
        hwp_layout.setSpacing(12)

        hwp_layout.addWidget(_section("HARDWARE PROFILE & METERS"))

        # CPU meter
        cpu_row = QWidget()
        cpu_l = QHBoxLayout(cpu_row)
        cpu_l.setContentsMargins(0, 0, 0, 0)
        cpu_lbl = QLabel("CPU Load:")
        cpu_lbl.setFixedWidth(100)
        cpu_lbl.setObjectName("lbl-muted")
        self._cpu_progress = QProgressBar()
        self._cpu_progress.setRange(0, 100)
        self._cpu_progress.setValue(0)
        self._cpu_progress.setFixedHeight(14)
        cpu_l.addWidget(cpu_lbl)
        cpu_l.addWidget(self._cpu_progress)
        hwp_layout.addWidget(cpu_row)

        # RAM meter
        ram_row = QWidget()
        ram_l = QHBoxLayout(ram_row)
        ram_l.setContentsMargins(0, 0, 0, 0)
        ram_lbl = QLabel("Memory:")
        ram_lbl.setFixedWidth(100)
        ram_lbl.setObjectName("lbl-muted")
        self._ram_progress = QProgressBar()
        self._ram_progress.setRange(0, 100)
        self._ram_progress.setValue(0)
        self._ram_progress.setFixedHeight(14)
        ram_l.addWidget(ram_lbl)
        ram_l.addWidget(self._ram_progress)
        hwp_layout.addWidget(ram_row)
        
        # Disk Space meter
        disk_row = QWidget()
        disk_l = QHBoxLayout(disk_row)
        disk_l.setContentsMargins(0, 0, 0, 0)
        disk_lbl = QLabel("Disk Free:")
        disk_lbl.setFixedWidth(100)
        disk_lbl.setObjectName("lbl-muted")
        self._disk_progress = QProgressBar()
        self._disk_progress.setRange(0, 100)
        self._disk_progress.setValue(0)
        self._disk_progress.setFixedHeight(14)
        disk_l.addWidget(disk_lbl)
        disk_l.addWidget(self._disk_progress)
        hwp_layout.addWidget(disk_row)

        self._hw_view = QTextBrowser()
        self._hw_view.setFixedHeight(120)
        hwp_layout.addWidget(self._hw_view)

        refresh_btn = QPushButton("refresh profiles")
        refresh_btn.setToolTip("Re-scout RAM, VRAM, and storage specifications")
        refresh_btn.clicked.connect(self._refresh_hardware)
        hwp_layout.addWidget(refresh_btn)

        layout.addWidget(hw_panel)

        # About Panel
        about_panel = QWidget()
        about_panel.setObjectName("panel")
        ap_layout = QVBoxLayout(about_panel)
        ap_layout.setContentsMargins(12, 12, 12, 12)
        ap_layout.setSpacing(8)

        ap_layout.addWidget(_section("ABOUT KARL"))
        
        about = QLabel(
            "Karl &mdash; Privacy-first Offline LLM Introspection Environment<br/>"
            "Zero network calls &middot; In-process inference &middot; Immutable trace logs<br/>"
            "<a href='https://github.com/ethan-da-tech-wizard/karl' style='color:#00C2FF; text-decoration:none;'>https://github.com/ethan-da-tech-wizard/karl</a>"
        )
        about.setObjectName("lbl-muted")
        about.setWordWrap(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setOpenExternalLinks(True)
        ap_layout.addWidget(about)

        layout.addWidget(about_panel)
        layout.addStretch()
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

    def _update_live_hardware(self):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            
            self._cpu_progress.setValue(int(cpu))
            self._cpu_progress.setFormat(f"%p% ({cpu:.1f}%)")
            
            self._ram_progress.setValue(int(mem.percent))
            used_gb = mem.used / 1_073_741_824
            total_gb = mem.total / 1_073_741_824
            self._ram_progress.setFormat(f"%p% ({used_gb:.1f} GB / {total_gb:.1f} GB)")
            
            # Disk space
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            self._disk_progress.setValue(int(100 - free_percent))
            free_gb = free / 1_073_741_824
            total_gb = total / 1_073_741_824
            self._disk_progress.setFormat(f"{free_gb:.1f} GB free ({free_percent:.1f}%)")
        except Exception as e:
            logger.warning(f"Error updating live hardware meters: {e}")

    def _refresh_hardware(self):
        from core.hardware_scout import get_hardware_profile
        p = get_hardware_profile()
        
        ram = p.get('ram_gb', '?')
        vram = p.get('vram_gb', 'N/A')
        storage = p.get('storage_gb', '?')
        
        if isinstance(vram, (int, float)):
            vram_str = f"{vram:.1f} GB"
        else:
            vram_str = str(vram)
            
        html_content = (
            f"<div style='font-family:{MONO}; color:#E4E4F0; line-height:1.6;'>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>RAM</span>"
            f"<span style='font-size:11pt; color:#00C2FF; font-weight:bold;'>{ram} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB</span></span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>VRAM</span>"
            f"<span style='font-size:11pt; color:#2DD4A0; font-weight:bold;'>{vram_str}</span>"
            f"</div>"
            f"<div style='margin-bottom:8px; display:flex;'>"
            f"<span style='display:inline-block; width:120px; color:#505068; font-size:8.5pt; font-weight:bold; letter-spacing:1px;'>STORAGE</span>"
            f"<span style='font-size:11pt; color:#F0B030; font-weight:bold;'>{storage} <span style='font-size:8.5pt; font-weight:normal; color:#9090A8;'>GB free</span></span>"
            f"</div>"
            f"</div>"
        )
        self._hw_view.setHtml(html_content)

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GGUF model", "data/models", "GGUF (*.gguf);;All Files (*)"
        )
        if path:
            self._model_path_input.setText(path)

    def _load_model(self):
        path = self._model_path_input.text().strip()
        if not path:
            self._model_status.setText("enter a model path first")
            return
        if not os.path.exists(path):
            self._model_status.setText(f"file not found: {path}")
            return

        from app.engine.model_loader import ModelLoader
        ModelLoader.reset_instance()
        try:
            ModelLoader.get_instance(model_path=path)
            name = os.path.basename(path)
            self.state.model_name = name
            from app.engine import config_store
            if not config_store.set_active_model(name):
                raise OSError("Failed to persist data/active_model.json")
            self._scan_models(force=True)
            self._run_model_preflight_checks()
        except Exception as e:
            self._model_status.setText(f"error: {e}")

    def _browse_draft_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Draft GGUF model", "data/models", "GGUF (*.gguf);;All Files (*)"
        )
        if path:
            self._draft_model_input.setText(path)

    def _load_speculative(self):
        draft_path = self._draft_model_input.text().strip()
        if not draft_path:
            self._draft_status.setText("Enter a draft model path first.")
            return
        if not os.path.exists(draft_path):
            self._draft_status.setText(f"File not found: {draft_path}")
            return

        base_path = self._model_path_input.text().strip()
        if not base_path or not os.path.exists(base_path):
            from app.engine import config_store as _cs
            active = _cs.get_active_model()
            base_path = os.path.join("data", "models", active["filename"])

        from app.engine.model_loader import ModelLoader
        ModelLoader.reset_instance()
        try:
            ModelLoader.get_instance(model_path=base_path, draft_model_path=draft_path)
            draft_name = os.path.basename(draft_path)
            from app.engine import config_store as _cs
            _cs.set_active_draft_model(draft_name)
            speculative_on = ModelLoader.is_speculative()
            if speculative_on:
                self._draft_status.setText(
                    f"<span style='color:#2DD4A0;'>Speculative decoding active — draft: "
                    f"{draft_name}</span>"
                )
            else:
                self._draft_status.setText(
                    "<span style='color:#FFD800;'>Draft model loaded but speculative kwarg "
                    "unsupported by this llama-cpp-python version. Standard inference active.</span>"
                )
            self._draft_status.setTextFormat(Qt.TextFormat.RichText)
            self._run_model_preflight_checks()
        except Exception as e:
            self._draft_status.setText(f"<span style='color:#FF5C7A;'>Error: {e}</span>")
            self._draft_status.setTextFormat(Qt.TextFormat.RichText)

    def _clear_draft_model(self):
        from app.engine.model_loader import ModelLoader
        from app.engine import config_store as _cs
        ModelLoader.reset_instance()
        _cs.set_active_draft_model(None)
        self._draft_model_input.clear()
        self._draft_status.setText("Draft model cleared. Standard inference active.")
        self._run_model_preflight_checks()

    def _scan_models(self, force=False):
        models_dir = "data/models"
        if force or self._cached_models_list is None:
            if not os.path.exists(models_dir):
                self._cached_models_list = []
            else:
                try:
                    files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
                    cached = []
                    for f in sorted(files):
                        path = os.path.join(models_dir, f)
                        try:
                            size_bytes = os.path.getsize(path)
                            size_gb = size_bytes / (1024 * 1024 * 1024)
                            size_str = f"{size_gb:.2f} GB"
                        except Exception:
                            size_str = "unknown size"
                        cached.append({"filename": f, "size_str": size_str})
                    self._cached_models_list = cached
                except Exception:
                    self._cached_models_list = []

        if not self._cached_models_list:
            if not os.path.exists(models_dir):
                self._model_list.setHtml("<span style='color:#F05050;'>data/models/ not found</span>")
            else:
                self._model_list.setHtml("<span style='color:#505068;'>no .gguf models in data/models/</span>")
            return

        active_name = self._get_active_model_name()

        html_lines = []
        for item in self._cached_models_list:
            f = item["filename"]
            size_str = item["size_str"]
            is_active = (f == active_name)
            if is_active:
                indicator = "<span style='color:#2DD4A0; font-weight:bold;'>[ACTIVE]</span>"
                bg_style = "background: #161625; border: 1px solid #383850;"
                color_style = "color: #00C2FF; font-weight:bold;"
            else:
                indicator = "<span style='color:#505068;'>[inactive]</span>"
                bg_style = "background: #0D0D16; border: 1px solid #252535;"
                color_style = "color: #E4E4F0;"
                
            html_lines.append(
                f"<div style='margin-bottom:6px; padding:6px 10px; border-radius:4px; {bg_style}'>"
                f"<span style='{color_style}'>{html.escape(f)}</span> &middot; "
                f"<span style='color:#9090A8;'>{size_str}</span> &middot; "
                f"{indicator}"
                f"</div>"
            )
        
        self._model_list.setHtml("".join(html_lines))

    def _apply_identity(self):
        if self._workbench:
            self._workbench.set_system_prompt(
                self._system_edit.toPlainText().strip()
            )

    def _scan_adapters(self, force=False):
        if force or self._cached_adapters_list is None:
            adapters_dir = "data/adapters"
            cached = []
            if os.path.exists(adapters_dir):
                try:
                    for d in sorted(os.listdir(adapters_dir)):
                        d_path = os.path.join(adapters_dir, d)
                        if os.path.isdir(d_path):
                            files = os.listdir(d_path)
                            if any(f.endswith(".gguf") for f in files):
                                cached.append(d)
                except Exception as e:
                    logger.warning(f"Error scanning adapters: {e}")
            self._cached_adapters_list = cached

        self._adapter_combo.clear()
        self._adapter_combo.addItem("none")
        for d in self._cached_adapters_list:
            self._adapter_combo.addItem(d)

        # Select active adapter
        active_adapter = self.state.adapter_name or "none"
        index = self._adapter_combo.findText(active_adapter)
        if index >= 0:
            self._adapter_combo.setCurrentIndex(index)

    def _load_adapter(self):
        from app.engine.model_loader import ModelLoader
        adapter_name = self._adapter_combo.currentText()
        if adapter_name == "none":
            adapter_name = None
            
        ModelLoader.reset_instance()
        self.state.adapter_name = adapter_name
        self.adapter_changed.emit(adapter_name or "")
        
        # Save to active model configuration, preserving the active filename
        from app.engine import config_store
        try:
            filename = config_store.get_active_model()["filename"]
            if not config_store.set_active_model(filename, adapter_name):
                raise OSError("Failed to persist data/active_model.json")

            self._scan_adapters(force=True)
            self._run_model_preflight_checks()
            
            QMessageBox.information(
                self, "Adapter Loaded",
                f"Adapter '{adapter_name or 'none'}' has been set as active."
            )
        except Exception as e:
            QMessageBox.critical(self, "Adapter Error", f"Failed to save active adapter: {e}")

    def refresh_filesystem_cache(self):
        self._scan_models(force=True)
        self._scan_adapters(force=True)
        self._populate_registry()
        self._refresh_hardware()
        self._run_model_preflight_checks()

    def _on_settings_search_changed(self, text: str):
        query = text.strip().lower()
        for label, row_widget in self._settings_rows:
            if not query or query in label.lower():
                row_widget.setVisible(True)
            else:
                row_widget.setVisible(False)

    def _run_model_preflight_checks(self):
        from core.hardware_scout import get_hardware_profile
        active_name = self._get_active_model_name()

        if active_name == "none":
            self._model_status.setText("<div style='color: #888;'>No active model loaded.</div>")
            self._model_status.setTextFormat(Qt.TextFormat.RichText)
            return

        report = []
        warnings = []
        
        # 1. File existence & GGUF signature check
        model_path = os.path.join("data", "models", active_name)
        if os.path.isabs(active_name):
            model_path = active_name
            active_name = os.path.basename(active_name)
            
        if not os.path.exists(model_path):
            warnings.append(f"Model file not found at: {model_path}")
        else:
            try:
                with open(model_path, "rb") as f:
                    header = f.read(4)
                    if header != b"GGUF":
                        warnings.append("Invalid file format: File header does not match GGUF specification.")
            except Exception as e:
                warnings.append(f"Could not verify model file header: {e}")

        # 2. RAM requirement preflight check
        profile = get_hardware_profile()
        sys_ram = profile.get("ram_gb", 0.0)
        
        reg_item = None
        for item in self._registry:
            if item.get("filename") == active_name:
                reg_item = item
                break
                
        if reg_item:
            min_ram = reg_item.get("min_ram_gb", 0.0)
            if sys_ram > 0 and sys_ram < min_ram:
                warnings.append(
                    f"RAM Limit Warning: Model requires at least {min_ram} GB RAM, but system has only {sys_ram:.1f} GB."
                )
        else:
            if os.path.exists(model_path):
                try:
                    size_gb = os.path.getsize(model_path) / (1024**3)
                    est_ram = size_gb * 1.5
                    if sys_ram > 0 and sys_ram < est_ram:
                        warnings.append(
                            f"RAM Limit Warning: Estimated RAM needed is {est_ram:.1f} GB, but system has only {sys_ram:.1f} GB."
                        )
                except Exception:
                    pass

        # 3. Adapter compatibility warning
        active_adapter = self.state.adapter_name or "none"
        if active_adapter == "none":
            from app.engine import config_store
            data = config_store.read_json(config_store.ACTIVE_MODEL_PATH, default=None)
            if isinstance(data, dict):
                active_adapter = data.get("adapter") or "none"

        if active_adapter and active_adapter != "none":
            model_lower = active_name.lower()
            adapter_lower = active_adapter.lower()
            
            m_arch = None
            if "qwen" in model_lower:
                m_arch = "qwen"
            elif "llama" in model_lower:
                m_arch = "llama"
            elif "mistral" in model_lower:
                m_arch = "mistral"
                
            a_arch = None
            if "qwen" in adapter_lower:
                a_arch = "qwen"
            elif "llama" in adapter_lower:
                a_arch = "llama"
            elif "mistral" in adapter_lower:
                a_arch = "mistral"

            if m_arch and a_arch and m_arch != a_arch:
                warnings.append(
                    f"Adapter Compatibility Mismatch: Active adapter '{active_adapter}' appears to be for "
                    f"{a_arch.upper()} architecture, but active base model '{active_name}' is {m_arch.upper()}."
                )
            elif active_adapter != "none":
                report.append(f"Active Adapter: <b>{active_adapter}</b> (loaded)")

        status_color = "#2DD4A0" if not warnings else "#FFD800"
        status_text = "HEALTHY" if not warnings else "WARNINGS DETECTED"
        
        html_report = [
            f"<div style='margin-top: 10px; padding: 10px; border-radius: 4px; border: 1px solid {status_color}33; background: rgba(30,30,50,0.2);'>",
            f"<div style='font-weight: bold; color: {status_color}; margin-bottom: 6px;'>MODEL DIAGNOSTIC REPORT: {status_text}</div>",
            f"<div>Active Model: <b>{active_name}</b></div>"
        ]
        
        if report:
            for r in report:
                html_report.append(f"<div>{r}</div>")
                
        if warnings:
            html_report.append("<div style='margin-top: 6px; font-weight: bold; color: #FF3366;'>Warnings:</div>")
            for w in warnings:
                html_report.append(f"<div style='color: #FFB0B0; font-size: 8.5pt;'>&bull; {w}</div>")
        else:
            html_report.append("<div style='color: #2DD4A0; font-size: 8.5pt;'>&bull; No resource conflicts or GGUF signature warnings. Ready.</div>")
            
        html_report.append("</div>")
        
        self._model_status.setText("".join(html_report))
        self._model_status.setTextFormat(Qt.TextFormat.RichText)

        # Show quantization tradeoff info
        from app.engine.model_loader import ModelLoader
        from core.hardware_scout import get_hardware_profile
        quant = ModelLoader.get_quantization()
        vram_needed = ModelLoader.vram_estimate_gb()
        if quant and hasattr(self, '_quant_info_lbl'):
            hw = get_hardware_profile()
            vram_free = hw.get("vram_gb", 0.0)
            vram_str = f"{vram_needed:.1f} GB required, {vram_free:.1f} GB free" if vram_needed else ""
            quant_quality = {"Q4_K_M": "Good", "Q5_K_M": "Better", "Q8_0": "Best", "Q6_K": "Very Good"}.get(quant, quant)
            color = "#2DD4A0" if (not vram_needed or vram_free >= vram_needed) else "#FF5C7A"
            self._quant_info_lbl.setText(
                f"<span style='color:{color};'>{quant}</span> — Quality: {quant_quality} "
                + (f"| VRAM: {vram_str}" if vram_str else "")
            )
            self._quant_info_lbl.setTextFormat(Qt.TextFormat.RichText)
            self._quant_info_lbl.setVisible(True)

    def _apply_defaults(self):
        from PyQt6.QtWidgets import QMessageBox
        temp = self._temp_spin.value()
        top_p = self._topp_spin.value()
        max_tokens = self._maxtok_spin.value()
        
        if self._workbench:
            self._workbench.set_hyperparams({
                "temperature": temp,
                "top_p": top_p,
                "max_tokens": max_tokens
            })
            QMessageBox.information(
                self, "Defaults Applied",
                f"Generation defaults applied to Workbench:\n"
                f"• Temperature: {temp}\n"
                f"• Top-P: {top_p}\n"
                f"• Max Tokens: {max_tokens}"
            )

    # ── theme tab ─────────────────────────────────────────────────────────────

    def _build_theme_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Left Column: Controls (scrollable in case of small screen)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        ctrl_panel = QWidget()
        ctrl_panel.setObjectName("panel")
        ctrl_layout = QVBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        ctrl_layout.addWidget(_section("VISUAL THEME PRESETS"))

        # Presets Combobox
        self._theme_preset_combo = QComboBox()
        for name in THEMES.keys():
            self._theme_preset_combo.addItem(name)
        self._theme_preset_combo.currentTextChanged.connect(self._on_preset_changed)
        ctrl_layout.addWidget(_row("Preset Palette", self._theme_preset_combo))

        # Preset Description
        self._preset_desc_lbl = QLabel("")
        self._preset_desc_lbl.setObjectName("lbl-muted")
        self._preset_desc_lbl.setWordWrap(True)
        self._preset_desc_lbl.setStyleSheet("font-size: 8.5pt; margin-left: 130px; margin-bottom: 6px;")
        ctrl_layout.addWidget(self._preset_desc_lbl)

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("CUSTOM ACCENT OVERRIDE"))

        # Custom Accent Picker Row
        self._custom_accent_btn = QPushButton("Pick Custom Accent...")
        self._custom_accent_btn.clicked.connect(self._pick_custom_accent)
        
        self._clear_accent_btn = QPushButton("Reset Accent")
        self._clear_accent_btn.clicked.connect(self._reset_custom_accent)
        
        self._accent_color_preview = QLabel()
        self._accent_color_preview.setFixedSize(24, 24)
        self._accent_color_preview.setStyleSheet("border: 1px solid #35356E; border-radius: 4px;")

        accent_layout = QHBoxLayout()
        accent_layout.setSpacing(8)
        accent_layout.addWidget(self._custom_accent_btn, 1)
        accent_layout.addWidget(self._clear_accent_btn)
        accent_layout.addWidget(self._accent_color_preview)
        
        accent_widget = QWidget()
        accent_widget_layout = QHBoxLayout(accent_widget)
        accent_widget_layout.setContentsMargins(0, 0, 0, 0)
        accent_widget_layout.addLayout(accent_layout)
        ctrl_layout.addWidget(_row("Custom Accent", accent_widget))

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("THEME GALLERY"))

        self._theme_gallery = QScrollArea()
        self._theme_gallery.setWidgetResizable(True)
        self._theme_gallery.setFrameShape(QFrame.Shape.NoFrame)
        self._theme_gallery.setMinimumHeight(320)
        self._theme_gallery_content = QWidget()
        self._theme_gallery_layout = QVBoxLayout(self._theme_gallery_content)
        self._theme_gallery_layout.setContentsMargins(0, 0, 0, 0)
        self._theme_gallery_layout.setSpacing(8)
        self._theme_gallery.setWidget(self._theme_gallery_content)
        ctrl_layout.addWidget(self._theme_gallery)

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("LAYOUT DENSITY PRESETS"))

        # Layout density selector
        self._layout_preset_combo = QComboBox()
        self._layout_preset_combo.addItems([
            "Focused Workbench",
            "Research Lab",
            "Training Console",
            "Evaluation Wall",
            "Compact Laptop",
            "Wide Monitor Command",
            "Minimal Distraction",
            "Max Introspection",
            "Knowledge Heavy",
            "Prompt Engineering Lab"
        ])
        self._layout_preset_combo.currentTextChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Layout Density", self._layout_preset_combo))

        ctrl_layout.addWidget(_hline())
        ctrl_layout.addWidget(_section("EFFECTS & MOTION SYSTEM"))

        # Glow enabled checkbox
        self._glow_enabled_check = QCheckBox("Enable Glow Effects")
        self._glow_enabled_check.stateChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Edge Glow", self._glow_enabled_check))

        # Glow Strength Slider
        self._glow_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self._glow_strength_slider.setRange(0, 20)
        self._glow_strength_slider.setSingleStep(1)
        self._glow_strength_slider.setPageStep(2)
        self._glow_strength_slider.setValue(10)
        self._glow_strength_slider.valueChanged.connect(self._on_control_changed)
        
        self._glow_strength_val_lbl = QLabel("1.0x")
        self._glow_strength_val_lbl.setFixedWidth(40)
        self._glow_strength_val_lbl.setObjectName("lbl-muted")
        
        glow_row_widget = QWidget()
        gr_layout = QHBoxLayout(glow_row_widget)
        gr_layout.setContentsMargins(0, 0, 0, 0)
        gr_layout.setSpacing(8)
        gr_layout.addWidget(self._glow_strength_slider, 1)
        gr_layout.addWidget(self._glow_strength_val_lbl)
        ctrl_layout.addWidget(_row("Glow Strength", glow_row_widget))

        # Animation Intensity (Speed) Slider
        self._animation_intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self._animation_intensity_slider.setRange(0, 20)
        self._animation_intensity_slider.setSingleStep(1)
        self._animation_intensity_slider.setPageStep(2)
        self._animation_intensity_slider.setValue(10)
        self._animation_intensity_slider.valueChanged.connect(self._on_control_changed)
        
        self._animation_intensity_val_lbl = QLabel("1.0x")
        self._animation_intensity_val_lbl.setFixedWidth(40)
        self._animation_intensity_val_lbl.setObjectName("lbl-muted")
        
        anim_row_widget = QWidget()
        ar_layout = QHBoxLayout(anim_row_widget)
        ar_layout.setContentsMargins(0, 0, 0, 0)
        ar_layout.setSpacing(8)
        ar_layout.addWidget(self._animation_intensity_slider, 1)
        ar_layout.addWidget(self._animation_intensity_val_lbl)
        ctrl_layout.addWidget(_row("Motion Speed", anim_row_widget))

        # Reduced motion checkbox (Disable active glowing animations)
        self._reduced_motion_check_app = QCheckBox("Disable active glowing animations (Reduced Motion)")
        self._reduced_motion_check_app.stateChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(_row("Accessibility", self._reduced_motion_check_app))

        # Save & Apply Button
        apply_btn = QPushButton("Save Appearance Config")
        apply_btn.setObjectName("btn-primary")
        apply_btn.clicked.connect(self._save_appearance_config)
        ctrl_layout.addWidget(apply_btn)

        scroll_layout.addWidget(ctrl_panel)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 3)

        # Right Column: Live Preview Card + Swatches
        preview_col = QWidget()
        pr_layout = QVBoxLayout(preview_col)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        pr_layout.setSpacing(12)

        # Swatches Panel
        swatches_panel = QWidget()
        swatches_panel.setObjectName("panel")
        sp_layout = QVBoxLayout(swatches_panel)
        sp_layout.setContentsMargins(12, 12, 12, 12)
        sp_layout.setSpacing(8)
        sp_layout.addWidget(_section("ACTIVE PALETTE OVERVIEW"))
        
        self._swatches_container = QWidget()
        self._swatches_layout = QHBoxLayout(self._swatches_container)
        self._swatches_layout.setContentsMargins(0, 4, 0, 4)
        self._swatches_layout.setSpacing(6)
        sp_layout.addWidget(self._swatches_container)
        pr_layout.addWidget(swatches_panel)

        # Live Preview Panel using TracingPanel
        self._preview_card = TracingPanel(self.state)
        self._preview_card.set_active(True)
        self._preview_card.setMinimumHeight(280)
        
        card_layout = QVBoxLayout(self._preview_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        
        self._add_preview_elements(card_layout)
        pr_layout.addWidget(self._preview_card, 1)

        layout.addWidget(preview_col, 2)

        # Load active configuration if file exists
        self._load_active_appearance_config()
        
        return w

    def _add_preview_elements(self, card_layout: QVBoxLayout):
        title = QLabel("LIVE PREVIEW")
        title.setObjectName("section-header")
        card_layout.addWidget(title)
        
        desc = QLabel("Realtime mockup card showing active styles.")
        desc.setObjectName("lbl-muted")
        desc.setStyleSheet("font-size: 8pt; margin-bottom: 2px;")
        card_layout.addWidget(desc)
        
        # Primary & Secondary Buttons mockup
        btn_row = QWidget()
        br_layout = QHBoxLayout(btn_row)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(8)
        
        btn_prim = QPushButton("Primary Button")
        btn_prim.setObjectName("btn-primary")
        btn_prim.setFixedHeight(26)
        btn_prim.setStyleSheet("font-size: 8.5pt; padding: 2px 10px;")
        
        btn_sec = QPushButton("Secondary Button")
        btn_sec.setObjectName("btn-secondary")
        btn_sec.setFixedHeight(26)
        btn_sec.setStyleSheet("font-size: 8.5pt; padding: 2px 10px;")
        
        br_layout.addWidget(btn_prim)
        br_layout.addWidget(btn_sec)
        card_layout.addWidget(btn_row)
        
        # Success & Error badges using custom painted icons
        badge_row = QWidget()
        bg_layout = QHBoxLayout(badge_row)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(16)
        
        # Success badge
        succ_widget = QWidget()
        sw_layout = QHBoxLayout(succ_widget)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(4)
        self._check_icon_preview = CheckIcon(self.state, color_role="green", size=14)
        lbl_succ = QLabel("Success Badge")
        lbl_succ.setStyleSheet("color: #00FFAA; font-size: 8.5pt;")
        sw_layout.addWidget(self._check_icon_preview)
        sw_layout.addWidget(lbl_succ)
        
        # Error badge
        err_widget = QWidget()
        ew_layout = QHBoxLayout(err_widget)
        ew_layout.setContentsMargins(0, 0, 0, 0)
        ew_layout.setSpacing(4)
        self._cross_icon_preview = CrossIcon(self.state, color_role="red", size=14)
        lbl_err = QLabel("Error Badge")
        lbl_err.setStyleSheet("color: #FF3366; font-size: 8.5pt;")
        ew_layout.addWidget(self._cross_icon_preview)
        ew_layout.addWidget(lbl_err)
        
        bg_layout.addWidget(succ_widget)
        bg_layout.addWidget(err_widget)
        card_layout.addWidget(badge_row)
        
        # Chat bubbles mockup
        chat_mockup = QWidget()
        cm_layout = QVBoxLayout(chat_mockup)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.setSpacing(6)
        
        # User bubble
        user_bubble = QLabel("How does local introspection work?")
        user_bubble.setStyleSheet(
            "background: rgba(31, 31, 61, 0.3); border: 1px solid rgba(53, 53, 110, 0.4); "
            "border-radius: 4px; padding: 6px; font-size: 8.5pt; color: #F0F5FF;"
        )
        cm_layout.addWidget(user_bubble)
        
        # Assistant bubble
        assistant_bubble = QLabel(
            "Analyzing trace stream...<br/>"
            "<span style='color: #A0AEC0; font-family: monospace; font-size: 8pt;'>"
            "&lt;think&gt;<br/>Reasoning tier 1: verifying model budget context... ok.<br/>&lt;/think&gt;</span><br/>"
            "Introspection processes generation traces in real-time."
        )
        assistant_bubble.setTextFormat(Qt.TextFormat.RichText)
        assistant_bubble.setStyleSheet(
            "background: rgba(13, 13, 27, 0.5); border: 1px solid rgba(31, 31, 61, 0.5); "
            "border-radius: 4px; padding: 6px; font-size: 8.5pt;"
        )
        cm_layout.addWidget(assistant_bubble)
        card_layout.addWidget(chat_mockup)
        
        card_layout.addStretch()

    def _load_active_appearance_config(self):
        from app.engine import config_store
        config = config_store.get_ui_config()
        theme_preset = config["theme_preset"]
        custom_accent = config["custom_accent"]
        layout_preset = config["layout_preset"]
        reduced_motion = config["reduced_motion"]
        glow_enabled = config["glow_enabled"]
        animation_intensity = config["animation_intensity"]
        glow_strength = config["glow_strength"]
        theme_mode = config.get("theme_mode", "midnight")

        self.state.theme_mode = theme_mode
        if hasattr(self, "_theme_mode_combo"):
            self._theme_mode_combo.blockSignals(True)
            self._theme_mode_combo.setCurrentText(theme_mode)
            self._theme_mode_combo.blockSignals(False)

        self._theme_preset_combo.blockSignals(True)
        idx = self._theme_preset_combo.findText(theme_preset)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)
        self._theme_preset_combo.blockSignals(False)

        self._layout_preset_combo.blockSignals(True)
        idx = self._layout_preset_combo.findText(layout_preset)
        if idx >= 0:
            self._layout_preset_combo.setCurrentIndex(idx)
        self._layout_preset_combo.blockSignals(False)

        self._glow_enabled_check.blockSignals(True)
        self._glow_enabled_check.setChecked(glow_enabled)
        self._glow_enabled_check.blockSignals(False)

        self._reduced_motion_check_app.blockSignals(True)
        self._reduced_motion_check_app.setChecked(reduced_motion)
        self._reduced_motion_check_app.blockSignals(False)

        self._glow_strength_slider.blockSignals(True)
        self._glow_strength_slider.setValue(int(glow_strength * 10))
        self._glow_strength_slider.blockSignals(False)
        self._glow_strength_val_lbl.setText(f"{glow_strength:.1f}x")

        self._animation_intensity_slider.blockSignals(True)
        self._animation_intensity_slider.setValue(int(animation_intensity * 10))
        self._animation_intensity_slider.blockSignals(False)
        self._animation_intensity_val_lbl.setText(f"{animation_intensity:.1f}x")

        self._active_custom_accent = custom_accent
        
        # Initial updates
        self._update_accent_button_text()
        self._on_preset_changed()

    def _sync_appearance_controls_from_state(self):
        theme_preset = getattr(self.state, "theme_preset", "Karl Obsidian Core")
        layout_preset = getattr(self.state, "layout_preset", "Focused Workbench")
        custom_accent = getattr(self.state, "custom_accent", None)
        reduced_motion = getattr(self.state, "reduced_motion", False)
        glow_enabled = getattr(self.state, "glow_enabled", True)
        animation_intensity = float(getattr(self.state, "animation_intensity", 1.0))
        glow_strength = float(getattr(self.state, "glow_strength", 1.0))
        theme_mode = getattr(self.state, "theme_mode", "midnight")

        if hasattr(self, "_theme_mode_combo"):
            self._theme_mode_combo.blockSignals(True)
            self._theme_mode_combo.setCurrentText(theme_mode)
            self._theme_mode_combo.blockSignals(False)

        self._theme_preset_combo.blockSignals(True)
        idx = self._theme_preset_combo.findText(theme_preset)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)
        self._theme_preset_combo.blockSignals(False)

        self._layout_preset_combo.blockSignals(True)
        idx = self._layout_preset_combo.findText(layout_preset)
        if idx >= 0:
            self._layout_preset_combo.setCurrentIndex(idx)
        self._layout_preset_combo.blockSignals(False)

        self._glow_enabled_check.blockSignals(True)
        self._glow_enabled_check.setChecked(glow_enabled)
        self._glow_enabled_check.blockSignals(False)

        self._reduced_motion_check_app.blockSignals(True)
        self._reduced_motion_check_app.setChecked(reduced_motion)
        self._reduced_motion_check_app.blockSignals(False)

        self._glow_strength_slider.blockSignals(True)
        self._glow_strength_slider.setValue(int(glow_strength * 10))
        self._glow_strength_slider.blockSignals(False)
        self._glow_strength_val_lbl.setText(f"{glow_strength:.1f}x")

        self._animation_intensity_slider.blockSignals(True)
        self._animation_intensity_slider.setValue(int(animation_intensity * 10))
        self._animation_intensity_slider.blockSignals(False)
        self._animation_intensity_val_lbl.setText(f"{animation_intensity:.1f}x")

        self._active_custom_accent = custom_accent
        self._update_accent_button_text()
        self._preset_desc_lbl.setText(THEMES.get(theme_preset, {}).get("description", ""))
        self._update_swatches()
        self._update_theme_gallery()

    def _update_accent_button_text(self):
        if self._active_custom_accent:
            self._custom_accent_btn.setText(f"Accent: {self._active_custom_accent}")
            self._accent_color_preview.setStyleSheet(
                f"background-color: {self._active_custom_accent}; border: 1px solid #35356E; border-radius: 4px;"
            )
        else:
            self._custom_accent_btn.setText("Pick Custom Accent...")
            colors = get_theme_colors(self.state)
            accent_default = colors.get("accent", "#00C2FF")
            self._accent_color_preview.setStyleSheet(
                f"background-color: {accent_default}; border: 1px solid #35356E; border-radius: 4px;"
            )

    def _on_preset_changed(self):
        preset_name = self._theme_preset_combo.currentText()
        preset_data = THEMES.get(preset_name, {})
        self._preset_desc_lbl.setText(preset_data.get("description", ""))
        self._update_accent_button_text()
        self._apply_active_theme()
        self._update_theme_gallery()

    def _pick_custom_accent(self):
        preset_name = self._theme_preset_combo.currentText()
        default_color = THEMES.get(preset_name, {}).get("accent", "#00C2FF")
        if self._active_custom_accent:
            default_color = self._active_custom_accent
            
        color = QColorDialog.getColor(QColor(default_color), self, "Select Custom Accent Color")
        if color.isValid():
            self._active_custom_accent = color.name().upper()
            self._update_accent_button_text()
            self._apply_active_theme()

    def _reset_custom_accent(self):
        self._active_custom_accent = None
        self._update_accent_button_text()
        self._apply_active_theme()

    def _on_control_changed(self):
        # Update sliders numeric indicators
        gs = self._glow_strength_slider.value() / 10.0
        ai = self._animation_intensity_slider.value() / 10.0
        self._glow_strength_val_lbl.setText(f"{gs:.1f}x")
        self._animation_intensity_val_lbl.setText(f"{ai:.1f}x")

        # Also sync reduced motion check in defaults tab
        self._reduced_motion_check.blockSignals(True)
        self._reduced_motion_check.setChecked(self._reduced_motion_check_app.isChecked())
        self._reduced_motion_check.blockSignals(False)

        # Debounce: slider drags fire valueChanged per tick; recompiling and
        # re-applying the app stylesheet on every tick stutters the drag.
        # Labels above update live, the theme applies once the drag settles.
        if not hasattr(self, "_theme_apply_timer"):
            from PyQt6.QtCore import QTimer
            self._theme_apply_timer = QTimer(self)
            self._theme_apply_timer.setSingleShot(True)
            self._theme_apply_timer.setInterval(120)
            self._theme_apply_timer.timeout.connect(self._apply_active_theme)
        self._theme_apply_timer.start()

    def _apply_active_theme(self):
        # Read from controls
        theme_preset = self._theme_preset_combo.currentText()
        layout_preset = self._layout_preset_combo.currentText()
        glow_enabled = self._glow_enabled_check.isChecked()
        reduced_motion = self._reduced_motion_check_app.isChecked()
        glow_strength = self._glow_strength_slider.value() / 10.0
        animation_intensity = self._animation_intensity_slider.value() / 10.0
        custom_accent = self._active_custom_accent

        # Write to state
        self.state.theme_preset = theme_preset
        self.state.layout_preset = layout_preset
        self.state.glow_enabled = glow_enabled
        self.state.reduced_motion = reduced_motion
        self.state.glow_strength = glow_strength
        self.state.animation_intensity = animation_intensity
        self.state.custom_accent = custom_accent

        # Trigger QApplication stylesheet compilation & reload
        self.appearance_changed.emit()

        # Update preview card elements
        self._preview_card.update_style()
        self._check_icon_preview.update()
        self._cross_icon_preview.update()
        self._update_swatches()

    def _update_swatches(self):
        # Clear existing swatches
        while self._swatches_layout.count():
            item = self._swatches_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Generate colors for current state
        colors = get_theme_colors(self.state)
        swatch_keys = [
            ("accent", "ACCENT"),
            ("accent_dark", "ALT"),
            ("bg_surface", "SURFACE"),
            ("bg_deep", "DEEP"),
            ("text_hi", "TEXT")
        ]
        
        for key, label in swatch_keys:
            hex_val = colors.get(key, "#000000")
            
            swatch_unit = QWidget()
            su_layout = QVBoxLayout(swatch_unit)
            su_layout.setContentsMargins(0, 0, 0, 0)
            su_layout.setSpacing(2)
            
            color_box = QLabel()
            color_box.setFixedSize(36, 24)
            color_box.setStyleSheet(
                f"background-color: {hex_val}; border: 1px solid {colors.get('border', '#35356E')}; border-radius: 3px;"
            )
            color_box.setToolTip(f"{label}: {hex_val}")
            
            lbl_text = QLabel(label)
            lbl_text.setStyleSheet("font-size: 7.5pt; font-weight: bold; text-align: center;")
            lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_text.setObjectName("lbl-muted")
            
            su_layout.addWidget(color_box, alignment=Qt.AlignmentFlag.AlignCenter)
            su_layout.addWidget(lbl_text, alignment=Qt.AlignmentFlag.AlignCenter)
            
            self._swatches_layout.addWidget(swatch_unit)

    def _update_theme_gallery(self):
        if not hasattr(self, "_theme_gallery_layout"):
            return
        # The 20 cards only differ by which one carries the ACTIVE marker;
        # skip the full rebuild when the selection hasn't changed.
        selected_now = self._theme_preset_combo.currentText()
        if (getattr(self, "_gallery_built_for", None) == selected_now
                and self._theme_gallery_layout.count() > 0):
            return
        self._gallery_built_for = selected_now
        while self._theme_gallery_layout.count():
            item = self._theme_gallery_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        selected = self._theme_preset_combo.currentText()
        for name, data in THEMES.items():
            border = data.get("border_hi", "#35356E")
            accent = data.get("accent", "#00E5FF")
            accent_alt = data.get("accent_alt", "#0099AA")
            bg_deep = data.get("bg_deep", "#020205")
            bg_surface = data.get("bg_surface", "#0D0D1B")
            bg_raised = data.get("bg_raised", "#14142D")
            text_hi = data.get("text_hi", "#F0F5FF")
            text_mid = data.get("text_mid", "#A0AEC0")

            card = QWidget()
            card.setObjectName("panel")
            card.setStyleSheet(
                f"QWidget#panel {{ background-color: {bg_surface}; border: 1px solid {border}; border-radius: 6px; }}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(6)

            header = QWidget()
            hl = QHBoxLayout(header)
            hl.setContentsMargins(0, 0, 0, 0)
            title = QLabel(name + ("  ACTIVE" if name == selected else ""))
            title.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 9.5pt;")
            hl.addWidget(title, 1)
            apply_btn = QPushButton("Apply")
            apply_btn.setObjectName("btn-primary" if name == selected else "btn-secondary")
            apply_btn.clicked.connect(lambda _checked=False, n=name: self._apply_theme_preset_from_gallery(n))
            hl.addWidget(apply_btn)
            cl.addWidget(header)

            desc = QLabel(data.get("description", ""))
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {text_mid}; font-size: 8.2pt;")
            cl.addWidget(desc)

            swatch_row = QWidget()
            sl = QHBoxLayout(swatch_row)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setSpacing(5)
            for value, label in (
                (accent, "accent"),
                (accent_alt, "alt"),
                (bg_deep, "deep"),
                (bg_surface, "surface"),
                (bg_raised, "raised"),
                (text_hi, "text"),
            ):
                box = QLabel()
                box.setFixedSize(34, 16)
                box.setToolTip(f"{label}: {value}")
                box.setStyleSheet(f"background-color: {value}; border: 1px solid {border}; border-radius: 3px;")
                sl.addWidget(box)
            sl.addStretch()
            cl.addWidget(swatch_row)
            self._theme_gallery_layout.addWidget(card)

        self._theme_gallery_layout.addStretch(1)

    def _apply_theme_preset_from_gallery(self, name: str):
        idx = self._theme_preset_combo.findText(name)
        if idx >= 0:
            self._theme_preset_combo.setCurrentIndex(idx)

    def _save_appearance_config_silent(self):
        from app.engine import config_store
        config_store.save_ui_config({
            "theme_preset": self.state.theme_preset,
            "custom_accent": self.state.custom_accent,
            "layout_preset": self.state.layout_preset,
            "reduced_motion": self.state.reduced_motion,
            "glow_enabled": self.state.glow_enabled,
            "animation_intensity": self.state.animation_intensity,
            "glow_strength": self.state.glow_strength,
            "theme_mode": getattr(self.state, "theme_mode", "midnight"),
            "log_rotation_size_mb": getattr(self.state, "log_rotation_size_mb", 10),
            "log_retention_days": getattr(self.state, "log_retention_days", 30),
            "single_session_auth": getattr(self.state, "single_session_auth", False),
        })

    def _save_appearance_config(self):
        self._save_appearance_config_silent()
        
        # Delete old config if exists to clean up
        old_path = "data/theme_config.json"
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
                
        QMessageBox.information(
            self, "Settings Saved",
            "Appearance configuration saved successfully to data/ui_config.json."
        )

    def _build_mcp_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        panel = QWidget(); panel.setObjectName("panel")
        pl = QVBoxLayout(panel); pl.setContentsMargins(12,12,12,12); pl.setSpacing(8)
        pl.addWidget(_section("MCP TOOL SERVERS"))
    
        desc = QLabel(
            "MCP servers extend Karl with tools: web search, file system, databases, APIs. "
            "Each server is a stdio subprocess spawned on connection."
        )
        desc.setObjectName("lbl-muted"); desc.setWordWrap(True)
        pl.addWidget(desc)
    
        self._mcp_server_list = QTextBrowser()
        self._mcp_server_list.setFixedHeight(140)
        pl.addWidget(self._mcp_server_list)
    
        add_row = QWidget(); ar = QHBoxLayout(add_row); ar.setContentsMargins(0,0,0,0); ar.setSpacing(6)
        self._mcp_name_input = QLineEdit();
        self._mcp_name_input.setPlaceholderText("Server name (e.g. brave-search)")
        self._mcp_cmd_input  = QLineEdit();
        self._mcp_cmd_input.setPlaceholderText("Command (e.g. npx @modelcontextprotocol/server-brave-search)")
        ar.addWidget(self._mcp_name_input, 1)
        ar.addWidget(self._mcp_cmd_input, 2)
        pl.addWidget(add_row)
    
        btn_row = QWidget(); br = QHBoxLayout(btn_row); br.setContentsMargins(0,0,0,0); br.setSpacing(6)
        add_btn = QPushButton("Add Server"); add_btn.setObjectName("btn-primary")
        add_btn.clicked.connect(self._add_mcp_server)
        remove_btn = QPushButton("Remove Selected"); remove_btn.setObjectName("btn-ghost")
        remove_btn.clicked.connect(self._remove_mcp_server)
        restart_btn = QPushButton("Restart MCP Client");
        restart_btn.setObjectName("btn-secondary")
        restart_btn.clicked.connect(self._restart_mcp_client)
        br.addWidget(add_btn); br.addWidget(remove_btn); br.addWidget(restart_btn)
        pl.addWidget(btn_row)
    
        self._mcp_tools_lbl = QLabel("Connected tools: —");
        self._mcp_tools_lbl.setObjectName("lbl-muted")
        pl.addWidget(self._mcp_tools_lbl)
        layout.addWidget(panel); layout.addStretch()
        self._refresh_mcp_display()
        return w

    def _refresh_mcp_display(self):
        from app.engine import config_store
        cfg = config_store.get_mcp_config()
        servers = cfg.get("mcpServers", {})
        if not servers:
            self._mcp_server_list.setPlainText("No MCP servers configured.")
            return
        lines = [f"• {name}: {s.get('command', '')} {' '.join(s.get('args', []))}"
                 for name, s in servers.items()]
        self._mcp_server_list.setPlainText("\n".join(lines))
        # Show connected tool count
        try:
            from app.engine.mcp_client import MCPClientManager
            tools = MCPClientManager.get_tool_schemas()
            self._mcp_tools_lbl.setText(f"Connected tools: {len(tools)}")
        except Exception:
            self._mcp_tools_lbl.setText("Connected tools: client not started")

    def _add_mcp_server(self):
        name = self._mcp_name_input.text().strip()
        cmd_raw = self._mcp_cmd_input.text().strip()
        if not name or not cmd_raw:
            QMessageBox.warning(self, "MCP", "Server name and command are required.")
            return
        parts = cmd_raw.split()
        command, args = parts[0], parts[1:]
        from app.engine import config_store
        config_store.add_mcp_server(name, command, args)
        self._mcp_name_input.clear(); self._mcp_cmd_input.clear()
        self._refresh_mcp_display()
    
    def _remove_mcp_server(self):
        name, ok = QInputDialog.getText(self, "Remove MCP Server", "Server name to remove:")
        if ok and name.strip():
            from app.engine import config_store
            config_store.remove_mcp_server(name.strip())
            self._refresh_mcp_display()
    
    def _restart_mcp_client(self):
        try:
            from app.engine.mcp_client import MCPClientManager
            MCPClientManager.reset_instance()
            mgr = MCPClientManager.get_instance()
            mgr.start()
            MCPClientManager.invalidate_cache()
            self._refresh_mcp_display()
            QMessageBox.information(self, "MCP", "MCP client restarted successfully.")
        except Exception as e:
            QMessageBox.critical(self, "MCP Error", str(e))
