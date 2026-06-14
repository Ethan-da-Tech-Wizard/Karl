"""
MiniGPT Training Thread — Educational Sandbox
=============================================
This module handles training the MiniGPT model in a background thread,
allowing Karl's UI to remain fully responsive during training.
It emits live loss scores and sample generations at regular intervals.
"""

import os
import json
import torch
import torch.nn as nn
from PyQt6.QtCore import QThread, pyqtSignal
from app.engine.mini_transformer import MiniGPT, CharTokenizer

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

    def run(self):
        try:
            self.log.emit("Initializing MiniGPT Trainer...")
            
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

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
