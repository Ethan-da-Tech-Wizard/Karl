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
    QProgressBar, QCheckBox,
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
            self.log.emit("Preparing training dataset...")
            import json
            import torch
            from datasets import load_dataset
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, BitsAndBytesConfig, TrainerCallback
            from peft import LoraConfig, get_peft_model
            from trl import SFTTrainer

            # Load dataset from curated examples
            dataset_path = "data/training/curated.jsonl"
            dataset = load_dataset("json", data_files=dataset_path, split="train")

            self.log.emit("Loading tokenizer and model...")
            tokenizer = AutoTokenizer.from_pretrained(self.hf_base_dir)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Set up QLoRA if requested and bitsandbytes is available
            use_qlora = self.config.get("use_qlora", False)
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
                    device_map="auto"
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    self.hf_base_dir,
                    device_map="auto"
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

            adapter_path = os.path.join("data", "adapters", self.adapter_name)
            os.makedirs(adapter_path, exist_ok=True)

            training_args = TrainingArguments(
                output_dir=os.path.join(adapter_path, "temp_checkpoints"),
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                learning_rate=self.config.get("lr", 2e-4),
                logging_steps=1,
                num_train_epochs=self.config.get("epochs", 3),
                save_strategy="no",
                report_to="none",
                fp16=True if torch.cuda.is_available() else False,
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
                dataset_text_field="messages",
                max_seq_length=512,
                tokenizer=tokenizer,
                args=training_args,
                callbacks=[TrainerProgressCallback()]
            )

            trainer.train()

            self.log.emit("Saving PyTorch adapter model weights...")
            trainer.model.save_pretrained(adapter_path)
            trainer.tokenizer.save_pretrained(adapter_path)

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
        layout.setSpacing(12)

        # SFT Panel
        sft_box = QWidget()
        sft_box.setObjectName("panel")
        sft_l = QVBoxLayout(sft_box)
        sft_l.setContentsMargins(12, 12, 12, 12)
        sft_l.setSpacing(8)
        sft_l.addWidget(_section("UNSLOTH / SFT FORMAT"))
        sft_l.addWidget(QLabel(
            "Exports curated examples in Unsloth-compatible JSONL.\n"
            "Fields: messages (compatible with HF chat format)."
        ))
        sft_btn = QPushButton("export SFT  →  unsloth_sft.jsonl")
        sft_btn.setObjectName("btn-primary")
        sft_btn.clicked.connect(lambda: self._export("sft"))
        sft_l.addWidget(sft_btn)
        layout.addWidget(sft_box)

        # DPO Panel
        dpo_box = QWidget()
        dpo_box.setObjectName("panel")
        dpo_l = QVBoxLayout(dpo_box)
        dpo_l.setContentsMargins(12, 12, 12, 12)
        dpo_l.setSpacing(8)
        dpo_l.addWidget(_section("DPO FORMAT"))
        dpo_l.addWidget(QLabel(
            "Exports thumbs-up (chosen) vs thumbs-down (rejected) pairs.\n"
            "Requires at least one example of each type."
        ))
        dpo_btn = QPushButton("export DPO  →  unsloth_dpo.jsonl")
        dpo_btn.clicked.connect(lambda: self._export("dpo"))
        dpo_l.addWidget(dpo_btn)
        layout.addWidget(dpo_box)

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
        self._check_deps()  # now safe — _train_btn exists

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
            messages = ex.get("messages", [])
            user_text = ""
            for m in messages:
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break
            preview = user_text[:60]
            item = QListWidgetItem(f"[{source}]  {preview}")
            self._example_list.addItem(item)

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
        from app.engine.model_loader import ModelLoader
        active_gguf = ModelLoader.model_name()
        
        # Determine expected Hugging Face repository based on active GGUF filename
        if "1.5b" in active_gguf.lower():
            repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
            folder_name = "DeepSeek-R1-Distill-Qwen-1.5B"
        elif "7b" in active_gguf.lower():
            repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
            folder_name = "DeepSeek-R1-Distill-Qwen-7B"
        elif "14b" in active_gguf.lower():
            repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
            folder_name = "DeepSeek-R1-Distill-Qwen-14B"
        elif "70b" in active_gguf.lower():
            repo_id = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
            folder_name = "DeepSeek-R1-Distill-Llama-70B"
        else:
            repo_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
            folder_name = "DeepSeek-R1-Distill-Qwen-1.5B"
            
        local_dir = os.path.join("data", "hf_models", folder_name)
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
            local_dir = f"data/hf_models/{os.path.basename(repo_id)}"
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

        self._train_btn.setEnabled(False)
        self._train_progress.setVisible(True)
        self._train_progress.setRange(0, 100)
        self._train_progress.setValue(0)
        
        self._train_log.clear()
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
