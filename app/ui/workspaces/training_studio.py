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
    QProgressBar, QCheckBox, QInputDialog, QGridLayout,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient
from app.ui.widgets.glow_panel import GlowPanel
from app.engine.mini_train_thread import MiniTrainThread
from app.engine.mini_transformer import MiniGPT, CharTokenizer
import torch
import traceback


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
    loss = pyqtSignal(int, float, float)     # step, loss_val, epoch
    progress = pyqtSignal(int, int, float)   # step, total_steps, epoch
    done = pyqtSignal(str)                   # adapter_path
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
                        loss_val = float(logs["loss"])
                        epoch_val = state.epoch if state.epoch is not None else 0.0
                        thread_ref.loss.emit(state.global_step, loss_val, epoch_val)
                        thread_ref.log.emit(f"Step {state.global_step}/{state.max_steps} | Epoch {epoch_val:.2f} | Loss: {loss_val:.4f}")

                def on_step_end(self, args, state, control, **kwargs):
                    epoch_val = state.epoch if state.epoch is not None else 0.0
                    thread_ref.progress.emit(state.global_step, state.max_steps, epoch_val)

            self.log.emit("Starting SFTTrainer...")
            trainer = SFTTrainer(
                model=model,
                train_dataset=dataset,
                args=training_args,
                processing_class=tokenizer,
                callbacks=[TrainerProgressCallback()]
            )

            trainer.train()

            # Save training history
            try:
                history_path = os.path.join(adapter_path, "train_history.json")
                with open(history_path, "w", encoding="utf-8") as fh:
                    json.dump(trainer.state.log_history, fh, indent=2)
                self.log.emit(f"Saved training history to {history_path}")
            except Exception as he:
                self.log.emit(f"Failed to save training history: {he}")

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


class AutoTrainThread(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, topic: str, adapter_name: str, config: dict):
        super().__init__()
        self.topic = topic
        self.adapter_name = adapter_name
        self.config = config
        self.process = None

    def run(self):
        import subprocess
        import sys
        
        cmd = [
            sys.executable,
            "auto_train.py",
            "--topic", self.topic,
            "--adapter_name", self.adapter_name,
            "--count", str(self.config.get("count", 15)),
            "--epochs", str(self.config.get("epochs", 3)),
            "--lr", str(self.config.get("lr", 2e-4)),
            "--rank", str(self.config.get("rank", 16)),
            "--alpha", str(self.config.get("alpha", 32)),
            "--dropout", str(self.config.get("dropout", 0.05)),
        ]
        if self.config.get("use_qlora", True):
            cmd.append("--qlora")

        self.log.emit(f"Launching Auto-Train Swarm Process: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            while True:
                if self.isInterruptionRequested():
                    self.process.terminate()
                    self.log.emit("Auto-training execution interrupted by user.")
                    break
                    
                line = self.process.stdout.readline()
                if not line:
                    break
                self.log.emit(line.strip())
                
            rc = self.process.wait()
            if rc == 0:
                self.done.emit(self.adapter_name)
            else:
                self.error.emit(f"Auto-train process exited with code {rc}")
        except Exception as e:
            self.error.emit(str(e))


class _FlywheelStatsThread(QThread):
    """Reads flywheel stats off the main thread to avoid blocking the UI."""
    stats_ready = pyqtSignal(dict)

    def run(self):
        stats = {}
        try:
            # Traces
            import glob
            trace_files = glob.glob("data/logs/traces/*.jsonl")
            total_traces = 0
            for fp in trace_files:
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        total_traces += sum(1 for line in f if line.strip())
                except Exception:
                    pass
            stats["traces_total"] = str(total_traces)

            # Sessions
            session_files = glob.glob("data/sessions/*.json")
            stats["sessions_saved"] = str(len(session_files))
            if session_files:
                latest = max(session_files, key=os.path.getmtime)
                import time
                age = time.time() - os.path.getmtime(latest)
                if age < 3600:
                    stats["last_session"] = f"{int(age // 60)}m ago"
                elif age < 86400:
                    stats["last_session"] = f"{int(age // 3600)}h ago"
                else:
                    stats["last_session"] = f"{int(age // 86400)}d ago"
            else:
                stats["last_session"] = "none"

            # Feedback from curated.jsonl
            thumbs_up = thumbs_down = corrections = 0
            curated_path = "data/training/curated.jsonl"
            if os.path.exists(curated_path):
                with open(curated_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            src = entry.get("source", "")
                            if src == "thumbs_up":
                                thumbs_up += 1
                            elif src == "thumbs_down":
                                thumbs_down += 1
                            elif src == "corrected":
                                corrections += 1
                        except Exception:
                            pass
            stats["thumbs_up"] = str(thumbs_up)
            stats["thumbs_down"] = str(thumbs_down)
            stats["corrections"] = str(corrections)
            stats["sft_examples"] = str(thumbs_up + corrections)
            stats["dpo_pairs"] = str(min(thumbs_up, thumbs_down))

            # Last export
            export_files = sorted(
                glob.glob("data/training/*.jsonl") + glob.glob("data/training/*.json"),
                key=os.path.getmtime, reverse=True
            )
            export_files = [f for f in export_files if "curated" not in f]
            if export_files:
                import time as _time
                age = _time.time() - os.path.getmtime(export_files[0])
                stats["last_export"] = f"{int(age // 3600)}h ago" if age > 3600 else f"{int(age // 60)}m ago"
            else:
                stats["last_export"] = "none"

            # Last SFT export content
            last_sft_content = ""
            export_jsonls = sorted(glob.glob("data/training/*.jsonl"), key=os.path.getmtime, reverse=True)
            export_jsonls = [f for f in export_jsonls if "curated" not in os.path.basename(f)]
            if export_jsonls:
                try:
                    with open(export_jsonls[0], "r", encoding="utf-8") as f:
                        lines = []
                        for _ in range(50):
                            line = f.readline()
                            if not line:
                                break
                            lines.append(line)
                        last_sft_content = "".join(lines)
                except Exception:
                    pass
            stats["last_sft_content"] = last_sft_content

            # Eval score
            if os.path.exists("data/eval_last.json"):
                with open("data/eval_last.json", "r", encoding="utf-8") as f:
                    eval_data = json.load(f)
                score = eval_data.get("score", 0.0)
                stats["eval_score"] = f"{score:.1%}"
                stats["eval_dataset"] = eval_data.get("dataset", "—")
                ts = eval_data.get("timestamp", "")
                stats["eval_date"] = ts[:10] if ts else "—"
            else:
                stats["eval_score"] = "no data"
                stats["eval_dataset"] = "—"
                stats["eval_date"] = "—"

        except Exception as e:
            stats["traces_total"] = f"error: {e}"

        self.stats_ready.emit(stats)


class LossChartWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loss-chart-widget")
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            #loss-chart-widget {
                background-color: #0D0D1B;
                border: 1px solid #1F1F3D;
                border-radius: 4px;
            }
        """)
        self._loss_history = []

    def set_loss_history(self, history: list[float]):
        self._loss_history = list(history)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        margin_left = 45
        margin_right = 15
        margin_top = 15
        margin_bottom = 25
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        # Draw background
        painter.setBrush(QBrush(QColor("#0D0D1B")))
        painter.setPen(QPen(QColor("#1F1F3D"), 1))
        painter.drawRoundedRect(0, 0, w, h, 4.0, 4.0)
        
        if plot_w <= 0 or plot_h <= 0:
            return
            
        if not self._loss_history:
            # Draw placeholder text
            painter.setFont(QFont("JetBrains Mono", 9))
            painter.setPen(QPen(QColor("#505068")))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Waiting for training loss...")
            return

        # Scale data
        min_y = min(self._loss_history)
        max_y = max(self._loss_history)
        
        if max_y > min_y:
            y_bottom = max(0.0, min_y - 0.1 * (max_y - min_y))
            y_top = max_y + 0.1 * (max_y - min_y)
        else:
            y_bottom = max(0.0, min_y - 0.5)
            y_top = min_y + 0.5
            
        # Draw horizontal grid lines
        grid_pen = QPen(QColor("#1F1F3D"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        
        font = QFont("JetBrains Mono", 8)
        painter.setFont(font)
        
        levels = [y_bottom, (y_bottom + y_top) / 2.0, y_top]
        for val in levels:
            pct = (val - y_bottom) / (y_top - y_bottom) if y_top != y_bottom else 0.5
            gy = margin_top + (1.0 - pct) * plot_h
            painter.drawLine(margin_left, int(gy), margin_left + plot_w, int(gy))
            
            # Label
            painter.setPen(QPen(QColor("#70708F")))
            painter.drawText(5, int(gy) - 7, margin_left - 10, 15, 
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                             f"{val:.2f}")
            painter.setPen(grid_pen)

        # Compute point coordinates
        points = []
        n_points = len(self._loss_history)
        for idx, val in enumerate(self._loss_history):
            x = margin_left + (idx / (n_points - 1) * plot_w) if n_points > 1 else margin_left + 0.5 * plot_w
            pct = (val - y_bottom) / (y_top - y_bottom) if y_top != y_bottom else 0.5
            y = margin_top + (1.0 - pct) * plot_h
            points.append((x, y))
            
        # Draw path
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        
        if len(points) > 1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i+1]
                dx = (x2 - x1) / 3.0
                path.cubicTo(x1 + dx, y1, x2 - dx, y2, x2, y2)
        else:
            path.lineTo(points[0][0] + 5, points[0][1])

        # Draw filled gradient under curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1][0], margin_top + plot_h)
        fill_path.lineTo(points[0][0], margin_top + plot_h)
        fill_path.closeSubpath()
        
        grad = QLinearGradient(0, margin_top, 0, margin_top + plot_h)
        grad.setColorAt(0.0, QColor(0, 194, 255, 60))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(fill_path, QBrush(grad))

        # Draw the curve line
        curve_pen = QPen(QColor("#00C2FF"), 2)
        painter.setPen(curve_pen)
        painter.drawPath(path)
        
        # Highlight last point
        last_x, last_y = points[-1]
        painter.setBrush(QBrush(QColor("#2DD4A0")))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        painter.drawEllipse(int(last_x) - 4, int(last_y) - 4, 8, 8)
        
        # Draw telemetry details inside chart area
        painter.setPen(QPen(QColor("#2DD4A0")))
        painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        curr_loss = self._loss_history[-1]
        painter.drawText(margin_left + 10, margin_top + 15, f"LOSS: {curr_loss:.4f}")
        
        # Draw count of steps
        painter.setPen(QPen(QColor("#70708F")))
        painter.setFont(QFont("JetBrains Mono", 7.5))
        painter.drawText(margin_left + 10, margin_top + 30, f"Steps: {n_points}")


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
        tabs.addTab(self._build_flywheel_tab(), "Flywheel")
        tabs.addTab(self._build_dataset_tab(), "Dataset")
        tabs.addTab(self._build_export_tab(), "Export")
        tabs.addTab(self._build_train_tab(), "Train")
        tabs.addTab(self._build_auto_train_tab(), "Auto-Train")
        tabs.addTab(self._build_mini_gpt_tab(), "Mini-GPT Sandbox")
        tabs.currentChanged.connect(self._on_tab_changed)
        self._tabs = tabs
        root.addWidget(tabs, 1)

        self._refresh()

    # ── flywheel tab ─────────────────────────────────────────────────────────

    def _build_flywheel_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
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
        self._flywheel_refresh_btn.clicked.connect(self._load_flywheel_stats)
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
        # We insert the buttons above the stretch
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
        return w

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

    def _on_tab_changed(self, idx: int):
        if idx == 0:  # Flywheel tab
            self._load_flywheel_stats()

    def _load_flywheel_stats(self):
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
        self._load_flywheel_stats()

    def _flywheel_export_dpo(self):
        self._export("dpo")
        self._load_flywheel_stats()

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

        return w

    # ── train tab ─────────────────────────────────────────────────────────────

    def _build_train_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
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

    def _build_auto_train_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Left Column: Configuration
        left_col = GlowPanel(self.state)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_layout.addWidget(_section("FLYWHEEL AUTO-TRAIN CONFIG"))

        # Form layout-like structure
        left_layout.addWidget(QLabel("Target Behavior / Topic:"))
        self._auto_topic_input = QLineEdit()
        self._auto_topic_input.setPlaceholderText("e.g., modular arithmetic, binary search")
        self._auto_topic_input.setToolTip("Enter the specific capability you want Karl to learn")
        left_layout.addWidget(self._auto_topic_input)

        left_layout.addWidget(QLabel("Adapter Save Name:"))
        self._auto_adapter_input = QLineEdit()
        self._auto_adapter_input.setPlaceholderText("e.g., math_specialist")
        self._auto_adapter_input.setToolTip("Save folder name under data/adapters/")
        left_layout.addWidget(self._auto_adapter_input)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)

        # Generate Count
        self._auto_count_spin = QSpinBox()
        self._auto_count_spin.setRange(2, 200)
        self._auto_count_spin.setValue(15)
        self._auto_count_spin.setToolTip("Number of training problems to generate and verify")
        grid.addWidget(QLabel("Examples Count:"), 0, 0)
        grid.addWidget(self._auto_count_spin, 0, 1)

        # Epochs
        self._auto_epochs_spin = QSpinBox()
        self._auto_epochs_spin.setRange(1, 20)
        self._auto_epochs_spin.setValue(3)
        grid.addWidget(QLabel("Epochs:"), 0, 2)
        grid.addWidget(self._auto_epochs_spin, 0, 3)

        # Rank
        self._auto_rank_spin = QSpinBox()
        self._auto_rank_spin.setRange(1, 256)
        self._auto_rank_spin.setValue(16)
        grid.addWidget(QLabel("Rank:"), 1, 0)
        grid.addWidget(self._auto_rank_spin, 1, 1)

        # Alpha
        self._auto_alpha_spin = QSpinBox()
        self._auto_alpha_spin.setRange(1, 512)
        self._auto_alpha_spin.setValue(32)
        grid.addWidget(QLabel("Alpha:"), 1, 2)
        grid.addWidget(self._auto_alpha_spin, 1, 3)

        # LR
        self._auto_lr_spin = QDoubleSpinBox()
        self._auto_lr_spin.setDecimals(6)
        self._auto_lr_spin.setRange(1e-6, 1e-2)
        self._auto_lr_spin.setSingleStep(1e-5)
        self._auto_lr_spin.setValue(2e-4)
        grid.addWidget(QLabel("Learning Rate:"), 2, 0)
        grid.addWidget(self._auto_lr_spin, 2, 1)

        # QLoRA Checkbox
        self._auto_qlora_check = QCheckBox("4-bit QLoRA")
        self._auto_qlora_check.setChecked(True)
        grid.addWidget(self._auto_qlora_check, 2, 2, 1, 2)

        left_layout.addLayout(grid)
        left_layout.addWidget(_hline())

        # Auto Train Button
        self._auto_train_btn = QPushButton("▶ start auto-training flywheel")
        self._auto_train_btn.setObjectName("btn-primary")
        self._auto_train_btn.setFixedHeight(36)
        self._auto_train_btn.clicked.connect(self._begin_auto_training)
        left_layout.addWidget(self._auto_train_btn)

        # Progress bar
        self._auto_progress = QProgressBar()
        self._auto_progress.setVisible(False)
        left_layout.addWidget(self._auto_progress)

        left_layout.addStretch()
        layout.addWidget(left_col, 1)

        # Right Column: Guide & Output Logs
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Guide panel explaining the flywheel
        guide_box = GlowPanel(self.state)
        gl = QVBoxLayout(guide_box)
        gl.setContentsMargins(12, 10, 12, 10)
        
        guide_text = (
            "🚀 <b>One-Click Auto-Train Flywheel:</b><br>"
            "This tab runs Karl's self-improvement flywheel completely autonomously:<br>"
            "1. <b>Synthesizer:</b> Generates synthetic problems for your custom behavior.<br>"
            "2. <b>Solver:</b> Attempts to solve the generated problems.<br>"
            "3. <b>Curator & Sandbox:</b> Verifies solutions in a secure execution sandbox.<br>"
            "4. <b>Self-Reflection:</b> Mistakes trigger an LLM-based debugging correction loop.<br>"
            "5. <b>Training:</b> Custom datasets are created, and SFT LoRA training begins."
        )
        guide_lbl = QLabel(guide_text)
        guide_lbl.setWordWrap(True)
        guide_lbl.setStyleSheet("font-size: 8.5pt; color: #00C2FF; line-height: 1.4;")
        gl.addWidget(guide_lbl)
        right_layout.addWidget(guide_box)

        # Output Logs
        log_box = QWidget()
        log_lay = QVBoxLayout(log_box)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.setSpacing(4)
        log_lay.addWidget(_section("FLYWHEEL AUTO-TRAIN LOGS"))
        self._auto_log = QTextBrowser()
        self._auto_log.setObjectName("reasoning-view")
        self._auto_log.setPlaceholderText("Logs will stream here when auto-training begins...")
        self._auto_log.setStyleSheet("font-family: monospace; font-size: 9pt;")
        log_lay.addWidget(self._auto_log)
        right_layout.addWidget(log_box, 1)

        layout.addWidget(right_col, 1)
        return w

    def _begin_auto_training(self):
        topic = self._auto_topic_input.text().strip()
        adapter_name = self._auto_adapter_input.text().strip()
        if not topic:
            self._auto_log.append("Please specify a target behavior/topic.")
            return
        if not adapter_name:
            self._auto_log.append("Please specify an adapter save name.")
            return

        # Sanitize adapter name for file path
        adapter_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', adapter_name)
        self._auto_adapter_input.setText(adapter_name)

        # Release VRAM first
        from app.engine.model_loader import ModelLoader
        ModelLoader.reset_instance()

        self._auto_train_btn.setEnabled(False)
        self._auto_progress.setVisible(True)
        self._auto_progress.setRange(0, 0)  # Indeterminate progress bar
        self._auto_log.clear()
        self._auto_log.append("Starting automated flywheel training pipeline...")

        config = {
            "count": self._auto_count_spin.value(),
            "epochs": self._auto_epochs_spin.value(),
            "rank": self._auto_rank_spin.value(),
            "alpha": self._auto_alpha_spin.value(),
            "lr": self._auto_lr_spin.value(),
            "use_qlora": self._auto_qlora_check.isChecked()
        }

        self._auto_thread = AutoTrainThread(topic, adapter_name, config)
        self._active_threads.add(self._auto_thread)
        self._auto_thread.finished.connect(
            lambda t=self._auto_thread: self._active_threads.discard(t)
        )
        self._auto_thread.finished.connect(self._auto_thread.deleteLater)
        self._auto_thread.log.connect(self._on_auto_log)
        self._auto_thread.done.connect(self._on_auto_done)
        self._auto_thread.error.connect(self._on_auto_error)
        self._auto_thread.start()

    def _on_auto_log(self, text: str):
        self._auto_log.append(text)

    def _on_auto_done(self, adapter_name: str):
        self._auto_train_btn.setEnabled(True)
        self._auto_progress.setVisible(False)
        QMessageBox.information(
            self, "Auto-Training Complete",
            f"Auto-training completed successfully!\nAdapter GGUF ready: data/adapters/{adapter_name}/{adapter_name}.gguf"
        )
        self._auto_topic_input.clear()
        self._auto_adapter_input.clear()

    def _on_auto_error(self, msg: str):
        self._auto_train_btn.setEnabled(True)
        self._auto_progress.setVisible(False)
        self._auto_log.append(f"\n[ERROR] Auto-training failed: {msg}")
        QMessageBox.critical(self, "Auto-Training Error", f"Auto-training failed:\n{msg}")

    # ── Mini-GPT Sandbox Implementation ─────────────────────────────────────────

    def _build_mini_gpt_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Left Column: Configuration Drawer
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        
        ll.addWidget(_section("MINI-GPT ARCHITECTURE"))
        
        # Dataset Selection
        ll.addWidget(QLabel("Training Dataset:"))
        self._mini_dataset_combo = QComboBox()
        self._mini_dataset_combo.addItems(["Tiny Shakespeare", "Karl's Trace Logs", "Custom Text File..."])
        self._mini_dataset_combo.currentTextChanged.connect(self._on_mini_dataset_changed)
        ll.addWidget(self._mini_dataset_combo)

        # Custom File Row (Initially Hidden)
        self._mini_custom_row = QWidget()
        cr_layout = QHBoxLayout(self._mini_custom_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(8)
        self._mini_file_label = QLabel("No file selected")
        self._mini_file_label.setObjectName("lbl-muted")
        self._mini_file_label.setWordWrap(True)
        cr_layout.addWidget(self._mini_file_label, 1)
        self._mini_browse_btn = QPushButton("Browse")
        self._mini_browse_btn.setObjectName("btn-ghost")
        self._mini_browse_btn.clicked.connect(self._on_mini_browse_file)
        cr_layout.addWidget(self._mini_browse_btn)
        self._mini_custom_row.setVisible(False)
        ll.addWidget(self._mini_custom_row)

        # Grid of architectural hyperparameters
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Block Size (Context):"), 0, 0)
        self._mini_block_size = QSpinBox()
        self._mini_block_size.setRange(16, 256)
        self._mini_block_size.setSingleStep(16)
        self._mini_block_size.setValue(64)
        grid.addWidget(self._mini_block_size, 0, 1)

        grid.addWidget(QLabel("Embedding Dimension:"), 1, 0)
        self._mini_n_embd = QSpinBox()
        self._mini_n_embd.setRange(32, 512)
        self._mini_n_embd.setSingleStep(32)
        self._mini_n_embd.setValue(128)
        grid.addWidget(self._mini_n_embd, 1, 1)

        grid.addWidget(QLabel("Attention Heads:"), 2, 0)
        self._mini_n_heads = QSpinBox()
        self._mini_n_heads.setRange(1, 16)
        self._mini_n_heads.setValue(4)
        grid.addWidget(self._mini_n_heads, 2, 1)

        grid.addWidget(QLabel("Transformer Layers:"), 3, 0)
        self._mini_n_layers = QSpinBox()
        self._mini_n_layers.setRange(1, 12)
        self._mini_n_layers.setValue(4)
        grid.addWidget(self._mini_n_layers, 3, 1)

        grid.addWidget(QLabel("Learning Rate:"), 4, 0)
        self._mini_lr = QDoubleSpinBox()
        self._mini_lr.setRange(1e-5, 1e-1)
        self._mini_lr.setSingleStep(1e-4)
        self._mini_lr.setValue(1e-3)
        self._mini_lr.setDecimals(5)
        grid.addWidget(self._mini_lr, 4, 1)

        grid.addWidget(QLabel("Max Iterations:"), 5, 0)
        self._mini_max_iters = QSpinBox()
        self._mini_max_iters.setRange(50, 5000)
        self._mini_max_iters.setSingleStep(50)
        self._mini_max_iters.setValue(500)
        grid.addWidget(self._mini_max_iters, 5, 1)

        ll.addWidget(grid_widget)
        ll.addWidget(_hline())

        # Buttons
        self._mini_train_btn = QPushButton("Start Sandbox Training")
        self._mini_train_btn.setObjectName("btn-primary")
        self._mini_train_btn.clicked.connect(self._start_mini_training)
        ll.addWidget(self._mini_train_btn)

        self._mini_stop_btn = QPushButton("Stop Training")
        self._mini_stop_btn.setObjectName("btn-danger")
        self._mini_stop_btn.setEnabled(False)
        self._mini_stop_btn.clicked.connect(self._stop_mini_training)
        ll.addWidget(self._mini_stop_btn)

        self._mini_progress_bar = QProgressBar()
        self._mini_progress_bar.setVisible(False)
        ll.addWidget(self._mini_progress_bar)

        ll.addStretch()
        splitter.addWidget(left)

        # Right Column: Visual Monitor and Output Viewers
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(1)

        # Upper: Training Log view
        log_panel = QWidget()
        lpl = QVBoxLayout(log_panel)
        lpl.setContentsMargins(0, 0, 0, 0)
        lpl.setSpacing(6)
        lpl.addWidget(_section("TRAINING TELEMETRY & LOSS"))
        
        telemetry_row = QWidget()
        trl_layout = QHBoxLayout(telemetry_row)
        trl_layout.setContentsMargins(0, 0, 0, 0)
        trl_layout.setSpacing(10)
        
        self._mini_log_view = QTextBrowser()
        self._mini_log_view.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #1F1F3D; border-radius: 4px; "
            "color: #2DD4A0; font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; padding: 6px;"
        )
        trl_layout.addWidget(self._mini_log_view, 1)
        
        self._mini_loss_chart = LossChartWidget()
        trl_layout.addWidget(self._mini_loss_chart, 1)
        
        lpl.addWidget(telemetry_row)
        right_splitter.addWidget(log_panel)

        # Lower: Live text generation stream
        gen_panel = QWidget()
        gpl = QVBoxLayout(gen_panel)
        gpl.setContentsMargins(0, 0, 0, 0)
        gpl.addWidget(_section("LIVE GENERATION MONITOR"))
        self._mini_sample_view = QTextBrowser()
        self._mini_sample_view.setStyleSheet(
            "background-color: #0D0D1B; border: 1px solid #1F1F3D; border-radius: 4px; "
            "color: #ECECF5; font-family: 'JetBrains Mono', monospace; font-size: 9pt; padding: 6px;"
        )
        self._mini_sample_view.setPlaceholderText("The model will stream sample generations here every 100 steps to show its learning progression...")
        gpl.addWidget(self._mini_sample_view)
        right_splitter.addWidget(gen_panel)

        rl.addWidget(right_splitter, 1)

        # Bottom: Inference Sandbox Groupbox
        self._mini_inference_group = QWidget()
        self._mini_inference_group.setObjectName("panel")
        self._mini_inference_group.setEnabled(False)
        ig_layout = QVBoxLayout(self._mini_inference_group)
        ig_layout.setContentsMargins(12, 12, 12, 12)
        ig_layout.setSpacing(8)
        
        ig_layout.addWidget(_section("TINY-GPT INFERENCE SANDBOX"))

        input_row = QHBoxLayout()
        self._mini_prompt_input = QLineEdit()
        self._mini_prompt_input.setPlaceholderText("Enter a starting prompt (e.g. 'To be or not to be') or leave empty...")
        self._mini_prompt_input.returnPressed.connect(self._run_mini_inference)
        input_row.addWidget(self._mini_prompt_input, 1)

        input_row.addWidget(QLabel("Temp:"))
        self._mini_temp_spin = QDoubleSpinBox()
        self._mini_temp_spin.setRange(0.1, 2.0)
        self._mini_temp_spin.setSingleStep(0.1)
        self._mini_temp_spin.setValue(0.8)
        self._mini_temp_spin.setFixedWidth(60)
        input_row.addWidget(self._mini_temp_spin)

        input_row.addWidget(QLabel("Tokens:"))
        self._mini_gen_tokens = QSpinBox()
        self._mini_gen_tokens.setRange(10, 500)
        self._mini_gen_tokens.setSingleStep(25)
        self._mini_gen_tokens.setValue(150)
        self._mini_gen_tokens.setFixedWidth(70)
        input_row.addWidget(self._mini_gen_tokens)

        self._mini_generate_btn = QPushButton("Generate Text")
        self._mini_generate_btn.setObjectName("btn-primary")
        self._mini_generate_btn.clicked.connect(self._run_mini_inference)
        input_row.addWidget(self._mini_generate_btn)
        ig_layout.addLayout(input_row)

        self._mini_generate_output = QTextBrowser()
        self._mini_generate_output.setStyleSheet(
            "background-color: #0B0B14; border: 1px solid #1F1F35; border-radius: 4px; "
            "color: #00C2FF; font-family: 'JetBrains Mono', monospace; font-size: 9pt; padding: 6px;"
        )
        self._mini_generate_output.setFixedHeight(100)
        ig_layout.addWidget(self._mini_generate_output)

        rl.addWidget(self._mini_inference_group)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Check if pre-existing weights exist to enable inference sandbox
        if os.path.exists("data/mini_gpt/weights.pt") and os.path.exists("data/mini_gpt/tokenizer.json") and os.path.exists("data/mini_gpt/config.json"):
            self._mini_inference_group.setEnabled(True)
            self._mini_generate_output.setHtml("<span style='color:#00C2FF;'>Pre-trained Sandbox weights found. Type a prompt above and generate text!</span>")

        self._mini_train_thread = None
        self._mini_loss_history = []

        return w

    def _on_mini_dataset_changed(self, text: str):
        self._mini_custom_row.setVisible(text == "Custom Text File...")

    def _on_mini_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Text File", "", "Text Files (*.txt *.md *.py *.jsonl);;All Files (*)")
        if path:
            self._mini_custom_file_path = path
            self._mini_file_label.setText(os.path.basename(path))

    def _get_mini_dataset_text(self) -> str:
        dataset_type = self._mini_dataset_combo.currentText()
        if dataset_type == "Tiny Shakespeare":
            path = "data/tiny_shakespeare.txt"
            if not os.path.exists(path):
                os.makedirs("data", exist_ok=True)
                default_shakespeare = (
                    "ROMEO:\n"
                    "But, soft! what light through yonder window breaks?\n"
                    "It is the east, and Juliet is the sun.\n"
                    "Arise, fair sun, and kill the envious moon,\n"
                    "Who is already sick and pale with grief,\n"
                    "That thou her maid art far more fair than she:\n"
                    "Be not her maid, since she is envious;\n"
                    "Her vestal livery is but sick and green\n"
                    "And none but fools do wear it; cast it off.\n"
                    "It is my lady, O, it is my love!\n"
                    "O, that she knew she were!\n"
                    "She speaks yet she says nothing: what of that?\n"
                    "Her eye discourses; I will answer it.\n"
                    "I am too bold, 'tis not to me she speaks:\n"
                    "Two of the fairest stars in all the heaven,\n"
                    "Having some business, do entreat her eyes\n"
                    "To twinkle in their spheres till they return.\n"
                    "What if her eyes were there, they in her head?\n"
                    "The brightness of her cheek would shame those stars,\n"
                    "As daylight doth a lamp; her eyes in heaven\n"
                    "Would through the airy region stream so bright\n"
                    "That birds would sing and think it were not night.\n"
                    "See, how she leans her cheek upon her hand!\n"
                    "O, that I were a glove upon that hand,\n"
                    "That I might touch that cheek!\n\n"
                    "JULIET:\n"
                    "Ay me!\n\n"
                    "ROMEO:\n"
                    "She speaks:\n"
                    "O, speak again, bright angel! for thou art\n"
                    "As glorious to this night, being o'er my head\n"
                    "As is a winged messenger of heaven\n"
                    "Unto the white-upturned wondering eyes\n"
                    "Of mortals that fall back to gaze on him\n"
                    "When he bestrides the lazy-pacing clouds\n"
                    "And sails upon the bosom of the air.\n"
                ) * 20  # Repeat to make it long enough for training
                with open(path, "w", encoding="utf-8") as f:
                    f.write(default_shakespeare)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        elif dataset_type == "Karl's Trace Logs":
            log_dir = "data/logs/traces"
            text_parts = []
            if os.path.exists(log_dir):
                for fname in sorted(os.listdir(log_dir)):
                    if fname.endswith(".jsonl"):
                        try:
                            with open(os.path.join(log_dir, fname), "r", encoding="utf-8") as f:
                                for line in f:
                                    if not line.strip():
                                        continue
                                    obj = json.loads(line)
                                    if "thinking" in obj and obj["thinking"]:
                                        text_parts.append(f"<think>\n{obj['thinking']}\n</think>\n")
                                    if "response" in obj and obj["response"]:
                                        text_parts.append(f"{obj['response']}\n")
                        except Exception:
                            pass
            text = "".join(text_parts)
            if not text:
                text = "SYSTEM: You are Karl. I am an AI assistant.\n" * 100
            return text

        elif dataset_type == "Custom Text File...":
            path = getattr(self, "_mini_custom_file_path", "")
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            else:
                raise ValueError("No custom text file selected. Please select a text file first.")
        
        return ""

    def _start_mini_training(self):
        try:
            text = self._get_mini_dataset_text()
            if len(text) < 500:
                QMessageBox.warning(self, "Dataset Too Small", "Training dataset must be at least 500 characters long.")
                return
            
            # Disable configuration panel
            self._mini_dataset_combo.setEnabled(False)
            self._mini_browse_btn.setEnabled(False)
            self._mini_block_size.setEnabled(False)
            self._mini_n_embd.setEnabled(False)
            self._mini_n_heads.setEnabled(False)
            self._mini_n_layers.setEnabled(False)
            self._mini_lr.setEnabled(False)
            self._mini_max_iters.setEnabled(False)
            
            # Toggle buttons
            self._mini_train_btn.setEnabled(False)
            self._mini_stop_btn.setEnabled(True)
            
            # Setup progress bar
            self._mini_progress_bar.setVisible(True)
            self._mini_progress_bar.setValue(0)
            self._mini_progress_bar.setMaximum(self._mini_max_iters.value())

            self._mini_log_view.clear()
            self._mini_sample_view.clear()
            self._mini_loss_history.clear()
            self._mini_loss_chart.set_loss_history([])

            config = {
                "batch_size": 32,
                "block_size": self._mini_block_size.value(),
                "n_embd": self._mini_n_embd.value(),
                "n_heads": self._mini_n_heads.value(),
                "n_layers": self._mini_n_layers.value(),
                "lr": self._mini_lr.value(),
                "max_iters": self._mini_max_iters.value(),
                "eval_interval": 50,
                "sample_interval": 100
            }

            self._mini_train_thread = MiniTrainThread(
                dataset_text=text,
                config=config
            )
            self._mini_train_thread.log.connect(self._on_mini_log)
            self._mini_train_thread.loss.connect(self._on_mini_loss)
            self._mini_train_thread.progress.connect(self._on_mini_progress)
            self._mini_train_thread.done.connect(self._on_mini_done)
            self._mini_train_thread.error.connect(self._on_mini_error)
            
            self._active_threads.add(self._mini_train_thread)
            self._mini_train_thread.finished.connect(lambda: self._active_threads.discard(self._mini_train_thread))
            self._mini_train_thread.finished.connect(self._mini_train_thread.deleteLater)
            
            self._mini_train_thread.start()

        except Exception as e:
            QMessageBox.critical(self, "Training Initialization Error", f"Could not launch training:\n{e}")

    def _stop_mini_training(self):
        if self._mini_train_thread and self._mini_train_thread.isRunning():
            self._mini_train_thread.stop()
            self._mini_stop_btn.setEnabled(False)

    def _on_mini_log(self, text: str):
        self._mini_log_view.append(text)

    def _on_mini_loss(self, step: int, val_loss: float):
        self._mini_loss_history.append(val_loss)
        self._mini_loss_chart.set_loss_history(self._mini_loss_history)
        
        # ASCII loss bar
        bar_len = int(min(20, max(1, val_loss * 4.0)))
        bar = "█" * (21 - bar_len) + "░" * bar_len
        self._mini_log_view.append(f"<b>[Telemetry] Step {step} | Val Loss: {val_loss:.4f} [{bar}]</b>")

    def _on_mini_progress(self, step: int, max_steps: int, sample_text: str):
        self._mini_progress_bar.setValue(step)
        html_sample = (
            f"<div style='color:#9090A8; font-size:8.2pt; border-bottom:1px solid #1F1F35; padding-bottom:3px; margin-bottom:5px;'>"
            f"  --- Generation Output (Step {step} / {max_steps}) ---"
            f"</div>"
            f"<div style='color:#ECECF5; font-size:9pt; white-space:pre-wrap; line-height:1.4;'>{html.escape(sample_text)}</div>"
        )
        self._mini_sample_view.setHtml(html_sample)

    def _on_mini_done(self, save_dir: str):
        self._mini_progress_bar.setValue(self._mini_max_iters.value())
        self._mini_progress_bar.setVisible(False)
        self._mini_train_btn.setEnabled(True)
        self._mini_stop_btn.setEnabled(False)
        
        # Restore configuration inputs
        self._mini_dataset_combo.setEnabled(True)
        self._mini_browse_btn.setEnabled(True)
        self._mini_block_size.setEnabled(True)
        self._mini_n_embd.setEnabled(True)
        self._mini_n_heads.setEnabled(True)
        self._mini_n_layers.setEnabled(True)
        self._mini_lr.setEnabled(True)
        self._mini_max_iters.setEnabled(True)

        self._mini_inference_group.setEnabled(True)
        QMessageBox.information(self, "Mini-GPT Training Complete", f"Educational Mini-GPT trained successfully!\nWeights saved to: {save_dir}/weights.pt")

    def _on_mini_error(self, msg: str):
        self._mini_progress_bar.setVisible(False)
        self._mini_train_btn.setEnabled(True)
        self._mini_stop_btn.setEnabled(False)
        
        # Restore inputs
        self._mini_dataset_combo.setEnabled(True)
        self._mini_browse_btn.setEnabled(True)
        self._mini_block_size.setEnabled(True)
        self._mini_n_embd.setEnabled(True)
        self._mini_n_heads.setEnabled(True)
        self._mini_n_layers.setEnabled(True)
        self._mini_lr.setEnabled(True)
        self._mini_max_iters.setEnabled(True)

        self._mini_log_view.append(f"\n[CRITICAL ERROR] Training failed:\n{msg}")
        QMessageBox.critical(self, "Mini-GPT Training Error", f"Training execution failed:\n{msg}")

    def _run_mini_inference(self):
        prompt = self._mini_prompt_input.text()
        self._mini_generate_btn.setEnabled(False)
        self._mini_generate_output.clear()
        
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            save_dir = "data/mini_gpt"
            
            config_path = os.path.join(save_dir, "config.json")
            weights_path = os.path.join(save_dir, "weights.pt")
            vocab_path = os.path.join(save_dir, "tokenizer.json")
            
            if not (os.path.exists(config_path) and os.path.exists(weights_path) and os.path.exists(vocab_path)):
                raise FileNotFoundError("Mini-GPT weights or config file not found. Please run training first.")
                
            # Load tokenizer
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_meta = json.load(f)
            tokenizer = CharTokenizer()
            tokenizer.chars = vocab_meta["chars"]
            tokenizer.stoi = vocab_meta["stoi"]
            tokenizer.itos = vocab_meta["itos"]
            tokenizer.vocab_size = len(tokenizer.chars)
            
            # Load config
            with open(config_path, "r", encoding="utf-8") as f:
                arch = json.load(f)
            
            # Recreate model
            model = MiniGPT(
                vocab_size=arch["vocab_size"],
                n_embd=arch["n_embd"],
                n_heads=arch["n_heads"],
                n_layers=arch["n_layers"],
                block_size=arch["block_size"],
                dropout=0.0
            )
            
            # Load weights
            state_dict = torch.load(weights_path, map_location=device)
            model.load_state_dict(state_dict)
            model = model.to(device)
            model.eval()
            
            # Encode prompt
            prompt_encoded = tokenizer.encode(prompt)
            if not prompt_encoded:
                prompt_encoded = [0]
            
            context_tensor = torch.tensor([prompt_encoded], dtype=torch.long, device=device)
            
            # Generate
            max_new = self._mini_gen_tokens.value()
            temp = self._mini_temp_spin.value()
            
            # Generate tokens
            gen_ids = model.generate(context_tensor, max_new_tokens=max_new, temperature=temp, top_k=20)[0].tolist()
            output_text = tokenizer.decode(gen_ids)
            
            self._mini_generate_output.setText(output_text)
            
        except Exception as e:
            traceback.print_exc()
            self._mini_generate_output.setHtml(f"<span style='color:#FF3B30;'>Inference error: {html.escape(str(e))}</span>")
        finally:
            self._mini_generate_btn.setEnabled(True)

