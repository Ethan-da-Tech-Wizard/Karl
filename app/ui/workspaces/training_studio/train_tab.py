import os
import json
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QLabel, QFileDialog, QMessageBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QLineEdit, QProgressBar, QCheckBox, QGridLayout,
    QFrame, QInputDialog
)

from app.ui.widgets.glow_panel import GlowPanel
from app.ui.workspaces.training_studio.threads import TrainingThread
from app.engine.model_loader import ModelLoader
from core.hardware_scout import get_hardware_profile

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section-header")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class TrainTab(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._active_threads = set()
        self._thread = None
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

        left_layout.addWidget(_section("LORA CONFIGURATION"))

        # We'll use a QGridLayout for hyperparams
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)

        # Base model row: we can use a QHBoxLayout inside the grid
        bm_row = QWidget()
        bm_lay = QHBoxLayout(bm_row)
        bm_lay.setContentsMargins(0, 0, 0, 0)
        bm_lay.setSpacing(6)
        
        self._base_model_combo = QComboBox()
        self._base_model_combo.setToolTip("Select the local HuggingFace base model weights to train")
        self._base_model_combo.currentIndexChanged.connect(self._check_deps)
        bm_lay.addWidget(self._base_model_combo, 1)

        browse_btn = QPushButton("browse...")
        browse_btn.setToolTip("Select a local HuggingFace weights directory")
        browse_btn.clicked.connect(self._browse_hf_model)
        bm_lay.addWidget(browse_btn)

        add_repo_btn = QPushButton("add repo...")
        add_repo_btn.setToolTip("Enter a HuggingFace repository ID to train (e.g. Qwen/Qwen2.5-Coder-1.5B)")
        add_repo_btn.clicked.connect(self._add_hf_repo)
        bm_lay.addWidget(add_repo_btn)

        grid.addWidget(QLabel("Base Model:"), 0, 0)
        grid.addWidget(bm_row, 0, 1, 1, 3)

        # Rank (SpinBox)
        self._rank_spin = QSpinBox()
        self._rank_spin.setRange(1, 256)
        self._rank_spin.setValue(16)
        self._rank_spin.setToolTip("LoRA factorization rank. Higher increases model capacity but uses more VRAM.")
        grid.addWidget(QLabel("Rank:"), 1, 0)
        grid.addWidget(self._rank_spin, 1, 1)

        # Alpha (SpinBox)
        self._alpha_spin = QSpinBox()
        self._alpha_spin.setRange(1, 512)
        self._alpha_spin.setValue(32)
        self._alpha_spin.setToolTip("LoRA scaling parameter. Controls scaling of adapter weight updates.")
        grid.addWidget(QLabel("Alpha:"), 1, 2)
        grid.addWidget(self._alpha_spin, 1, 3)

        # Dropout
        self._dropout_spin = QDoubleSpinBox()
        self._dropout_spin.setRange(0.0, 0.5)
        self._dropout_spin.setSingleStep(0.05)
        self._dropout_spin.setValue(0.05)
        self._dropout_spin.setToolTip("LoRA dropout probability. Helps prevent overfitting.")
        grid.addWidget(QLabel("Dropout:"), 2, 0)
        grid.addWidget(self._dropout_spin, 2, 1)

        # Epochs
        self._epochs_spin = QSpinBox()
        self._epochs_spin.setRange(1, 20)
        self._epochs_spin.setValue(3)
        self._epochs_spin.setToolTip("Number of full passes over the training dataset.")
        grid.addWidget(QLabel("Epochs:"), 2, 2)
        grid.addWidget(self._epochs_spin, 2, 3)

        # LR
        self._lr_spin = QDoubleSpinBox()
        self._lr_spin.setDecimals(6)
        self._lr_spin.setRange(1e-6, 1e-2)
        self._lr_spin.setSingleStep(1e-5)
        self._lr_spin.setValue(2e-4)
        self._lr_spin.setToolTip("Training step size (optimizer learning rate).")
        grid.addWidget(QLabel("Learning Rate:"), 3, 0)
        grid.addWidget(self._lr_spin, 3, 1)

        # QLoRA Checkbox
        self._qlora_check = QCheckBox("4-bit QLoRA")
        self._qlora_check.setChecked(True)
        self._qlora_check.setToolTip("Enable 4-bit quantized QLoRA training to reduce VRAM requirements")
        grid.addWidget(self._qlora_check, 3, 2, 1, 2)

        left_layout.addLayout(grid)
        left_layout.addWidget(_hline())

        # Adapter Name Input
        left_layout.addWidget(QLabel("Adapter Save Name:"))
        self._adapter_name_input = QLineEdit()
        self._adapter_name_input.setPlaceholderText("e.g., my_coder_lora")
        self._adapter_name_input.setToolTip("Enter folder name where the compiled model adapter will be saved")
        self._adapter_name_input.textChanged.connect(self._update_export_path_preview)
        left_layout.addWidget(self._adapter_name_input)

        self._export_path_lbl = QLabel("Export Path: data/adapters/")
        self._export_path_lbl.setObjectName("lbl-muted")
        self._export_path_lbl.setStyleSheet("font-size: 8pt; padding-left: 2px;")
        left_layout.addWidget(self._export_path_lbl)


        # Train Button
        self._train_btn = QPushButton("▶ begin training")
        self._train_btn.setObjectName("btn-primary")
        self._train_btn.setFixedHeight(36)
        self._train_btn.setToolTip("Start adapter SFT training thread on the local GPU")
        self._train_btn.clicked.connect(self._begin_training)
        left_layout.addWidget(self._train_btn)

        # Progress bar
        self._train_progress = QProgressBar()
        self._train_progress.setVisible(False)
        left_layout.addWidget(self._train_progress)

        left_layout.addStretch()
        layout.addWidget(left_col, 1)

        # Right Column: Guide & Output Logs
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # dependency check card
        dep_box = GlowPanel(self.state)
        dep_lay = QVBoxLayout(dep_box)
        dep_lay.setContentsMargins(12, 10, 12, 10)
        dep_lay.setSpacing(4)
        dep_lay.addWidget(_section("DEPENDENCIES & MODEL STATUS"))
        self._deps_lbl = QLabel("")
        self._deps_lbl.setObjectName("lbl-muted")
        self._deps_lbl.setWordWrap(True)
        self._deps_lbl.setStyleSheet("font-size: 9pt; line-height: 1.3;")
        dep_lay.addWidget(self._deps_lbl)
        right_layout.addWidget(dep_box)

        # VRAM warning info panel
        vram_info = GlowPanel(self.state)
        vram_info.setStyleSheet("background: rgba(240, 176, 48, 0.03); border: 1px solid rgba(240, 176, 48, 0.15); border-radius: 4px;")
        vil = QVBoxLayout(vram_info)
        vil.setContentsMargins(12, 10, 12, 10)
        
        warn_text = (
            "⚠️ <b>Hardware Requirement Guide:</b><br>"
            "• <b>1.5B Model:</b> ~6 GB VRAM (4-bit QLoRA) / ~10 GB VRAM (16-bit LoRA)<br>"
            "• <b>7B / 8B Model:</b> ~14 GB VRAM (4-bit QLoRA) / ~22 GB VRAM (16-bit LoRA)<br>"
            "Ensure you have PyTorch-compatible CUDA drivers and sufficient free GPU memory."
        )
        warn_lbl = QLabel(warn_text)
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet("font-size: 8.5pt; color: #F0B030; line-height: 1.4;")
        vil.addWidget(warn_lbl)
        right_layout.addWidget(vram_info)

        # Training log
        log_box = QWidget()
        log_lay = QVBoxLayout(log_box)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.setSpacing(4)
        log_lay.addWidget(_section("TRAINING SYSTEM LOGS"))
        self._train_log = QTextBrowser()
        self._train_log.setObjectName("reasoning-view")
        self._train_log.setPlaceholderText("Logs will stream here when training begins...")
        self._train_log.setStyleSheet("font-family: monospace; font-size: 9pt;")
        log_lay.addWidget(self._train_log)
        
        right_layout.addWidget(log_box, 1)

        layout.addWidget(right_col, 1)
        self._check_deps()

    def refresh(self):
        self._refresh_base_models()

    def _load_custom_models(self) -> list[dict]:
        path = "data/custom_train_models.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_custom_model(self, display_name: str, item_data: str, is_path: bool):
        custom_models = self._load_custom_models()
        # Avoid duplicates
        if any(item.get("data") == item_data for item in custom_models):
            return
        custom_models.append({
            "display": display_name,
            "data": item_data,
            "is_path": is_path
        })
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/custom_train_models.json", "w") as f:
                json.dump(custom_models, f, indent=4)
        except Exception:
            pass

    def _browse_hf_model(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select local HuggingFace model directory", "data/hf_models"
        )
        if not path:
            return
            
        # Check if there are safetensors or bin files in the selected directory
        try:
            files = os.listdir(path)
            has_weights = any(f.endswith(".safetensors") or f.endswith(".bin") for f in files)
            if not has_weights:
                QMessageBox.warning(
                    self, "Missing weights",
                    "The selected directory does not seem to contain model weights (.safetensors or .bin files)."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error reading directory", str(e))
            
        # Add to combobox and select
        name = os.path.basename(path)
        self._save_custom_model(name, path, is_path=True)
        self._refresh_base_models()
        
        # Select the newly added path
        for idx in range(self._base_model_combo.count()):
            if self._base_model_combo.itemData(idx) == path:
                self._base_model_combo.setCurrentIndex(idx)
                break

    def _add_hf_repo(self):
        repo_id, ok = QInputDialog.getText(
            self, "Add HuggingFace Repository ID",
            "Enter HuggingFace Repository ID (e.g. Qwen/Qwen2.5-Coder-1.5B):"
        )
        if not ok or not repo_id.strip():
            return
            
        repo_id = repo_id.strip()
        self._save_custom_model(repo_id, repo_id, is_path=False)
        self._refresh_base_models()
        
        # Select the newly added repo
        for idx in range(self._base_model_combo.count()):
            if self._base_model_combo.itemData(idx) == repo_id:
                self._base_model_combo.setCurrentIndex(idx)
                break

    def _refresh_base_models(self):
        self._base_model_combo.blockSignals(True)
        self._base_model_combo.clear()
        
        standard_models = [
            "DeepSeek-R1-Distill-Qwen-1.5B",
            "DeepSeek-R1-Distill-Qwen-7B",
            "DeepSeek-R1-Distill-Llama-8B",
            "DeepSeek-R1-Distill-Qwen-14B",
            "DeepSeek-R1-Distill-Llama-70B",
            "deepseek-r1-1.5b-hf",
        ]
        
        # Scan data/hf_models for any other directories containing weights
        hf_dir = os.path.join("data", "hf_models")
        scanned_folders = []
        if os.path.exists(hf_dir):
            try:
                for name in os.listdir(hf_dir):
                    path = os.path.join(hf_dir, name)
                    if os.path.isdir(path) and name not in standard_models:
                        files = os.listdir(path)
                        if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                            scanned_folders.append(name)
            except Exception:
                pass
                
        all_options = standard_models + sorted(scanned_folders)
        
        for opt in all_options:
            local_path = os.path.join("data", "hf_models", opt)
            exists = False
            if os.path.exists(local_path):
                try:
                    files = os.listdir(local_path)
                    if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                        exists = True
                except Exception:
                    pass
            display_name = f"{opt}  (Ready)" if exists else f"{opt}  (Missing weights)"
            self._base_model_combo.addItem(display_name, opt)
            
        # Append persisted custom models
        for custom in self._load_custom_models():
            opt = custom.get("data")
            is_path = custom.get("is_path", False)
            
            # Skip if already exists in standard/scanned
            already_exists = False
            for idx in range(self._base_model_combo.count()):
                if self._base_model_combo.itemData(idx) == opt:
                    already_exists = True
                    break
            if already_exists:
                continue
                
            exists = False
            if is_path:
                if os.path.exists(opt):
                    try:
                        files = os.listdir(opt)
                        if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                            exists = True
                    except Exception:
                        pass
            else:
                basename = opt.split("/")[-1] if "/" in opt else opt
                local_path = os.path.join("data", "hf_models", basename)
                if os.path.exists(local_path):
                    try:
                        files = os.listdir(local_path)
                        if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                            exists = True
                    except Exception:
                        pass
            status = "Ready" if exists else "Missing weights"
            display_name = f"Custom: {custom.get('display')}  ({status})"
            self._base_model_combo.addItem(display_name, opt)
            
        # Try to select the one matching the active gguf model
        active_gguf = ModelLoader.model_name()
        for idx in range(self._base_model_combo.count()):
            opt = self._base_model_combo.itemData(idx)
            if opt and (
                ("1.5b" in opt.lower() and "1.5b" in active_gguf.lower()) or
                ("7b" in opt.lower() and "7b" in active_gguf.lower()) or
                ("8b" in opt.lower() and "8b" in active_gguf.lower()) or
                ("14b" in opt.lower() and "14b" in active_gguf.lower()) or
                ("70b" in opt.lower() and "70b" in active_gguf.lower())
            ):
                self._base_model_combo.setCurrentIndex(idx)
                break
                
        self._base_model_combo.blockSignals(False)
        self._check_deps()

    def _get_hf_model_path(self) -> tuple[str | None, str]:
        idx = self._base_model_combo.currentIndex()
        if idx < 0:
            return None, "unknown"
        selected_folder = self._base_model_combo.itemData(idx)
        if not selected_folder:
            return None, "unknown"
            
        # 1. Check if absolute path
        if os.path.isabs(selected_folder):
            if os.path.exists(selected_folder):
                try:
                    files = os.listdir(selected_folder)
                    if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                        return selected_folder, os.path.basename(selected_folder)
                except Exception:
                    pass
            return None, os.path.basename(selected_folder)
            
        # 2. Check if selected_folder is a full repo ID (contains a slash)
        if "/" in selected_folder:
            repo_id = selected_folder
            basename = selected_folder.split("/")[-1]
        else:
            basename = selected_folder
            if "1.5b" in selected_folder.lower():
                repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
            elif "7b" in selected_folder.lower():
                repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
            elif "8b" in selected_folder.lower() or "llama-8b" in selected_folder.lower():
                repo_id = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
            elif "14b" in selected_folder.lower():
                repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
            elif "70b" in selected_folder.lower():
                repo_id = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
            else:
                repo_id = f"deepseek-ai/{selected_folder}"
                
        local_dir = os.path.join("data", "hf_models", basename)
        if os.path.exists(local_dir):
            try:
                files = os.listdir(local_dir)
                if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                    return local_dir, repo_id
            except Exception:
                pass
                
        return None, repo_id

    def _check_deps(self):
        missing = []
        for pkg in ("peft", "trl", "transformers", "datasets", "gguf"):
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
                
        hf_path, repo_id = self._get_hf_model_path()
        
        if missing:
            self._deps_lbl.setText(
                f"In-app training requires: {', '.join(missing)}\n"
                f"Install with:  pip install {' '.join(missing)}"
            )
            self._deps_lbl.setObjectName("lbl-red")
            self._train_btn.setEnabled(False)
        elif hf_path is None:
            # Check if it was an absolute path
            idx = self._base_model_combo.currentIndex()
            selected_folder = self._base_model_combo.itemData(idx) if idx >= 0 else None
            
            if selected_folder and os.path.isabs(selected_folder):
                self._deps_lbl.setText(
                    f"Selected directory '{selected_folder}' is missing model weights (.safetensors or .bin).\n"
                    f"Please choose a directory containing HuggingFace model weights."
                )
            else:
                basename = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                local_dir = f"data/hf_models/{basename}"
                self._deps_lbl.setText(
                    f"HuggingFace model weights for '{repo_id}' are missing in '{local_dir}'.\n"
                    f"To download them privately and enable training, run in terminal:\n"
                    f"huggingface-cli download {repo_id} --local-dir {local_dir}"
                )
            self._deps_lbl.setObjectName("lbl-red")
            self._train_btn.setEnabled(False)
        else:
            self._deps_lbl.setText(
                f"✓ training dependencies available\n"
                f"✓ base HF model weights ready: {os.path.basename(hf_path)}"
            )
            self._deps_lbl.setObjectName("lbl-green")
            self._train_btn.setEnabled(True)

    def _begin_training(self):
        adapter_name = self._adapter_name_input.text().strip()
        if not adapter_name:
            self._train_log.append("set an adapter name first.")
            return

        # Sanitize adapter name for file path
        adapter_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', adapter_name)
        self._adapter_name_input.setText(adapter_name)

        # Preflight dataset validation
        curated_file = "data/training/curated.jsonl"
        if not os.path.exists(curated_file) or os.path.getsize(curated_file) == 0:
            self._train_log.append("Training failed: Ingestion file is empty.")
            QMessageBox.warning(self, "Validation Failed", "The dataset is empty. Curate some examples first.")
            return
            
        try:
            with open(curated_file, "r") as f:
                for line_idx, line in enumerate(f):
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    if "messages" not in obj:
                        raise ValueError(f"Line {line_idx+1}: Missing required 'messages' key for SFT training.")
        except Exception as e:
            self._train_log.append(f"Training failed: Dataset validation failed:\n{e}")
            QMessageBox.critical(self, "Dataset Validation Error", f"curated.jsonl format validation failed:\n{e}")
            return

        examples = self.state.curator.get_all_examples()
        if len(examples) < 5:
            self._train_log.append(
                f"need at least 5 examples (have {len(examples)}). "
                "curate more in the workbench."
            )
            return


        hf_base_dir, repo_id = self._get_hf_model_path()
        if not hf_base_dir:
            self._train_log.append(f"Base HuggingFace weights for {repo_id} not found locally.")
            return

        # VRAM Safety Guard Check
        hw = get_hardware_profile()
        vram = hw.get("vram_gb", 0.0)
        
        # Determine model size category from folder name or repo name
        model_name_lower = hf_base_dir.lower()
        is_large = any(term in model_name_lower for term in ["7b", "8b", "14b", "70b"])
        use_qlora = self._qlora_check.isChecked()
        
        if is_large and not use_qlora and isinstance(vram, (int, float)) and vram < 16.0:
            QMessageBox.critical(
                self, "VRAM Safety Guard",
                f"You are attempting to train a large model ({os.path.basename(hf_base_dir)}) in full 16-bit precision.\n\n"
                f"Your GPU has {vram:.1f} GB of VRAM. Training a 7B/8B model in 16-bit requires at least 16 GB of VRAM just to load the model weights, "
                f"which will instantly crash with CUDA Out of Memory.\n\n"
                f"Please check '4-bit QLoRA' to enable memory-efficient training."
            )
            return

        self._train_btn.setEnabled(False)
        self._train_progress.setVisible(True)
        self._train_progress.setRange(0, 100)
        self._train_progress.setValue(0)
        
        self._train_log.clear()
        self._train_log.append("Releasing GPU VRAM from active inference engine...")
        ModelLoader.reset_instance()
        
        self._train_log.append("Initializing local training pipeline...")

        config = {
            "rank": self._rank_spin.value(),
            "alpha": self._alpha_spin.value(),
            "dropout": self._dropout_spin.value(),
            "lr": self._lr_spin.value(),
            "epochs": self._epochs_spin.value(),
            "use_qlora": self._qlora_check.isChecked()
        }

        # Start thread
        self._thread = TrainingThread(hf_base_dir, adapter_name, config)
        self._active_threads.add(self._thread)
        self._thread.finished.connect(
            lambda t=self._thread: self._active_threads.discard(t)
        )
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.log.connect(self._on_train_log)
        self._thread.loss.connect(self._on_train_loss)
        self._thread.progress.connect(self._on_train_progress)
        self._thread.done.connect(self._on_train_done)
        self._thread.error.connect(self._on_train_error)
        self._thread.start()

    def _on_train_log(self, text: str):
        self._train_log.append(text)
        
    def _on_train_loss(self, step: int, value: float, epoch: float):
        self._train_log.append(f"[METRIC] Step {step} | Epoch {epoch:.2f} | Loss: {value:.4f}")

    def _on_train_progress(self, current: int, total: int, epoch: float):
        if total > 0:
            percentage = int((current / total) * 100)
            self._train_progress.setValue(percentage)
            
    def _on_train_done(self, adapter_path: str):
        self._train_btn.setEnabled(True)
        self._train_progress.setVisible(False)
        QMessageBox.information(
            self, "Training Complete",
            f"Trained adapter successfully saved and converted to GGUF in:\n{adapter_path}"
        )
        self._adapter_name_input.clear()
        self._check_deps()
        
    def _on_train_error(self, msg: str):
        self._train_btn.setEnabled(True)
        self._train_progress.setVisible(False)
        self._train_log.append(f"\n[ERROR] Training failed:\n{msg}")
        QMessageBox.critical(self, "Training Error", f"Training encountered an error:\n{msg}")
        self._check_deps()

    def _update_export_path_preview(self, name):
        name = name.strip()
        if not name:
            self._export_path_lbl.setText("Export Path: data/adapters/")
        else:
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            self._export_path_lbl.setText(f"Export Path: data/adapters/{safe_name}/")
