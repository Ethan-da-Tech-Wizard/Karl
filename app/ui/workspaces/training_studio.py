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
import html
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QTextBrowser, QLabel, QListWidget,
    QListWidgetItem, QFrame, QFileDialog, QMessageBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit,
    QProgressBar, QCheckBox, QInputDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


def _section(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("section-header")
    return l


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


# ── training thread ───────────────────────────────────────────────────────────

class TrainingThread(QThread):
    loss = pyqtSignal(int, float)     # step, loss_val
    progress = pyqtSignal(int, int) # step, total_steps
    done = pyqtSignal(str)           # adapter_path
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, hf_base_dir: str, adapter_name: str, config: dict):
        super().__init__()
        self.hf_base_dir = hf_base_dir
        self.adapter_name = adapter_name
        self.config = config

    def run(self):
        try:
            import os
            import gc
            import torch

            # Configure PyTorch to prevent memory fragmentation
            os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
            
            # Clear CUDA cache before starting
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.log.emit("Preparing training dataset...")
            from datasets import load_dataset
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainerCallback
            from peft import LoraConfig, get_peft_model
            from trl import SFTConfig, SFTTrainer

            # Load dataset from curated examples
            dataset_path = "data/training/curated.jsonl"
            dataset = load_dataset("json", data_files=dataset_path, split="train")

            self.log.emit("Loading tokenizer and model...")
            tokenizer = AutoTokenizer.from_pretrained(self.hf_base_dir)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Set up QLoRA if requested and bitsandbytes is available
            use_qlora = self.config.get("use_qlora", False)
            device_map_to_use = {"": 0} if torch.cuda.is_available() else "auto"
            
            # Load model weights in float16 on GPU (saves 50% VRAM over default float32)
            torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

            if use_qlora:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                model = AutoModelForCausalLM.from_pretrained(
                    self.hf_base_dir,
                    quantization_config=bnb_config,
                    torch_dtype=torch_dtype,
                    device_map=device_map_to_use
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    self.hf_base_dir,
                    torch_dtype=torch_dtype,
                    device_map=device_map_to_use
                )

            self.log.emit("Configuring LoRA...")
            lora_config = LoraConfig(
                r=self.config.get("rank", 16),
                lora_alpha=self.config.get("alpha", 32),
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                lora_dropout=self.config.get("dropout", 0.05),
                bias="none",
                task_type="CAUSAL_LM"
            )

            # Prepare model for training
            model = get_peft_model(model, lora_config)
            
            # Disable caching to support gradient checkpointing during SFT
            model.config.use_cache = False

            adapter_path = os.path.join("data", "adapters", self.adapter_name)
            os.makedirs(adapter_path, exist_ok=True)

            training_args = SFTConfig(
                output_dir=os.path.join(adapter_path, "temp_checkpoints"),
                dataset_text_field="messages",
                max_length=512,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                learning_rate=self.config.get("lr", 2e-4),
                logging_steps=1,
                num_train_epochs=self.config.get("epochs", 3),
                save_strategy="no",
                report_to="none",
                fp16=True if torch.cuda.is_available() else False,
                gradient_checkpointing=True if torch.cuda.is_available() else False,
            )

            # Callback to report progress and loss
            thread_ref = self
            class TrainerProgressCallback(TrainerCallback):
                def on_log(self, args, state, control, logs=None, **kwargs):
                    if logs and "loss" in logs:
                        thread_ref.loss.emit(state.global_step, float(logs["loss"]))
                        thread_ref.log.emit(f"Step {state.global_step}: loss = {logs['loss']:.4f}")

                def on_step_end(self, args, state, control, **kwargs):
                    thread_ref.progress.emit(state.global_step, state.max_steps)

            self.log.emit("Starting SFTTrainer...")
            trainer = SFTTrainer(
                model=model,
                train_dataset=dataset,
                args=training_args,
                processing_class=tokenizer,
                callbacks=[TrainerProgressCallback()]
            )

            trainer.train()

            self.log.emit("Saving PyTorch adapter model weights...")
            trainer.model.save_pretrained(adapter_path)
            tokenizer.save_pretrained(adapter_path)

            # Clean up temp checkpoint folder
            import shutil
            temp_checkpoints = os.path.join(adapter_path, "temp_checkpoints")
            if os.path.exists(temp_checkpoints):
                shutil.rmtree(temp_checkpoints)

            # Convert to GGUF format
            self.log.emit("Converting PyTorch adapter to GGUF format...")
            import subprocess
            import sys
            cmd = [
                sys.executable,
                "app/utils/convert_lora_to_gguf.py",
                "--base", self.hf_base_dir,
                "--outfile", os.path.join(adapter_path, f"{self.adapter_name}.gguf"),
                adapter_path
            ]
            self.log.emit(f"Running: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"LoRA GGUF conversion failed: {res.stderr}")

            self.log.emit("Training and GGUF conversion completed successfully!")
            self.done.emit(adapter_path)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Re-collect garbage and empty CUDA cache to release VRAM to the OS
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass


class TrainingStudioWorkspace(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("workspace-root")
        self._active_threads = set()
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

        desc = QLabel(
            "Manage curated user feedback datasets and run model training. "
            "Export positive/negative ratings in SFT or DPO format, and train LoRA adapters locally."
        )
        desc.setObjectName("lbl-muted")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 8.5pt; margin-bottom: 6px; padding-left: 2px;")
        root.addWidget(desc)

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
        self._example_list.setToolTip("Double-click or select a curated example to preview")
        ll.addWidget(self._example_list, 1)

        del_btn = QPushButton("delete selected")
        del_btn.setObjectName("btn-danger")
        del_btn.setToolTip("Remove the selected curation example from training database")
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
        layout.setSpacing(16)

        cards = QWidget()
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)

        # SFT Panel
        sft_box = QWidget()
        sft_box.setObjectName("panel")
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
        dpo_box = QWidget()
        dpo_box.setObjectName("panel")
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

        layout.addWidget(_hline())
        layout.addWidget(_section("LORA CONFIG"))

        # config grid
        cfg = QWidget()
        cfg_l = QHBoxLayout(cfg)
        cfg_l.setContentsMargins(0, 0, 0, 0)
        cfg_l.setSpacing(20)

        def _row(label_text: str, widget: QWidget) -> QWidget:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(12)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            rl.addWidget(lbl)
            rl.addWidget(widget)
            rl.addStretch()
            return row

        self._base_model_combo = QComboBox()
        self._base_model_combo.setMinimumWidth(260)
        self._base_model_combo.setToolTip("Select the local HuggingFace base model weights to train")
        self._base_model_combo.currentIndexChanged.connect(self._check_deps)

        self._rank_spin = QSpinBox()
        self._rank_spin.setRange(1, 256)
        self._rank_spin.setValue(16)
        self._rank_spin.setFixedWidth(80)
        self._rank_spin.setToolTip("LoRA factorization rank. Higher increases model capacity but uses more VRAM.")

        self._alpha_spin = QSpinBox()
        self._alpha_spin.setRange(1, 512)
        self._alpha_spin.setValue(32)
        self._alpha_spin.setFixedWidth(80)
        self._alpha_spin.setToolTip("LoRA scaling parameter. Controls scaling of adapter weight updates.")

        self._dropout_spin = QDoubleSpinBox()
        self._dropout_spin.setRange(0.0, 0.5)
        self._dropout_spin.setSingleStep(0.05)
        self._dropout_spin.setValue(0.05)
        self._dropout_spin.setFixedWidth(80)
        self._dropout_spin.setToolTip("LoRA dropout probability. Helps prevent overfitting.")

        self._lr_spin = QDoubleSpinBox()
        self._lr_spin.setDecimals(6)
        self._lr_spin.setRange(1e-6, 1e-2)
        self._lr_spin.setSingleStep(1e-5)
        self._lr_spin.setValue(2e-4)
        self._lr_spin.setFixedWidth(100)
        self._lr_spin.setToolTip("Training step step size (optimizer learning rate).")

        self._epochs_spin = QSpinBox()
        self._epochs_spin.setRange(1, 20)
        self._epochs_spin.setValue(3)
        self._epochs_spin.setFixedWidth(80)
        self._epochs_spin.setToolTip("Number of full passes over the training dataset.")

        self._qlora_check = QCheckBox("4-bit QLoRA  (requires bitsandbytes)")
        self._qlora_check.setChecked(True)
        self._qlora_check.setToolTip("Enable 4-bit quantized QLoRA training to reduce VRAM requirements")

        # Base model row with Browse and Add buttons
        base_model_row = QWidget()
        bm_layout = QHBoxLayout(base_model_row)
        bm_layout.setContentsMargins(0, 2, 0, 2)
        bm_layout.setSpacing(12)
        lbl = QLabel("base model")
        lbl.setFixedWidth(80)
        bm_layout.addWidget(lbl)
        bm_layout.addWidget(self._base_model_combo)
        
        browse_btn = QPushButton("browse...")
        browse_btn.setToolTip("Select a local HuggingFace weights directory")
        browse_btn.clicked.connect(self._browse_hf_model)
        bm_layout.addWidget(browse_btn)
        
        add_repo_btn = QPushButton("add repo...")
        add_repo_btn.setToolTip("Enter a HuggingFace repository ID to train (e.g. Qwen/Qwen2.5-Coder-1.5B)")
        add_repo_btn.clicked.connect(self._add_hf_repo)
        bm_layout.addWidget(add_repo_btn)
        bm_layout.addStretch()
        
        layout.addWidget(base_model_row)

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

        # VRAM warning info panel
        vram_info = QWidget()
        vram_info.setObjectName("panel")
        vram_info.setStyleSheet("background: rgba(240, 176, 48, 0.05); border: 1px solid rgba(240, 176, 48, 0.2); border-radius: 4px;")
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
        layout.addWidget(vram_info)
        layout.addWidget(_hline())

        self._adapter_name_input = QLineEdit()
        self._adapter_name_input.setPlaceholderText("adapter name (saved to data/adapters/)")
        self._adapter_name_input.setToolTip("Enter folder name where the compiled model adapter will be saved")
        layout.addWidget(self._adapter_name_input)

        self._train_btn = QPushButton("▶ begin training")
        self._train_btn.setObjectName("btn-primary")
        self._train_btn.setToolTip("Start adapter SFT training thread on the local GPU")
        self._train_btn.clicked.connect(self._begin_training)
        layout.addWidget(self._train_btn)
        self._check_deps()

        self._train_progress = QProgressBar()
        self._train_progress.setVisible(False)
        layout.addWidget(self._train_progress)

        self._train_log = QTextBrowser()
        self._train_log.setObjectName("reasoning-view")
        self._train_log.setFixedHeight(120)
        self._train_log.setPlaceholderText("training log...")
        layout.addWidget(self._train_log)

        layout.addStretch()
        return w

    # ── logic ─────────────────────────────────────────────────────────────────

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
        self._example_list.clear()
        for ex in self.state.curator.get_all_examples():
            source = ex.get("source", "unknown")
            if source == "thumbs_up":
                tag = "✓ positive"
            elif source == "corrected":
                tag = "✎ corrected"
            elif source == "thumbs_down":
                tag = "✗ negative"
            else:
                tag = f"● {source}"
            
            messages = ex.get("messages", [])
            user_text = ""
            for m in messages:
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break
            preview = user_text[:60]
            item = QListWidgetItem(f"[{tag:<10}]  {preview}")
            self._example_list.addItem(item)
            
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
        name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
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
        from app.engine.model_loader import ModelLoader
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

    def _on_example_selected(self, row: int):
        if row < 0:
            return
        examples = self.state.curator.get_all_examples()
        if row >= len(examples):
            return
        ex = examples[row]
        
        messages = ex.get("messages", [])
        timestamp = ex.get("timestamp", "")
        source = ex.get("source", "unknown")
        
        html_parts = [
            f"<div style='font-size:9pt;color:#9090A8;margin-bottom:12px;border-bottom:1px solid #252535;padding-bottom:6px;'>"
            f"Source: <b style='color:#00C2FF;'>{source}</b> &middot; Created: {timestamp}"
            f"</div>"
        ]
        
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            
            color = "#00C2FF" if role == "SYSTEM" else ("#2DD4A0" if role == "ASSISTANT" else "#E4E4F0")
            bg = "#14141F" if role == "SYSTEM" else ("#0D0D16" if role == "ASSISTANT" else "#1C1C2A")
            border = "#252535" if role == "SYSTEM" else ("#1A1A25" if role == "ASSISTANT" else "#383850")
            
            html_parts.append(
                f"<div style='margin-bottom:10px;'>"
                f"<div style='font-size:7.5pt;font-weight:bold;color:#505068;margin-bottom:3px;letter-spacing:1px;'>{role}</div>"
                f"<div style='background:{bg};border:1px solid {border};border-radius:4px;padding:8px 12px;color:{color};font-size:9.5pt;white-space:pre-wrap;'>{html.escape(content)}</div>"
                f"</div>"
            )
            
        self._detail_view.setHtml("".join(html_parts))

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
                out_path = self.state.curator.export_dpo(path)
            self._export_status.setText(f"saved: {out_path}")
        except Exception as e:
            self._export_status.setText(f"error: {e}")

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
        from core.hardware_scout import get_hardware_profile
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
        from app.engine.model_loader import ModelLoader
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
        
    def _on_train_loss(self, step: int, value: float):
        # Optional: update a plot or stat in the future
        pass

    def _on_train_progress(self, current: int, total: int):
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
