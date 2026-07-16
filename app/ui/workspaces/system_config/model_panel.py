from __future__ import annotations

import html
import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QLabel, QLineEdit,
    QFileDialog,
    QMessageBox, QProgressBar,
    QComboBox,
    QCheckBox,
    QScrollArea, QFrame,
)

from app.engine import config_store
from .common import _hline, _row, _section

logger = logging.getLogger("karl.system_config")

class ModelPanelMixin:
    def _build_model_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
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

        self._load_model_btn = QPushButton("load model")
        self._load_model_btn.setObjectName("btn-primary")
        self._load_model_btn.setToolTip("Load selected GGUF model without blocking the interface")
        self._load_model_btn.clicked.connect(self._load_model)
        ap_layout.addWidget(self._load_model_btn)

        # Circuit Breaker Status Row
        cb_row = QWidget()
        cbl = QHBoxLayout(cb_row)
        cbl.setContentsMargins(0, 0, 0, 0)
        cbl.setSpacing(8)
        self._cb_status_lbl = QLabel("Circuit Breaker: CLOSED")
        self._cb_status_lbl.setToolTip("Protects the system from freeze loops on repeated load failures")
        self._cb_status_lbl.setStyleSheet("font-size: 9pt;")
        cbl.addWidget(self._cb_status_lbl, 1)

        self._cb_reset_btn = QPushButton("reset breaker")
        self._cb_reset_btn.setObjectName("btn-secondary")
        self._cb_reset_btn.setToolTip("Force-close the circuit breaker to allow model loading immediately")
        self._cb_reset_btn.clicked.connect(self._reset_circuit_breaker)
        cbl.addWidget(self._cb_reset_btn)
        ap_layout.addWidget(cb_row)

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

        self._speculative_toggle = QCheckBox("Enable speculative drafting")
        self._speculative_toggle.setToolTip("Use a smaller local draft GGUF to propose tokens for the active base model")
        ap_layout.addWidget(self._speculative_toggle)

        spec_desc = QLabel(
            "Load a small draft model (e.g. Qwen-0.5B, 1.5B) alongside the base model "
            "to accelerate token generation via speculative decoding."
        )
        spec_desc.setObjectName("lbl-muted")
        spec_desc.setWordWrap(True)
        ap_layout.addWidget(spec_desc)

        self._draft_model_combo = QComboBox()
        self._draft_model_combo.setToolTip("Draft GGUF selector. Registry companion models appear first when configured.")
        self._draft_model_combo.currentTextChanged.connect(self._on_draft_combo_changed)
        ap_layout.addWidget(_row("Draft Selector", self._draft_model_combo))

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

        self._clear_draft_btn = QPushButton("clear draft")
        self._clear_draft_btn.setObjectName("btn-ghost")
        self._clear_draft_btn.setToolTip("Remove draft model and reload base model normally")
        self._clear_draft_btn.clicked.connect(self._clear_draft_model)

        spec_btn_row = QWidget()
        sbl = QHBoxLayout(spec_btn_row)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(8)
        sbl.addWidget(self._load_speculative_btn)
        sbl.addWidget(self._clear_draft_btn)
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


    def _start_model_load(
        self,
        model_path: str,
        *,
        adapter_name: str | None = None,
        draft_model_path: str | None = None,
        status_label: QLabel | None = None,
        speculative: bool = False,
        on_loaded=None,
        on_error=None,
        on_finished=None,
    ):
        from app.engine.model_load_thread import ModelLoadThread

        if getattr(self, "_model_load_thread", None) and self._model_load_thread.isRunning():
            if status_label is not None:
                status_label.setText("model load already running")
            return False

        controls = [
            getattr(self, "_load_model_btn", None),
            getattr(self, "_load_speculative_btn", None),
            getattr(self, "_clear_draft_btn", None),
            getattr(self, "_adapter_combo", None),
        ]
        for control in controls:
            if control is not None:
                control.setEnabled(False)

        if status_label is not None:
            label = os.path.basename(model_path)
            if draft_model_path:
                label = f"{label} + draft {os.path.basename(draft_model_path)}"
            status_label.setText(f"loading {label}...")
            status_label.setTextFormat(Qt.TextFormat.PlainText)

        thread = ModelLoadThread(
            model_path,
            adapter_name=adapter_name,
            draft_model_path=draft_model_path,
        )

        def handle_loaded(filename: str, loaded_adapter: str | None, draft_filename: str | None):
            self.state.model_name = filename
            self.state.adapter_name = loaded_adapter
            self.adapter_changed.emit(loaded_adapter or "")
            self._scan_models(force=True)
            self._scan_adapters(force=True)
            if hasattr(self, "_populate_registry"):
                self._populate_registry()
            if hasattr(self, "_model_path_input"):
                self._model_path_input.setText(os.path.join("data", "models", filename))

            if speculative and status_label is not None:
                from app.engine.model_loader import ModelLoader
                if ModelLoader.is_speculative():
                    status_label.setText(
                        f"<span style='color:#2DD4A0;'>Speculative decoding active — draft: "
                        f"{draft_filename}</span>"
                    )
                else:
                    status_label.setText(
                        "<span style='color:#FFD800;'>Draft model loaded but speculative kwarg "
                        "unsupported by this llama-cpp-python version. Standard inference active.</span>"
                    )
                status_label.setTextFormat(Qt.TextFormat.RichText)
            elif status_label is not None:
                status_label.setText(f"<span style='color:#2DD4A0;'>loaded {filename}</span>")
                status_label.setTextFormat(Qt.TextFormat.RichText)

            self._run_model_preflight_checks()
            if on_loaded is not None:
                on_loaded(filename, loaded_adapter, draft_filename)

        def handle_error(msg: str):
            if status_label is not None:
                status_label.setText(f"<span style='color:#FF5C7A;'>Error: {msg}</span>")
                status_label.setTextFormat(Qt.TextFormat.RichText)
            else:
                QMessageBox.critical(self, "Model Load Error", msg)
            if on_error is not None:
                on_error(msg)

        def handle_finished():
            for control in controls:
                if control is not None:
                    control.setEnabled(True)
            self._active_threads.discard(thread)
            if getattr(self, "_model_load_thread", None) is thread:
                self._model_load_thread = None
            if on_finished is not None:
                on_finished()

        thread.loaded.connect(handle_loaded)
        thread.error.connect(handle_error)
        thread.finished.connect(handle_finished)
        thread.finished.connect(thread.deleteLater)
        self._model_load_thread = thread
        self._active_threads.add(thread)
        thread.start()
        return True


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
        if ModelLoader.is_instance_locked():
            self._model_status.setText(
                "Cannot reload model while inference is active — "
                "stop the current generation first."
            )
            return
        self._start_model_load(path, status_label=self._model_status)


    def _browse_draft_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Draft GGUF model", "data/models", "GGUF (*.gguf);;All Files (*)"
        )
        if path:
            self._draft_model_input.setText(path)
            name = os.path.basename(path)
            idx = self._draft_model_combo.findText(name)
            if idx >= 0:
                self._draft_model_combo.setCurrentIndex(idx)


    def _on_draft_combo_changed(self, text: str):
        if not text or text == "none":
            self._draft_model_input.clear()
            return
        self._draft_model_input.setText(os.path.join("data", "models", text))


    def _load_speculative(self):
        if not self._speculative_toggle.isChecked():
            self._clear_draft_model()
            return

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

        self._start_model_load(
            base_path,
            draft_model_path=draft_path,
            status_label=self._draft_status,
            speculative=True,
        )


    def _clear_draft_model(self):
        from app.engine.model_loader import ModelLoader
        from app.engine import config_store as _cs
        try:
            ModelLoader.reset_instance()
            _cs.set_active_draft_model(None, enabled=False)
            self._speculative_toggle.setChecked(False)
            self._draft_model_combo.setCurrentIndex(0)
            self._draft_model_input.clear()
            self._draft_status.setText("Draft model cleared. Standard inference active.")
            self._run_model_preflight_checks()
        except Exception as e:
            self._draft_status.setText(f"<span style='color:#FF5C7A;'>Error: {e}</span>")
            self._draft_status.setTextFormat(Qt.TextFormat.RichText)


    def _populate_draft_selector(self):
        if not hasattr(self, "_draft_model_combo"):
            return

        active_name = self._get_active_model_name()
        companion = config_store.registry_draft_model_filename(active_name)
        draft_cfg = config_store.get_active_draft_model()
        preferred = draft_cfg.get("filename") or companion

        candidates: list[str] = []
        if companion:
            candidates.append(companion)
        if self._cached_models_list:
            for item in self._cached_models_list:
                name = item["filename"]
                if name != active_name and name not in candidates:
                    candidates.append(name)

        self._draft_model_combo.blockSignals(True)
        self._draft_model_combo.clear()
        self._draft_model_combo.addItem("none")
        for name in candidates:
            label = name
            self._draft_model_combo.addItem(label)

        selected = self._draft_model_combo.findText(preferred or "")
        self._draft_model_combo.setCurrentIndex(selected if selected >= 0 else 0)
        self._draft_model_combo.blockSignals(False)

        self._speculative_toggle.setChecked(bool(draft_cfg.get("enabled")))
        if preferred and selected >= 0:
            self._draft_model_input.setText(os.path.join("data", "models", preferred))
        elif not draft_cfg.get("enabled"):
            self._draft_model_input.clear()


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
            self._populate_draft_selector()
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
        self._populate_draft_selector()


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
        if ModelLoader.is_instance_locked():
            QMessageBox.warning(
                self, "Karl — Inference Active",
                "Cannot change adapter while inference is active.\n"
                "Stop the current generation first.",
            )
            return
        adapter_name = self._adapter_combo.currentText()
        if adapter_name == "none":
            adapter_name = None

        ModelLoader.reset_instance()
        self.state.adapter_name = adapter_name
        self.adapter_changed.emit(adapter_name or "")
        
        # Save to active model configuration, preserving the active filename
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


    def _reset_circuit_breaker(self):
        from app.engine.model_loader import ModelLoader
        ModelLoader.reset_circuit_breaker()
        if hasattr(self, "_cb_status_lbl") and self._cb_status_lbl is not None:
            self._cb_status_lbl.setText("<span style='color:#2DD4A0;'>Circuit Breaker: CLOSED</span>")
            self._cb_status_lbl.setTextFormat(Qt.TextFormat.RichText)
