import logging
import os
import json
import uuid
import gzip
import shutil
import threading
import hashlib
import base64
from datetime import datetime, timezone

logger = logging.getLogger("karl.trace_logger")


_MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file before rotation


class TraceLogger:
    def __init__(self, log_dir: str = "data/logs/traces", archive_dir: str = "data/logs/archive"):
        self.log_dir = log_dir
        self.archive_dir = archive_dir
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        self._session_id = str(uuid.uuid4())
        self._log_file: str | None = None
        self._lock = threading.Lock()
        self._refresh_path()
        self.prune_logs()

    def _get_max_bytes(self) -> int:
        global _MAX_BYTES
        if _MAX_BYTES != 50 * 1024 * 1024:
            return _MAX_BYTES
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            size_mb = config.get("log_rotation_size_mb", 10)
            return size_mb * 1024 * 1024
        except Exception:
            return 10 * 1024 * 1024

    def _get_encryption_key(self) -> bytes:
        """Derives a Fernet-compatible encryption key from bridge token and stable hardware salt."""
        try:
            # 1. Load bridge token
            token = "karl-default-secret"
            token_path = "data/bridge_token.json"
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    token_data = json.load(f)
                    token = token_data.get("token", token)
            
            # 2. Get STABLE hardware salt (using totals, not available/free)
            import psutil
            import platform
            from core.hardware_scout import get_cpu_flags
            
            total_ram = psutil.virtual_memory().total
            total_storage = shutil.disk_usage(os.getcwd()).total
            cpu_flags = "".join(get_cpu_flags())
            os_name = platform.system()
            
            salt_seed = f"{total_ram}-{total_storage}-{cpu_flags}-{os_name}"
            
            # 3. Derive key using PBKDF2
            k = hashlib.pbkdf2_hmac(
                'sha256', 
                token.encode(), 
                salt_seed.encode(), 
                100000
            )
            # Fernet keys must be 32 url-safe base64-encoded bytes
            return base64.urlsafe_b64encode(k)
        except Exception as e:
            logger.error(f"Failed to derive encryption key: {e}")
            return base64.urlsafe_b64encode(b"karl-emergency-fallback-key-32b!")

    def prune_logs(self):
        """Delete trace log files and archives older than log_retention_days."""
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            retention_days = config.get("log_retention_days", 30)
        except Exception:
            retention_days = 30

        if not retention_days or retention_days <= 0:
            return

        now = datetime.now(timezone.utc)
        
        # Prune live traces, compressed archives, and encrypted archives
        for directory in [self.log_dir, self.archive_dir]:
            if not os.path.exists(directory):
                continue
            for f in os.listdir(directory):
                if (f.startswith("trace_") and (f.endswith(".jsonl") or f.endswith(".jsonl.gz") or f.endswith(".jsonl.enc"))):
                    path = os.path.join(directory, f)
                    try:
                        mtime = os.path.getmtime(path)
                        mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        age_days = (now - mtime_dt).days
                        if age_days > retention_days:
                            os.remove(path)
                            logger.info(f"Pruned old log file: {f}")
                    except Exception as e:
                        logger.warning(f"Failed to prune log file {f}: {e}")

    def _archive_log(self, file_path: str):
        """Compresses and ENCRYPTS a rotated log file."""
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return

        try:
            from cryptography.fernet import Fernet
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            filename = os.path.basename(file_path)
            # Use .jsonl.enc for encrypted Gzip payload
            archive_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.jsonl.enc"
            archive_path = os.path.join(self.archive_dir, archive_filename)

            logger.info(f"Encrypting and Archiving log {filename}...")
            
            # 1. Gzip compress in memory
            with open(file_path, 'rb') as f_in:
                gzipped_data = gzip.compress(f_in.read())
            
            # 2. Encrypt
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted_data = f.encrypt(gzipped_data)
            
            # 3. Write encrypted archive
            with open(archive_path, 'wb') as f_out:
                f_out.write(encrypted_data)
            
            # Verify the archive exists and is non-empty before deleting original
            if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
                os.remove(file_path)
                logger.info(f"Successfully encrypted and archived {filename}")
            else:
                logger.error(f"Failed to verify archive {archive_path}. Keeping original.")
        except ImportError:
            logger.error("cryptography module not found. Falling back to plaintext Gzip archival.")
            # Fallback to standard Gzip if cryptography is missing
            self._archive_log_plaintext(file_path)
        except Exception as e:
            logger.error(f"Failed to encrypt archive log file {file_path}: {e}")

    def _archive_log_plaintext(self, file_path: str):
        """Standard Gzip archival fallback."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            filename = os.path.basename(file_path)
            archive_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.jsonl.gz"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            with open(file_path, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            if os.path.exists(archive_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Plaintext fallback archival failed: {e}")

    def _refresh_path(self):
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            base = os.path.join(self.log_dir, f"trace_{date_str}.jsonl")
            max_bytes = self._get_max_bytes()
            
            # Check if base needs archival
            if os.path.exists(base) and os.path.getsize(base) >= max_bytes:
                self._archive_log(base)
            
            if not os.path.exists(base):
                self._log_file = base
                return

            # If base still exists (because size was < max or archive failed), use it
            if os.path.getsize(base) < max_bytes:
                self._log_file = base
                return
            
            # Fallback rotation if archival failed or file is somehow still too large
            i = 1
            while True:
                candidate = os.path.join(self.log_dir, f"trace_{date_str}_{i}.jsonl")
                if os.path.exists(candidate) and os.path.getsize(candidate) >= max_bytes:
                    self._archive_log(candidate)
                    
                if not os.path.exists(candidate) or os.path.getsize(candidate) < max_bytes:
                    self._log_file = candidate
                    return
                i += 1

    def log_generation(
        self,
        compiled_prompt: str,
        hyperparams: dict,
        raw_output: str,
        parsed_thought: str,
        parsed_response: str,
        execution_time: float,
        rag_context: list | None = None,
        workflow: str = "general_chat",
        template: str = "reasoning_minimal",
        feedback: str = "none",
        corrected_response: str | None = None,
        model_name: str | None = None,
        adapter_name: str | None = None,
        diagnostics: dict | None = None,
        gpu_temp_c: float | None = None,
    ) -> str:
        """
        Logs one generation event. Returns the path of the log file written to.

        The JSONL schema is compatible with Unsloth SFT and DPO export.
        """
        self.prune_logs()
        
        # _refresh_path handles locking internally
        self._refresh_path()

        timing = {
            "total_seconds": round(execution_time, 3),
        }
        gen_tps = 0.0
        if diagnostics:
            gen_tps = diagnostics.get("generation_tps", 0.0)
            timing.update({
                "prefill_seconds": round(diagnostics.get("prefill_time", 0), 3),
                "prefill_tps": round(diagnostics.get("prefill_tps", 0), 1),
                "generation_seconds": round(diagnostics.get("generation_time", 0), 3),
                "generation_tps": round(gen_tps, 1),
                "prompt_tokens": diagnostics.get("prompt_tokens", 0),
                "generation_tokens": diagnostics.get("generation_tokens", 0),
                "total_tps": round(diagnostics.get("total_tps", 0), 1),
            })

        # ── Thermal Warning Check ───────────────────────────────────────────
        warning = None
        try:
            from core.hardware_scout import get_hardware_profile
            profile = get_hardware_profile()
            throttled = False
            for gpu in profile.get("gpu_list", []):
                if "Thermal Throttling Active" in gpu.get("alerts", []):
                    throttled = True
                    break
            
            if throttled and gen_tps < 2.0:
                warning = f"Low-Throughput Thermal Throttle Degradation (Speed: {gen_tps:.1f} tok/sec)"
                logger.warning(f"Logging degraded generation: {warning}")
        except Exception as e:
            logger.debug(f"Could not perform thermal warning check: {e}")
        # ────────────────────────────────────────────────────────────────────

        entry = {
            "id": str(uuid.uuid4()),
            "session_id": self._session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timing": timing,
            "gpu_temp_c": gpu_temp_c,
            "model": model_name or "unknown",
            "adapter": adapter_name,
            "workflow": workflow,
            "template": template,
            "hyperparams": hyperparams,
            "system_prompt": "",          # populated by caller if desired
            "compiled_prompt": compiled_prompt,
            "thinking": parsed_thought,
            "response": parsed_response,
            "raw_output": raw_output,
            "rag_chunks": rag_context or [],
            "feedback": feedback,          # none | thumbs_up | thumbs_down | corrected
            "corrected_response": corrected_response,
        }
        if warning:
            entry["warning"] = warning

        with self._lock:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return self._log_file

    @staticmethod
    def decrypt_in_memory(token: str, file_path: str) -> list[dict]:
        """
        Decrypts an archived .enc log file in RAM without writing to disk.
        Returns a list of parsed JSON records.
        """
        try:
            from cryptography.fernet import Fernet
            import hashlib
            import base64
            import psutil
            import platform
            from core.hardware_scout import get_cpu_flags
            
            # 1. Derive key from PROVIDED token and STABLE hardware salt
            total_ram = psutil.virtual_memory().total
            total_storage = shutil.disk_usage(os.getcwd()).total
            cpu_flags = "".join(get_cpu_flags())
            os_name = platform.system()
            salt_seed = f"{total_ram}-{total_storage}-{cpu_flags}-{os_name}"
            
            k = hashlib.pbkdf2_hmac('sha256', token.encode(), salt_seed.encode(), 100000)
            key = base64.urlsafe_b64encode(k)
            
            # 2. Decrypt
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archive not found: {file_path}")
                
            with open(file_path, 'rb') as f_in:
                encrypted_data = f_in.read()
            
            fernet = Fernet(key)
            try:
                gzipped_data = fernet.decrypt(encrypted_data)
            except Exception:
                raise ValueError("Invalid bridge token or hardware profile mismatch.")
            
            # 3. Decompress and Parse
            decompressed = gzip.decompress(gzipped_data).decode('utf-8')
            records = []
            for line in decompressed.strip().split('\n'):
                if line.strip():
                    records.append(json.loads(line))
            return records
            
        except (ValueError, FileNotFoundError):
            raise
        except Exception as e:
            logger.error(f"In-memory decryption error: {e}")
            raise RuntimeError(f"Failed to decrypt log: {e}")

    def update_last_entry_feedback(self, feedback: str, corrected_response: str | None = None):
        """
        Rewrite the last line of the active jsonl file with the updated feedback
        and corrected response.
        """
        # _refresh_path handles locking internally
        self._refresh_path()
        
        with self._lock:
            if not self._log_file or not os.path.exists(self._log_file):
                return

            try:
                with open(self._log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                if not lines:
                    return

                last_line = lines[-1].strip()
                if not last_line:
                    return

                entry = json.loads(last_line)
                entry["feedback"] = feedback
                if corrected_response is not None:
                    entry["corrected_response"] = corrected_response

                lines[-1] = json.dumps(entry, ensure_ascii=False) + "\n"

                with open(self._log_file, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            except Exception as e:
                logger.warning(f"Error updating feedback: {e}")

