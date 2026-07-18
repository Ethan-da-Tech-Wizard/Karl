import logging
import os
import json
import uuid
import gzip
import shutil
import threading
import hashlib
import base64
import ctypes
import sys
from datetime import datetime, timezone
from contextlib import contextmanager

from app.utils import compactor

logger = logging.getLogger("karl.trace_logger")


_MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file before rotation

# PBKDF2-HMAC-SHA256 iteration counts for the archive encryption key.
# New archives always use the stronger count; decrypt paths also try the
# older, weaker count so archives written before this hardening pass remain
# readable.
_PBKDF2_ITERATIONS = 600_000
_LEGACY_PBKDF2_ITERATIONS = 100_000

# ── libc page locking ────────────────────────────────────────────────────────
_libc = None
if sys.platform != "win32":
    try:
        _libc = ctypes.CDLL(None)
    except Exception:
        _libc = None

_MCL_CURRENT = 1
_MCL_FUTURE  = 2


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
        threading.Thread(target=self.enforce_retention_policy, daemon=True).start()

    @staticmethod
    def read_jsonl(path: str) -> list[dict]:
        """Read a JSONL file, skipping empty or malformed lines."""
        records: list[dict] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict):
                        records.append(record)
        except OSError:
            return []
        return records

    @contextmanager
    def _secure_mem_lock(self):
        """Context manager to lock/unlock process memory in RAM on POSIX."""
        locked = False
        if _libc and hasattr(_libc, "mlockall"):
            res = _libc.mlockall(_MCL_CURRENT | _MCL_FUTURE)
            if res != 0:
                logger.debug(f"System warning: mlockall failed (code {res}). Memory pages could not be locked in RAM.")
            else:
                locked = True
        
        try:
            yield
        finally:
            if locked and _libc and hasattr(_libc, "munlockall"):
                _libc.munlockall()

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
        """
        Derives a Fernet-compatible encryption key from the bridge token and
        the machine-locked hardware UUID salt.

        Raises RuntimeError rather than falling back to any hardcoded
        password/salt/key: a static fallback baked into the source is public
        by definition, so silently downgrading to it would make every
        archive it protects trivially decryptable by anyone who has read
        this file. Callers (see _archive_log) must treat this as "cannot
        encrypt right now" and refuse to archive, not paper over it.
        """
        token_path = "data/bridge_token.json"
        if not os.path.exists(token_path):
            raise RuntimeError(
                f"No bridge token found at {token_path} — cannot derive a "
                "trace-log encryption key. Start the WebSocket bridge at "
                "least once (it provisions the token) before archiving logs."
            )
        with open(token_path, "r") as f:
            token_data = json.load(f)
        token = token_data.get("token")
        if not token:
            raise RuntimeError(f"{token_path} does not contain a usable bridge token.")

        # Machine-locked salt (motherboard UUID / machine-id derived).
        from core.hardware_scout import get_hardware_profile
        profile = get_hardware_profile()
        hardware_uuid = profile.get("hardware_uuid")
        if not hardware_uuid:
            raise RuntimeError(
                "Could not determine a hardware UUID salt for key derivation."
            )

        k = hashlib.pbkdf2_hmac(
            'sha256',
            token.encode(),
            hardware_uuid.encode(),
            _PBKDF2_ITERATIONS,
        )
        # Fernet keys must be 32 url-safe base64-encoded bytes
        return base64.urlsafe_b64encode(k)

    @staticmethod
    def _zero_bytes(ba: bytearray) -> None:
        """Overwrite every byte of *ba* with 0x00 in-place (cryptographic memory sanitization).

        This only scrubs the mutable bytearray passed in. It does NOT retroactively
        scrub the immutable `bytes` objects that fed into it upstream (e.g. the
        token/hardware_uuid encodes, the raw PBKDF2 digest, and the base64-encoded
        key in _get_encryption_key()) — CPython gives no way to zero an immutable
        object's backing memory, so those linger as ordinary garbage until the
        allocator happens to reuse that heap slot. mlockall() in _secure_mem_lock()
        prevents those pages from being swapped to disk while locked, but it is not
        equivalent to scrubbing them. Treat this as best-effort, not a guarantee
        that no copy of the key material remains in process memory.
        """
        for i in range(len(ba)):
            ba[i] = 0

    def prune_logs(self):
        """Deprecated: use enforce_retention_policy."""
        self.enforce_retention_policy(self.log_dir)

    def enforce_retention_policy(self, logs_dir="data/logs"):
        """
        Deletes trace logs and token streams whose age exceeds retention limits,
        and enforces maximum folder size on disk by deleting the oldest files.
        """
        try:
            from app.engine import config_store
            config = config_store.get_ui_config()
            retention_days = config.get("log_retention_days", 30)
            max_size_mb = config.get("max_log_disk_size_mb", 1024)
        except Exception:
            retention_days = 30
            max_size_mb = 1024

        reclaimed_bytes = 0

        # Step 1: Remove aged logs
        if retention_days and retention_days > 0:
            now = datetime.now(timezone.utc)
            for root, _, files in os.walk(logs_dir):
                for f in files:
                    if f.endswith((".jsonl", ".jsonl.compact", ".gz", ".enc", ".tokens")):
                        filepath = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(filepath)
                            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                            age_days = (now - mtime_dt).days
                            if age_days > retention_days:
                                size = os.path.getsize(filepath)
                                os.remove(filepath)
                                reclaimed_bytes += size
                                logger.info(f"Retention policy: deleted aged file {f} ({size} bytes)")
                        except Exception as e:
                            logger.warning(f"Failed to delete {f} during age sweep: {e}")

        # Step 2: Enforce folder disk size cap
        if max_size_mb and max_size_mb > 0:
            max_bytes = max_size_mb * 1024 * 1024
            
            # Collect all log files with their mtimes and sizes
            log_files = []
            total_size = 0
            for root, _, files in os.walk(logs_dir):
                for f in files:
                    if f.endswith((".jsonl", ".jsonl.compact", ".gz", ".enc", ".tokens")):
                        filepath = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(filepath)
                            size = os.path.getsize(filepath)
                            log_files.append((filepath, mtime, size))
                            total_size += size
                        except Exception:
                            pass

            if total_size > max_bytes:
                # Sort by mtime ascending (oldest first)
                log_files.sort(key=lambda x: x[1])
                for filepath, _, size in log_files:
                    if total_size <= max_bytes:
                        break
                    try:
                        os.remove(filepath)
                        total_size -= size
                        reclaimed_bytes += size
                        logger.info(f"Disk quota: deleted old file {os.path.basename(filepath)} ({size} bytes)")
                    except Exception as e:
                        logger.warning(f"Failed to delete {filepath} during quota sweep: {e}")

        if reclaimed_bytes > 0:
            logger.info(f"Log governance: reclaimed {reclaimed_bytes / (1024 * 1024):.2f} MB")

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
            
            with self._secure_mem_lock():
                # 1. Gzip compress in memory
                with open(file_path, 'rb') as f_in:
                    gzipped_data = gzip.compress(f_in.read())
                
                # 2. Encrypt — hold key in a mutable bytearray so it can be zeroed after use
                key_ba = bytearray(self._get_encryption_key())
                try:
                    fernet = Fernet(bytes(key_ba))
                    encrypted_data = fernet.encrypt(gzipped_data)
                finally:
                    TraceLogger._zero_bytes(key_ba)
                
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
            # Deliberately do NOT fall back to plaintext or a weaker key here:
            # this branch is reached when _get_encryption_key() refuses to
            # derive a key (see its docstring). The source file is left in
            # place, unarchived — it stays as an ordinary plaintext trace log
            # under log_dir (no worse than before archival was attempted) and
            # will be retried on the next rotation, rather than silently
            # protected by a key an attacker could trivially reproduce.
            logger.critical(
                "Could not encrypt-archive %s: %s. Leaving it unarchived under "
                "%s until the key can be derived (see _get_encryption_key).",
                file_path, e, self.log_dir,
            )

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

    @staticmethod
    def _compact_log_path(jsonl_path: str) -> str:
        return f"{jsonl_path}.compact"

    def _append_compact_entry(self, jsonl_path: str, entry: dict) -> None:
        compact_path = self._compact_log_path(jsonl_path)
        try:
            with open(compact_path, "a", encoding="utf-8") as f:
                f.write(compactor.compact_trace_for_ai(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write compact trace log {compact_path}: {e}")

    def _rewrite_compact_file(self, jsonl_path: str, entries: list[dict]) -> None:
        compact_path = self._compact_log_path(jsonl_path)
        try:
            with open(compact_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(compactor.compact_trace_for_ai(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to rewrite compact trace log {compact_path}: {e}")

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
        throttle_reasons: list[str] | None = None,
        cooling_duration_sec: float = 0.0,
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
            "throttle_reasons": throttle_reasons or [],
            "cooling_duration_sec": round(cooling_duration_sec, 3),
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
            self._append_compact_entry(self._log_file, entry)

        return self._log_file

    @staticmethod
    def decrypt_in_memory(token: str, file_path: str) -> list[dict]:
        """
        Decrypts an archived .enc log file in RAM without writing to disk.
        Returns a list of parsed JSON records.
        """
        locked = False
        if _libc and hasattr(_libc, "mlockall"):
            res = _libc.mlockall(_MCL_CURRENT | _MCL_FUTURE)
            if res != 0:
                logger.debug(f"System warning: mlockall failed (code {res}). Memory pages could not be locked in RAM.")
            else:
                locked = True

        try:
            from cryptography.fernet import Fernet
            import hashlib
            import base64
            from core.hardware_scout import get_hardware_profile

            # 1. Derive key from PROVIDED token and the SAME motherboard-UUID salt
            # used by _get_encryption_key() at archive time. This must match
            # exactly, or every archive encrypted by _archive_log() becomes
            # permanently undecryptable. No fallback salt is used here: a
            # missing hardware UUID means the key can't possibly match what
            # was used at archive time (that path now also refuses to use a
            # fallback — see _get_encryption_key), so guessing would just
            # waste time before failing anyway.
            profile = get_hardware_profile()
            hardware_uuid = profile.get("hardware_uuid")
            if not hardware_uuid:
                raise ValueError("Could not determine a hardware UUID salt for key derivation.")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archive not found: {file_path}")

            with open(file_path, 'rb') as f_in:
                encrypted_data = f_in.read()

            # 2. Decrypt — try the current iteration count first, then the
            # legacy (pre-hardening) count so archives written before the
            # PBKDF2 iteration bump remain readable.
            gzipped_data = None
            last_exc: Exception | None = None
            for iterations in (_PBKDF2_ITERATIONS, _LEGACY_PBKDF2_ITERATIONS):
                k = hashlib.pbkdf2_hmac('sha256', token.encode(), hardware_uuid.encode(), iterations)
                key = base64.urlsafe_b64encode(k)
                try:
                    gzipped_data = Fernet(key).decrypt(encrypted_data)
                    break
                except Exception as exc:
                    last_exc = exc
            if gzipped_data is None:
                raise ValueError("Invalid bridge token or hardware profile mismatch.") from last_exc

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
        finally:
            if locked and _libc and hasattr(_libc, "munlockall"):
                _libc.munlockall()

    @staticmethod
    def decrypt_to_bytearray(file_path: str, key: bytes) -> bytearray:
        """
        Decrypt *file_path* (Fernet-encrypted gzipped JSONL) using the provided
        pre-derived key and return the decompressed plaintext as a mutable bytearray.
        The caller is responsible for calling _zero_bytes() on the result when finished.
        """
        from cryptography.fernet import Fernet as _Fernet
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archive not found: {file_path}")
        with open(file_path, "rb") as fh:
            encrypted_data = fh.read()
        fernet = _Fernet(key)
        try:
            gzipped = fernet.decrypt(encrypted_data)
        except Exception:
            raise ValueError("Decryption failed: invalid key or corrupted archive.")
        return bytearray(gzip.decompress(gzipped))

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

                entries = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        entries.append(parsed)
                self._rewrite_compact_file(self._log_file, entries)
            except Exception as e:
                logger.warning(f"Error updating feedback: {e}")
