import os
import json
import sys
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

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

    def request_stop(self):
        self.requestInterruption()

    def run(self):
        from app.engine.task_supervisor import TaskSupervisor
        task_id = TaskSupervisor.instance().register(
            name=f"LoRA Training: {self.adapter_name}",
            cancellable=self,
        )
        self.task_id = task_id
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
                    if state.max_steps > 0:
                        from app.engine.task_supervisor import TaskSupervisor
                        TaskSupervisor.instance().update_progress(task_id, state.global_step / state.max_steps)

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
            TaskSupervisor.instance().finish(task_id)

        except Exception as e:
            TaskSupervisor.instance().fail(task_id, str(e))
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

    def request_stop(self):
        self.requestInterruption()
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def run(self):
        from app.engine.task_supervisor import TaskSupervisor
        task_id = TaskSupervisor.instance().register(
            name=f"Auto-Train Swarm: {self.adapter_name}",
            cancellable=self,
        )
        self.task_id = task_id
        
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
                TaskSupervisor.instance().finish(task_id)
            else:
                self.error.emit(f"Auto-train process exited with code {rc}")
                TaskSupervisor.instance().fail(task_id, f"Auto-train process exited with code {rc}")
        except Exception as e:
            TaskSupervisor.instance().fail(task_id, str(e))
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


class MiniTrainThread(QThread):
    # Signals for communicating with UI
    loss = pyqtSignal(int, float)            # step, loss_val
    progress = pyqtSignal(int, int, str)     # step, total_steps, text_sample
    done = pyqtSignal(str)                   # adapter/model folder path
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(
        self,
        dataset_text: str,
        config: dict,
        save_dir: str = "data/mini_gpt"
    ):
        super().__init__()
        self.dataset_text = dataset_text
        self.config = config
        self.save_dir = save_dir
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def request_stop(self):
        self.stop()

    def run(self):
        from app.engine.task_supervisor import TaskSupervisor
        task_id = TaskSupervisor.instance().register(
            name="MiniGPT Training",
            cancellable=self,
        )
        self.task_id = task_id
        try:
            self.log.emit("Initializing MiniGPT Trainer...")
            
            # Lazy imports
            import torch
            from app.engine.mini_transformer import MiniGPT, CharTokenizer

            # 1. Hyperparameters
            batch_size = self.config.get("batch_size", 32)
            block_size = self.config.get("block_size", 64)
            n_embd = self.config.get("n_embd", 128)
            n_heads = self.config.get("n_heads", 4)
            n_layers = self.config.get("n_layers", 4)
            dropout = self.config.get("dropout", 0.1)
            learning_rate = self.config.get("lr", 1e-3)
            max_iters = self.config.get("max_iters", 500)
            eval_interval = self.config.get("eval_interval", 50)
            sample_interval = self.config.get("sample_interval", 100)

            # Device configuration
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.log.emit(f"Using device: {device.upper()}")

            # 2. Tokenizer
            self.log.emit("Fitting tokenizer...")
            tokenizer = CharTokenizer()
            tokenizer.fit(self.dataset_text)
            vocab_size = tokenizer.vocab_size
            self.log.emit(f"Dataset Vocabulary Size: {vocab_size} characters")

            # Encode data
            data = torch.tensor(tokenizer.encode(self.dataset_text), dtype=torch.long)
            
            # Split train / val
            n = int(0.9 * len(data))
            train_data = data[:n]
            val_data = data[n:]
            
            if len(train_data) <= block_size:
                raise ValueError(f"Dataset is too short! Must be longer than block size ({block_size}).")

            # 3. Model setup
            self.log.emit("Instantiating MiniGPT Model...")
            model = MiniGPT(
                vocab_size=vocab_size,
                n_embd=n_embd,
                n_heads=n_heads,
                n_layers=n_layers,
                block_size=block_size,
                dropout=dropout
            )
            model = model.to(device)

            # Print param count
            param_count = sum(p.numel() for p in model.parameters())
            self.log.emit(f"Model Parameters: {param_count:,}")

            # Optimizer
            optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

            # Batch helper
            def get_batch(split):
                split_data = train_data if split == 'train' else val_data
                ix = torch.randint(len(split_data) - block_size, (batch_size,))
                x = torch.stack([split_data[i:i+block_size] for i in ix])
                y = torch.stack([split_data[i+1:i+block_size+1] for i in ix])
                x, y = x.to(device), y.to(device)
                return x, y

            # Validation loss helper
            @torch.no_grad()
            def estimate_loss():
                out = {}
                model.eval()
                for split in ['train', 'val']:
                    losses = torch.zeros(10)
                    for k in range(10):
                        X, Y = get_batch(split)
                        _, loss = model(X, Y)
                        losses[k] = loss.item()
                    out[split] = losses.mean().item()
                model.train()
                return out

            self.log.emit("Starting training loop...")
            
            for step in range(max_iters + 1):
                if self._stop_requested:
                    self.log.emit("Training interrupted by user.")
                    break

                # Sample batch and calculate loss
                xb, yb = get_batch('train')
                logits, loss = model(xb, yb)
                
                # Backpropagation
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                if max_iters > 0:
                    from app.engine.task_supervisor import TaskSupervisor
                    TaskSupervisor.instance().update_progress(task_id, step / max_iters)

                # Periodic evaluation
                if step % eval_interval == 0:
                    eval_losses = estimate_loss()
                    self.log.emit(f"Step {step}/{max_iters} | Train Loss: {eval_losses['train']:.4f} | Val Loss: {eval_losses['val']:.4f}")
                    self.loss.emit(step, eval_losses['val'])

                # Periodic text sampling
                if step % sample_interval == 0:
                    model.eval()
                    # Feed a newline character as the start context
                    context = torch.zeros((1, 1), dtype=torch.long, device=device)
                    # Generate 150 characters
                    gen_ids = model.generate(context, max_new_tokens=150, temperature=0.8, top_k=20)[0].tolist()
                    sample_text = tokenizer.decode(gen_ids)
                    model.train()

                    self.progress.emit(step, max_iters, sample_text)

            # 4. Save model weights, tokenizer, and config
            os.makedirs(self.save_dir, exist_ok=True)
            
            # Save PyTorch weights
            weights_path = os.path.join(self.save_dir, "weights.pt")
            torch.save(model.state_dict(), weights_path)
            
            # Save architecture config
            config_path = os.path.join(self.save_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "n_embd": n_embd,
                    "n_heads": n_heads,
                    "n_layers": n_layers,
                    "block_size": block_size,
                    "vocab_size": vocab_size
                }, f, indent=2)

            # Save tokenizer metadata
            vocab_path = os.path.join(self.save_dir, "tokenizer.json")
            with open(vocab_path, "w", encoding="utf-8") as f:
                json.dump({
                    "chars": tokenizer.chars,
                    "stoi": tokenizer.stoi,
                    "itos": tokenizer.itos
                }, f, indent=2)

            self.log.emit(f"Model saved successfully to {self.save_dir}")
            self.done.emit(self.save_dir)
            TaskSupervisor.instance().finish(task_id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            TaskSupervisor.instance().fail(task_id, str(e))
            self.error.emit(str(e))
