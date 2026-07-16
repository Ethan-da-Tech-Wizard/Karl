"""
WebSocket Server Manager — Karl Workbench
==========================================
Hosts a local WebSocket server to bridge communication between Karl's Multi-Agent Swarm
and editor extensions (such as VS Code/Code OSS).
"""

import logging
import os
import json
import asyncio
import threading
import re
import time
import uuid
import ssl
import subprocess
import pathlib
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import websockets
from websockets.datastructures import Headers
from websockets.http11 import Response
from typing import Set, Optional, Any
from PyQt6.QtCore import Qt

from app.engine import config_store
from app.engine.swarm_orchestrator import SwarmOrchestratorThread
from app.engine.inference_service import InferenceService
from app.engine.model_loader import CircuitBreakerOpenException, ModelLoader
from app.utils.rag_pipeline import RAGPipeline
from app.ui.workspaces.docs_data import DEFAULT_LIBRARY
from app.ui.workspaces.prompt_lab import generate_char_diff_html
from app.utils.keychain_manager import save_cached_token
from app.utils.correlation_logger import new_correlation_id, set_correlation_id


logger = logging.getLogger("karl.websocket")


class WebSocketServerManager:
    """Secure JSON-RPC 2.0 WebSocket bridge for editor integrations."""

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, port: int = 8080, state=None) -> "WebSocketServerManager":
        """Return the process-wide bridge manager, creating it if necessary."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(port, state)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Forces recreation of the singleton on the next call."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.stop()
                cls._instance = None

    def __init__(self, port: int = 8080, state=None):
        """Initialize bridge state, token security, SSL files, and event loop.

        Args:
            port: Preferred local WSS port. Startup may use the next available
                port in the configured range.
            state: Optional AppState. When provided, its RAG pipeline is reused.
        """
        self.port = port
        self.state = state
        self.clients: Set[Any] = set()
        self.client_metadata = {} # client -> {id, ip, latency}
        self.client_histories = {}
        self._clients_lock = threading.Lock()
        self.last_generation_metrics = {
            "prefill_duration_seconds": 0.0,
            "tokens_per_second": 0.0,
            "kv_cache_hit_rate": 0.0,
            "vram_delta_mb": 0.0,
        }
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self.orchestrator: Optional[SwarmOrchestratorThread] = None
        self.chat_thread = None
        self.mini_train_thread = None
        self._lease_audit_task: asyncio.Task | None = None
        # Guards orchestrator/chat_thread hand-off: the asyncio handler
        # (loop thread) and stop() (Qt thread) both stop/replace them.
        self._threads_lock = threading.Lock()
        self.kb_ingest_thread: Optional[threading.Thread] = None
        if state is not None:
            self.rag = state.rag
        else:
            self.rag = RAGPipeline()
        self._inference_service = InferenceService(state)
        self._seed_codex()
        self._init_security()
        self._ensure_ssl_certs()
        self.server = None
        self.started_event = threading.Event()
        self._start_loop_thread()

    _TOKEN_LIFETIME = 43_200      # 12 hours in seconds
    _LEASE_AUDIT_INTERVAL = 60    # seconds between session-lease sweeps
    _CLOSE_CODE_UNAUTHORIZED = 4001
    _CLOSE_CODE_LEASE_EXPIRED = 4002
    _CLOSE_CODE_REVOKED = 4003
    _TOKEN_PATH = "data/bridge_token.json"

    # Ordered from least to most privileged — also written to bridge_token.json.
    _FULL_SCOPES: list[str] = [
        "read:telemetry",
        "read:kb",
        "write:kb",
        "admin:execute",
    ]

    # Maps each guarded RPC method to the single scope it requires.
    # Methods absent from this dict are accessible to any authenticated client.
    METHOD_SCOPES: dict[str, str] = {
        "get_runtime_status": "read:telemetry",
        "list_kb_sources":    "read:kb",
        "search_kb":          "read:kb",
        "ingest_path":        "write:kb",
        "submit_task":        "admin:execute",
        "submit_chat":        "admin:execute",
    }
    _SSL_CERT_PATH = "data/ssl/localhost.crt"
    _SSL_KEY_PATH = "data/ssl/localhost.key"
    _JSONRPC_VERSION = "2.0"
    _RPC_ERROR_MESSAGES = {
        -32700: "Parse error",
        -32600: "Invalid Request",
        -32601: "Method not found",
        -32602: "Invalid params",
        -32603: "Internal error",
    }
    _RPC_METHODS = {
        "authenticate",
        "refresh_token",
        "get_runtime_status",
        "list_models",
        "set_active_model",
        "list_prompt_pairs",
        "get_prompt_pair",
        "save_prompt_pair",
        "delete_prompt_pair",
        "list_kb_sources",
        "ingest_path",
        "search_kb",
        "submit_task",
        "stop_task",
        "submit_chat",
        "list_codex_topics",
        "get_codex_content",
        "compute_diff",
        "start_auto_train",
        "fit_vectorizer",
        "start_mini_train",
        "create_custom_agent",
        "list_custom_agents",
    }

    def _ensure_ssl_certs(self):
        """Generates self-signed localhost SSL certificates if missing."""
        ssl_dir = os.path.dirname(self._SSL_CERT_PATH)
        os.makedirs(ssl_dir, exist_ok=True)
        
        if not os.path.exists(self._SSL_CERT_PATH) or not os.path.exists(self._SSL_KEY_PATH):
            logger.info("Generating self-signed SSL certificates for WSS...")
            try:
                # Use openssl command if available
                cmd = [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-keyout", self._SSL_KEY_PATH,
                    "-out", self._SSL_CERT_PATH,
                    "-sha256", "-days", "3650", "-nodes",
                    "-subj", "/C=XX/ST=State/L=City/O=Karl/OU=Engine/CN=localhost"
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"SSL certificates generated at {self._SSL_CERT_PATH}")
            except Exception as e:
                logger.error(f"Failed to generate SSL certificates: {e}. WSS server will fail to start.")

    def _init_security(self):
        """Initialise the multi-token store and safe-path rules."""
        self.bridge_token: str = ""
        self._token_created_at: float = 0.0
        self._token_store: dict[str, list[str]] = {}

        env_token = os.environ.get("KARL_BRIDGE_TOKEN", "").strip()
        if env_token:
            self.bridge_token = env_token
            self._token_created_at = time.time()
            self._token_store = {env_token: list(self._FULL_SCOPES)}
            self._persist_token_store()
            save_cached_token(self.bridge_token)
        elif os.path.exists(self._TOKEN_PATH):
            try:
                with open(self._TOKEN_PATH, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if "tokens" in payload:
                    # New multi-token format
                    self._token_store = {k: list(v) for k, v in payload["tokens"].items()}
                    self._token_created_at = float(payload.get("created_at", 0.0))
                else:
                    # Legacy single-token format — migrate in place
                    old_tok = payload.get("token", "")
                    self._token_created_at = float(payload.get("created_at", 0.0))
                    if old_tok:
                        self._token_store = {old_tok: list(self._FULL_SCOPES)}
                # Identify the admin token (first one carrying admin:execute scope)
                self.bridge_token = next(
                    (tok for tok, sc in self._token_store.items() if "admin:execute" in sc),
                    "",
                )
                if time.time() - self._token_created_at > self._TOKEN_LIFETIME or not self.bridge_token:
                    self._rotate_token()
                else:
                    save_cached_token(self.bridge_token)
            except Exception:
                self._rotate_token()
        else:
            self._rotate_token()

        # Sensitive directories that should never be targeted by agents or RAG
        self.blocked_paths = {
            "/", "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
            "/var", "/boot", "/dev", "/proc", "/sys", "/root"
        }
        user_home = os.path.expanduser("~")
        self.blocked_paths.add(user_home)
        self.blocked_paths.add(os.path.join(user_home, "Desktop"))
        self.blocked_paths.add(os.path.join(user_home, "Documents"))
        self.blocked_paths.add(os.path.join(user_home, "Downloads"))

    def _generate_token(self) -> str:
        return uuid.uuid4().hex

    def _rotate_token(self) -> None:
        """Generate a fresh admin token.

        Non-admin scoped tokens in _token_store are preserved so that
        previously issued read-only/KB keys stay valid after rotation.
        """
        # Drop the previous admin token only
        if not hasattr(self, "_token_store"):
            self._token_store = {}
        self._token_store.pop(self.bridge_token, None)
        self.bridge_token = self._generate_token()
        self._token_created_at = time.time()
        self._token_store[self.bridge_token] = list(self._FULL_SCOPES)
        self._persist_token_store()
        save_cached_token(self.bridge_token)

    def _persist_token_store(self) -> None:
        """Write the in-memory token store to data/bridge_token.json."""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self._TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "token": self.bridge_token,
                        "tokens": self._token_store,
                        "created_at": self._token_created_at,
                    },
                    f,
                    indent=2,
                )
        except Exception as exc:
            logger.warning("Could not persist token store: %s", exc)

    def add_scoped_token(self, scopes: list[str]) -> str:
        """Generate and register a new token with *scopes*. Returns the token hex."""
        token = self._generate_token()
        if not hasattr(self, "_token_store"):
            self._token_store = {}
        self._token_store[token] = list(scopes)
        self._persist_token_store()
        logger.info("Scoped token added: scopes=%s", scopes)
        return token

    def _get_token_scopes(self, token: str) -> list[str] | None:
        """Return scopes for *token* if valid and unexpired, else None."""
        if not token:
            return None
        if not hasattr(self, "_token_store"):
            return None
        if time.time() - self._token_created_at > self._TOKEN_LIFETIME:
            logger.info("Token store expired (12h). Rotating.")
            self._rotate_token()
            return None
        return self._token_store.get(token)

    def _validate_token(self, token: str) -> bool:
        """Returns True if token is present in the store and unexpired."""
        return self._get_token_scopes(token) is not None

    def _is_safe_path(self, path: str) -> bool:
        """Checks if a path is outside sensitive system directories.

        Uses os.path.realpath so that symlinks pointing into blocked directories
        are caught before any filesystem operation is performed on them.
        """
        if not path:
            return False
        real_path = os.path.realpath(os.path.expanduser(path))

        for blocked in self.blocked_paths:
            real_blocked = os.path.realpath(blocked)
            if real_path == real_blocked or real_path.startswith(real_blocked + os.sep):
                project_root = os.path.realpath(os.getcwd())
                if real_path == project_root or real_path.startswith(project_root + os.sep):
                    return True
                return False
        return True

    def _seed_codex(self):
        library_dir = "data/codex_library"
        os.makedirs(library_dir, exist_ok=True)
        version_filepath = os.path.join(library_dir, ".version")
        current_version = "5.0"

        needs_upgrade = True
        if os.path.exists(version_filepath):
            try:
                with open(version_filepath, "r", encoding="utf-8") as vf:
                    if vf.read().strip() == current_version:
                        needs_upgrade = False
            except OSError as exc:
                logger.warning("could not read codex version file %s: %s", version_filepath, exc)

        if needs_upgrade or not [f for f in os.listdir(library_dir) if f.endswith((".html", ".md"))]:
            for topic, content in DEFAULT_LIBRARY.items():
                safe_name = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip()
                filepath = os.path.join(library_dir, f"{safe_name}.html")
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                except OSError as exc:
                    logger.warning("could not seed codex topic %r to %s: %s", topic, filepath, exc)
            try:
                with open(version_filepath, "w", encoding="utf-8") as vf:
                    vf.write(current_version)
            except OSError as exc:
                logger.warning("could not write codex version file %s: %s", version_filepath, exc)

    def _active_model_config(self) -> dict:
        return config_store.get_active_model()

    def _read_model_registry(self) -> list[dict]:
        return config_store.get_model_registry()

    def _list_models(self) -> dict:
        models_dir = os.path.join("data", "models")
        active = self._active_model_config()
        registry = self._read_model_registry()
        registered = {}
        models = []

        for entry in registry:
            filename = entry.get("filename")
            if not filename:
                continue
            registered[filename] = True
            path = os.path.join(models_dir, filename)
            installed = os.path.exists(path)
            size_gb = None
            if installed:
                try:
                    size_gb = round(os.path.getsize(path) / (1024 ** 3), 2)
                except OSError as exc:
                    logger.debug("could not stat model file %s: %s", path, exc)
            models.append({
                "name": entry.get("name", filename),
                "filename": filename,
                "tier": entry.get("tier"),
                "n_ctx": entry.get("n_ctx", 4096),
                "min_ram_gb": entry.get("min_ram_gb"),
                "min_vram_gb": entry.get("min_vram_gb"),
                "min_storage_gb": entry.get("min_storage_gb"),
                "installed": installed,
                "active": filename == active["filename"],
                "size_gb": size_gb,
                "source": "registry",
            })

        if os.path.exists(models_dir):
            try:
                for filename in sorted(os.listdir(models_dir)):
                    if not filename.endswith(".gguf") or registered.get(filename):
                        continue
                    path = os.path.join(models_dir, filename)
                    try:
                        size_gb = round(os.path.getsize(path) / (1024 ** 3), 2)
                    except OSError as exc:
                        logger.debug("could not stat model file %s: %s", path, exc)
                        size_gb = None
                    models.append({
                        "name": filename,
                        "filename": filename,
                        "tier": None,
                        "n_ctx": ModelLoader._read_registry_n_ctx(filename),
                        "min_ram_gb": None,
                        "min_vram_gb": None,
                        "min_storage_gb": None,
                        "installed": True,
                        "active": filename == active["filename"],
                        "size_gb": size_gb,
                        "source": "local",
                    })
            except OSError as exc:
                logger.warning("could not scan models directory %s: %s", models_dir, exc)

        return {
            "active": active,
            "models": models,
        }

    def _set_active_model(self, filename: str, adapter: str | None = None) -> dict:
        safe_filename = os.path.basename(filename or "")
        if not safe_filename or safe_filename != filename:
            raise ValueError("Invalid model filename.")

        model_path = os.path.join("data", "models", safe_filename)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file is not installed: {safe_filename}")

        active = {"filename": safe_filename}
        if adapter:
            safe_adapter = os.path.basename(adapter)
            if not safe_adapter or safe_adapter != adapter or "." in adapter:
                raise ValueError("Invalid adapter name.")
            active["adapter"] = adapter

        if not config_store.set_active_model(safe_filename, adapter):
            raise OSError("Failed to persist data/active_model.json")

        ModelLoader.reset_instance()
        return {
            "active": active,
            "loaded": False,
            "message": f"Active model set to {safe_filename}. It will load on the next generation.",
        }

    def _prompt_pairs_dir(self) -> str:
        path = os.path.join("data", "prompt_pairs")
        os.makedirs(path, exist_ok=True)
        return path

    def _safe_prompt_pair_name(self, name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", (name or "").strip())
        if not safe_name:
            raise ValueError("Prompt pair name is required.")
        return safe_name

    def _prompt_pair_path(self, name: str) -> str:
        return os.path.join(self._prompt_pairs_dir(), f"{self._safe_prompt_pair_name(name)}.json")

    def _list_prompt_pairs(self) -> dict:
        pairs = []
        for filename in sorted(os.listdir(self._prompt_pairs_dir())):
            if not filename.endswith(".json"):
                continue
            name = os.path.splitext(filename)[0]
            path = os.path.join(self._prompt_pairs_dir(), filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("could not read prompt pair %s: %s", path, exc)
                data = {}
            pairs.append({
                "name": name,
                "system_a": data.get("system_a", ""),
                "system_b": data.get("system_b", ""),
                "user_a": data.get("user_a", ""),
                "user_b": data.get("user_b", ""),
                "model_a": data.get("model_a"),
                "model_b": data.get("model_b"),
            })
        return {"pairs": pairs}

    def _get_prompt_pair(self, name: str) -> dict:
        safe_name = self._safe_prompt_pair_name(name)
        path = self._prompt_pair_path(safe_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt pair not found: {safe_name}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["name"] = safe_name
        return data

    def _save_prompt_pair(self, params: dict) -> dict:
        name = self._safe_prompt_pair_name(params.get("name", ""))
        data = {
            "name": name,
            "system_a": params.get("system_a", ""),
            "user_a": params.get("user_a", ""),
            "system_b": params.get("system_b", ""),
            "user_b": params.get("user_b", ""),
            "model_a": params.get("model_a"),
            "adapter_a": params.get("adapter_a"),
            "model_b": params.get("model_b"),
            "adapter_b": params.get("adapter_b"),
            "rag_a": bool(params.get("rag_a", False)),
            "loop_a": bool(params.get("loop_a", False)),
            "rag_b": bool(params.get("rag_b", False)),
            "loop_b": bool(params.get("loop_b", False)),
            "output_a_raw": params.get("output_a_raw", ""),
            "output_b_raw": params.get("output_b_raw", ""),
            "output_a_display": params.get("output_a_display", ""),
            "output_b_display": params.get("output_b_display", ""),
        }
        with open(self._prompt_pair_path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return {"name": name, "saved": True}

    def _delete_prompt_pair(self, name: str) -> dict:
        safe_name = self._safe_prompt_pair_name(name)
        path = self._prompt_pair_path(safe_name)
        if os.path.exists(path):
            os.remove(path)
        return {"name": safe_name, "deleted": True}

    def _kb_supported_extensions(self) -> set[str]:
        return {".pdf", ".docx", ".txt", ".md", ".py", ".csv"}

    def _kb_snapshot(self) -> dict:
        self.rag._load_index()
        sources = []
        counts = {}
        ingested_at = {}
        for doc in self.rag.documents:
            source = doc.get("source_file", "unknown")
            counts[source] = counts.get(source, 0) + 1
            if source not in ingested_at:
                ingested_at[source] = doc.get("ingested_at")

        for source in sorted(counts):
            sources.append({
                "name": source,
                "chunks": counts[source],
                "ingested_at": ingested_at.get(source),
            })

        return {
            "sources": sources,
            "total_sources": len(sources),
            "total_chunks": self.rag.total_chunks,
            "supported_extensions": sorted(self._kb_supported_extensions()),
            "ingesting": bool(self.kb_ingest_thread and self.kb_ingest_thread.is_alive()),
        }

    def _collect_kb_files(self, path: str, recursive: bool) -> list[str]:
        if not path:
            raise ValueError("Path is required.")

        expanded = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(expanded):
            ext = os.path.splitext(expanded)[1].lower()
            if ext not in self._kb_supported_extensions():
                raise ValueError(f"Unsupported file type: {ext or 'none'}")
            return [expanded]

        if not os.path.isdir(expanded):
            raise FileNotFoundError(f"Path not found: {path}")

        files = []
        if recursive:
            for root, dirs, names in os.walk(expanded):
                dirs[:] = [d for d in dirs if d not in {".git", "venv", ".venv", "__pycache__", "node_modules"}]
                for name in names:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in self._kb_supported_extensions():
                        files.append(os.path.join(root, name))
        else:
            for name in os.listdir(expanded):
                candidate = os.path.join(expanded, name)
                ext = os.path.splitext(name)[1].lower()
                if os.path.isfile(candidate) and ext in self._kb_supported_extensions():
                    files.append(candidate)

        return sorted(files)

    def _start_kb_ingest(self, params: dict) -> dict:
        if self.kb_ingest_thread and self.kb_ingest_thread.is_alive():
            raise RuntimeError("Knowledge Base ingestion is already running.")

        path = params.get("path", "")
        recursive = bool(params.get("recursive", True))
        chunk_size = int(params.get("chunk_size", 200))
        overlap = int(params.get("overlap", 50))
        if chunk_size < 50 or chunk_size > 2000:
            raise ValueError("chunk_size must be between 50 and 2000.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and lower than chunk_size.")

        files = self._collect_kb_files(path, recursive)
        if not files:
            raise ValueError("No supported files found for ingestion.")

        task_id = str(uuid.uuid4())

        def worker():
            total = len(files)

            def progress_cb(current: int, total_files: int, event: dict):
                self._send_notification("kb_ingest_progress", {
                    "task_id": task_id,
                    "current": current,
                    "total": total_files,
                    "filename": event.get("filename", ""),
                    "chunks": int(event.get("chunks", 0) or 0),
                    "status": event.get("status", "parsed"),
                })

            if hasattr(self.rag, "ingest_files"):
                result = self.rag.ingest_files(
                    files,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    batch_size=32,
                    progress_cb=progress_cb,
                )
            else:
                total_chunks = 0
                per_file = []
                errors = []
                for index, filepath in enumerate(files, 1):
                    filename = os.path.basename(filepath)
                    progress_cb(index, total, {"filename": filename, "status": "parsed"})
                    try:
                        chunks = self.rag.ingest_file(
                            filepath,
                            chunk_size=chunk_size,
                            overlap=overlap,
                        )
                        total_chunks += chunks
                        per_file.append({
                            "path": filepath,
                            "filename": filename,
                            "chunks": chunks,
                        })
                    except Exception as exc:
                        errors.append({
                            "path": filepath,
                            "filename": filename,
                            "error": str(exc),
                        })
                result = {
                    "files": per_file,
                    "errors": errors,
                    "file_count": len(per_file),
                    "error_count": len(errors),
                    "chunks_added": total_chunks,
                }

            self._send_notification("kb_ingest_finished", {
                "task_id": task_id,
                "files": result["files"],
                "errors": result["errors"],
                "file_count": result["file_count"],
                "error_count": result["error_count"],
                "chunks_added": result["chunks_added"],
                "queued_file_count": total,
                "snapshot": self._kb_snapshot(),
            })

        self.kb_ingest_thread = threading.Thread(target=worker, daemon=True)
        self.kb_ingest_thread.start()
        return {
            "status": "started",
            "task_id": task_id,
            "file_count": len(files),
            "path": os.path.abspath(os.path.expanduser(path)),
        }

    def _search_kb(self, params: dict) -> dict:
        query = (params.get("query") or "").strip()
        if not query:
            raise ValueError("query is required.")

        top_k = int(params.get("top_k", 3))
        threshold = float(params.get("threshold", 0.0))
        source_filter = params.get("source_filter") or None
        top_k = max(1, min(top_k, 25))
        threshold = max(0.0, threshold)

        self.rag._load_index()
        results = self.rag.retrieve_with_metadata(
            query,
            top_k=top_k,
            source_filter=source_filter,
        )
        if threshold > 0.0:
            results = [r for r in results if float(r.get("distance", 0.0)) <= threshold]

        return {
            "query": query,
            "top_k": top_k,
            "threshold": threshold,
            "source_filter": source_filter,
            "results": [
                {
                    "text": r.get("text", ""),
                    "source_file": r.get("source_file", "unknown"),
                    "chunk_id": r.get("chunk_id"),
                    "rank": r.get("rank"),
                    "distance": float(r.get("distance", 0.0)),
                    "ingested_at": r.get("ingested_at"),
                }
                for r in results
            ],
            "snapshot": self._kb_snapshot(),
        }

    def _runtime_status(self) -> dict:
        active_model = self._active_model_config()
        loaded = ModelLoader.is_loaded()
        model_name = ModelLoader.model_name() if loaded else active_model["filename"]
        adapter = getattr(ModelLoader, "_active_adapter", None) if loaded else active_model["adapter"]
        n_ctx = ModelLoader.n_ctx() if loaded else ModelLoader._read_registry_n_ctx(model_name)
        swarm_active = bool(self.orchestrator and self.orchestrator.isRunning())
        chat_active = bool(self.chat_thread and self.chat_thread.isRunning())

        ram_mb = None
        try:
            import psutil
            ram_mb = round(psutil.Process(os.getpid()).memory_info().rss / 1_048_576, 1)
        except Exception:
            pass

        return {
            "bridge": {
                "port": self.port,
                "clients": len(self.clients),
                "listening": self.server is not None,
            },
            "runtime": {
                "state": "running" if (swarm_active or chat_active) else "idle",
                "swarm_active": swarm_active,
                "chat_active": chat_active,
            },
            "model": {
                "name": model_name,
                "loaded": loaded,
                "n_ctx": n_ctx,
            },
            "adapter": {
                "name": adapter,
                "loaded": bool(adapter),
            },
            "system": {
                "ram_mb": ram_mb,
            },
        }

    def _rpc_error_response(
        self,
        code: int,
        req_id: Any = None,
        message: str | None = None,
        data: Any = None,
    ) -> dict:
        error = {
            "code": code,
            "message": message or self._RPC_ERROR_MESSAGES.get(code, "Error"),
        }
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": self._JSONRPC_VERSION,
            "error": error,
            "id": req_id,
        }

    def _rpc_result_response(self, req_id: Any, result: Any) -> dict:
        return {
            "jsonrpc": self._JSONRPC_VERSION,
            "id": req_id,
            "result": result,
        }

    async def _send_rpc_error(
        self,
        websocket,
        code: int,
        req_id: Any = None,
        message: str | None = None,
        data: Any = None,
    ) -> None:
        await websocket.send(json.dumps(self._rpc_error_response(code, req_id, message, data)))

    async def _send_rpc_result(self, websocket, req_id: Any, result: Any) -> None:
        await websocket.send(json.dumps(self._rpc_result_response(req_id, result)))

    def _parse_json_rpc_request(self, message: str) -> tuple[dict | None, dict | None]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError as exc:
            return None, self._rpc_error_response(-32700, None, data=str(exc))

        req_id = data.get("id") if isinstance(data, dict) else None
        if not isinstance(data, dict):
            return None, self._rpc_error_response(-32600, req_id)
        if data.get("jsonrpc") != self._JSONRPC_VERSION:
            return None, self._rpc_error_response(-32600, req_id)
        method = data.get("method")
        if not isinstance(method, str) or not method:
            return None, self._rpc_error_response(-32600, req_id)
        if method not in self._RPC_METHODS:
            return None, self._rpc_error_response(
                -32601,
                req_id,
                data=f"Method not found: {method}",
            )

        params = data.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return None, self._rpc_error_response(
                -32602,
                req_id,
                data="params must be an object when provided.",
            )
        data["params"] = params
        return data, None

    def _validate_rpc_params(self, method: str, params: dict) -> str | None:
        def require_string(name: str) -> str | None:
            value = params.get(name)
            if not isinstance(value, str) or not value.strip():
                return f"{name} is required and must be a string."
            return None

        if method == "set_active_model":
            return require_string("filename")
        if method == "get_prompt_pair":
            return require_string("name")
        if method == "save_prompt_pair":
            return require_string("name")
        if method == "delete_prompt_pair":
            return require_string("name")
        if method == "ingest_path":
            return require_string("path")
        if method == "search_kb":
            return require_string("query")
        if method == "submit_chat":
            return require_string("message")
        if method == "submit_task":
            for name in ("objective", "workspace_path"):
                error = require_string(name)
                if error:
                    return error
        if method == "start_auto_train":
            for name in ("topic", "adapter_name"):
                error = require_string(name)
                if error:
                    return error
        if method == "fit_vectorizer":
            documents = params.get("documents")
            if not isinstance(documents, list) or not documents:
                return "documents is required and must be a non-empty list."
        return None

    def _record_generation_metrics(self, diagnostics: dict | None) -> None:
        diagnostics = diagnostics or {}
        prefill = diagnostics.get("prefill_duration_sec", diagnostics.get("prefill_time", 0.0))
        tps = diagnostics.get("tokens_per_second", diagnostics.get("generation_tps", 0.0))
        vram_delta = diagnostics.get("vram_usage_mb_delta", diagnostics.get("vram_delta_mb", 0.0))

        kv_hit_rate = diagnostics.get("kv_cache_hit_rate")
        if kv_hit_rate is None:
            kv_cache = diagnostics.get("kv_cache") or {}
            cached = kv_cache.get("tokens_from_cache", diagnostics.get("kv_cache_hits", 0))
            total = (
                diagnostics.get("prefill_tokens_count")
                or cached + kv_cache.get("tokens_to_eval", 0)
            )
            kv_hit_rate = (float(cached) / float(total)) if total else 0.0

        self.last_generation_metrics = {
            "prefill_duration_seconds": self._metric_float(prefill),
            "tokens_per_second": self._metric_float(tps),
            "kv_cache_hit_rate": max(0.0, min(1.0, self._metric_float(kv_hit_rate))),
            "vram_delta_mb": self._metric_float(vram_delta),
        }

    def _metric_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _process_rss_bytes(self) -> int:
        try:
            import psutil
            return int(psutil.Process(os.getpid()).memory_info().rss)
        except Exception:
            return 0

    def _prometheus_metrics(self) -> str:
        metrics = {
            "karl_active_connections": len(self.clients),
            "karl_system_memory_usage_bytes": self._process_rss_bytes(),
            "karl_prefill_duration_seconds": self.last_generation_metrics.get(
                "prefill_duration_seconds", 0.0
            ),
            "karl_tokens_per_second": self.last_generation_metrics.get(
                "tokens_per_second", 0.0
            ),
            "karl_kv_cache_hit_rate": self.last_generation_metrics.get(
                "kv_cache_hit_rate", 0.0
            ),
            "karl_vram_delta_mb": self.last_generation_metrics.get("vram_delta_mb", 0.0),
        }
        specs = [
            ("karl_active_connections", "Number of active WebSocket clients"),
            ("karl_system_memory_usage_bytes", "Resident memory usage of the Karl process in bytes"),
            ("karl_prefill_duration_seconds", "Prefill latency of the last generation in seconds"),
            ("karl_tokens_per_second", "Token generation throughput of the last generation"),
            ("karl_kv_cache_hit_rate", "KV cache hit rate of the last generation from 0.0 to 1.0"),
            ("karl_vram_delta_mb", "VRAM consumption delta of the last generation in megabytes"),
        ]

        lines = []
        for name, help_text in specs:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {metrics[name]}")
        return "\n".join(lines) + "\n"

    def _http_response(self, status_code: int, reason: str, content_type: str, body: str) -> Response:
        return Response(
            status_code,
            reason,
            Headers([
                ("Content-Type", content_type),
                ("Content-Length", str(len(body.encode("utf-8")))),
            ]),
            body.encode("utf-8"),
        )

    def _is_websocket_upgrade(self, request) -> bool:
        headers = getattr(request, "headers", {}) or {}
        try:
            upgrade = headers.get("Upgrade", "")
            connection = headers.get("Connection", "")
        except Exception:
            return False
        return upgrade.lower() == "websocket" or "upgrade" in connection.lower()

    def _process_http_request(self, connection, request) -> Response | None:
        path = getattr(request, "path", "") or ""
        parsed = urlparse(path)
        if parsed.path == "/metrics":
            return self._http_response(
                200,
                "OK",
                "text/plain; version=0.0.4; charset=utf-8",
                self._prometheus_metrics(),
            )
        if self._is_websocket_upgrade(request):
            return None
        return self._http_response(404, "Not Found", "text/plain; charset=utf-8", "Not Found\n")

    async def _audit_session_leases(self) -> None:
        """Periodically sweeps active connections and closes sessions whose lease
        has exceeded _TOKEN_LIFETIME without a refresh."""
        while True:
            await asyncio.sleep(self._LEASE_AUDIT_INTERVAL)
            now = time.time()
            expired = [
                ws
                for ws, meta in list(self.client_metadata.items())
                if now - meta.get("session_start", now) > self._TOKEN_LIFETIME
            ]
            for ws in expired:
                cid = self.client_metadata.get(ws, {}).get("id", "?")
                logger.info("Session lease expired for client %s — closing 4002.", cid)
                try:
                    await ws.close(self._CLOSE_CODE_LEASE_EXPIRED, "Session lease expired")
                except Exception as exc:
                    logger.debug("Error closing expired session %s: %s", cid, exc)

    async def _close_all_clients(self, code: int, reason: str) -> None:
        """Close every active WebSocket connection with *code* and *reason*."""
        clients = list(self.clients)
        if clients:
            await asyncio.gather(
                *[ws.close(code, reason) for ws in clients],
                return_exceptions=True,
            )

    def force_revoke(self) -> None:
        """Revoke the bridge token and force-close all active connections.

        Safe to call from any thread (e.g. management UI or CLI signal handler).
        """
        # Invalidate all in-memory tokens so no new auth can succeed
        self.bridge_token = ""
        self._token_created_at = 0.0
        self._token_store = {}

        # Wipe the on-disk token
        try:
            if os.path.exists(self._TOKEN_PATH):
                os.remove(self._TOKEN_PATH)
        except Exception as exc:
            logger.warning("force_revoke: could not remove token file: %s", exc)

        # Remove from OS keychain
        try:
            from app.utils.keychain_manager import revoke_tokens
            revoke_tokens()
        except Exception as exc:
            logger.warning("force_revoke: keychain revocation failed: %s", exc)

        # Close active WebSocket sessions
        if self.loop and self.loop.is_running():
            close_coro = self._close_all_clients(self._CLOSE_CODE_REVOKED, "Token revoked")
            try:
                asyncio.run_coroutine_threadsafe(close_coro, self.loop)
                logger.info("force_revoke: all connections scheduled for closure.")
            except Exception as exc:
                close_coro.close()
                logger.warning("force_revoke: could not schedule client closure: %s", exc)

    def _start_loop_thread(self):
        """Starts a background daemon thread running an asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_server())
        if self.server is not None:
            self._lease_audit_task = self.loop.create_task(self._audit_session_leases())
        try:
            self.loop.run_forever()
        finally:
            try:
                pending = asyncio.all_tasks(self.loop)
                if pending:
                    # Let the loop run to cancel tasks
                    for task in pending:
                        task.cancel()
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self.loop.close()

    _DISCOVERY_PATH = pathlib.Path.home() / ".karl" / "service_discovery.json"
    _PORT_RANGE = 10  # try self.port through self.port + 9

    def _build_ssl_context(self):
        """Return an SSL context from the project cert files, or raise RuntimeError."""
        if os.path.exists(self._SSL_CERT_PATH) and os.path.exists(self._SSL_KEY_PATH):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(self._SSL_CERT_PATH, self._SSL_KEY_PATH)
            logger.info("WSS Secure WebSockets enabled.")
            return ctx
        logger.error("WSS SSL certificates missing. Server will NOT start without WSS.")
        raise RuntimeError("SSL context required for WSS enforcement.")

    async def _start_server(self):
        try:
            host = os.environ.get("KARL_WS_HOST", "localhost")
            ssl_context = None

            # Standard WS (no SSL) bypasses self-signed certificate validation errors
            # in editor webviews, but is only safe for a strictly loopback bind.
            # "0.0.0.0" (and any other host) binds a network-reachable interface, so
            # TLS is mandatory there -- never fall back to plaintext on that path.
            if host in ("localhost", "127.0.0.1", "::1"):
                logger.info("Using standard WS (no SSL) for loopback-only server.")
            else:
                ssl_context = self._build_ssl_context()

            # Try self.port through self.port + _PORT_RANGE - 1 to survive conflicts.
            server = None
            last_exc: Exception | None = None
            for candidate in range(self.port, self.port + self._PORT_RANGE):
                try:
                    server = await websockets.serve(
                        self._handler,
                        host,
                        candidate,
                        ssl=ssl_context,
                        process_request=self._process_http_request,
                    )
                    self.port = candidate
                    break
                except OSError as exc:
                    logger.info("Port %d in use (%s). Trying %d.", candidate, exc, candidate + 1)
                    last_exc = exc

            if server is None:
                raise last_exc or OSError(
                    f"No port available in {self.port}–{self.port + self._PORT_RANGE - 1}"
                )

            self.server = server
            logger.info("Server running on wss://%s:%d", host, self.port)
            self._write_service_discovery()
        except Exception as e:
            logger.warning("Failed to start server: %s", e)
        finally:
            self.started_event.set()

    def _write_service_discovery(self) -> None:
        """Write ~/.karl/service_discovery.json so clients can locate this instance."""
        try:
            self._DISCOVERY_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._DISCOVERY_PATH.write_text(
                json.dumps({
                    "active_port": self.port,
                    "token": self.bridge_token,
                    "bound_at": datetime.now(timezone.utc).isoformat(),
                }),
                encoding="utf-8",
            )
            logger.info("Service discovery written: %s", self._DISCOVERY_PATH)
        except Exception as exc:
            logger.warning("Could not write service discovery: %s", exc)

    def _remove_service_discovery(self) -> None:
        """Remove ~/.karl/service_discovery.json on shutdown."""
        try:
            self._DISCOVERY_PATH.unlink(missing_ok=True)
            logger.info("Service discovery file removed.")
        except Exception as exc:
            logger.warning("Could not remove service discovery: %s", exc)

    def stop(self):
        """Synchronously shuts down the server and joins the background thread."""
        if self.loop and self.loop.is_running():
            with self._threads_lock:
                # Stop the orchestrator if running
                if self.orchestrator and self.orchestrator.isRunning():
                    self.orchestrator.request_stop()
                    self.orchestrator.wait()

                # Stop chat thread if running
                if self.chat_thread and self.chat_thread.isRunning():
                    if hasattr(self.chat_thread, "request_stop"):
                        self.chat_thread.request_stop()
                    self.chat_thread.wait()

                # Stop mini train thread if running
                if hasattr(self, "mini_train_thread") and self.mini_train_thread and self.mini_train_thread.isRunning():
                    self.mini_train_thread.stop()
                    self.mini_train_thread.wait()

            # Stop websockets server
            future = asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)
            try:
                future.result(timeout=5.0)
            except TimeoutError:
                future.cancel()
                logger.debug("Timed out waiting for WebSocket server cleanup; cancelling close task.")
            except Exception as e:
                logger.warning(f"Error closing server connection: {e}")

            # Stop the loop and join thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.loop_thread:
                self.loop_thread.join(timeout=2.0)
        self.clients.clear()

    async def _stop_server(self):
        audit_task = getattr(self, "_lease_audit_task", None)
        if audit_task is not None:
            audit_task.cancel()
            try:
                await audit_task
            except asyncio.CancelledError:
                pass
            self._lease_audit_task = None

        if self.clients:
            await asyncio.gather(
                *[client.close() for client in list(self.clients)],
                return_exceptions=True,
            )
            self.clients.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            logger.info("Server stopped.")

        self._remove_service_discovery()

    async def _handler(self, websocket, path=None):
        # ── Connection-stage token authentication ─────────────────────────────
        raw_path = path or ""
        if not raw_path:
            try:
                if hasattr(websocket, "request"):
                    raw_path = websocket.request.path
                else:
                    raw_path = getattr(websocket, "path", "") or ""
            except Exception:
                pass
        
        parsed = urlparse(raw_path)
        qs = parse_qs(parsed.query)
        url_token = qs.get("token", [""])[0]

        token_scopes = self._get_token_scopes(url_token)
        if token_scopes is None and self._validate_token(url_token):
            token_scopes = list(self._FULL_SCOPES)
        if token_scopes is None:
            remote = getattr(websocket, "remote_address", "unknown")
            logger.warning(
                "Rejected connection from %s: invalid or expired token (path: %s)",
                remote, raw_path,
            )
            await websocket.close(self._CLOSE_CODE_UNAUTHORIZED, "Unauthorized: invalid or expired token")
            return
        # ─────────────────────────────────────────────────────────────────────

        client_id = str(uuid.uuid4())[:8]
        ip = "unknown"
        try:
            ip = websocket.remote_address[0]
        except Exception:
            pass

        self.clients.add(websocket)
        self.client_metadata[websocket] = {
            "id": client_id,
            "ip": ip,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "session_start": time.time(),  # reset by refresh_token to extend lease
            "authenticated": True,
            "scopes": token_scopes,         # RBAC scope list for this connection
        }
        self.client_histories[websocket] = []
        logger.info(f"Client connected: {websocket.remote_address} (ID: {client_id})")
        try:
            async for message in websocket:
                data, rpc_error = self._parse_json_rpc_request(message)
                if rpc_error is not None:
                    await websocket.send(json.dumps(rpc_error))
                    continue

                method = data.get("method")
                params = data.get("params", {})
                req_id = data.get("id")
                token = params.get("token")

                # Bind a per-frame correlation ID so every log line emitted
                # during this request is tagged with the client and request ID.
                set_correlation_id(
                    f"ws:{client_id}:{req_id if req_id is not None else new_correlation_id()}"
                )

                params_error = self._validate_rpc_params(method, params)
                if params_error:
                    await self._send_rpc_error(websocket, -32602, req_id, data=params_error)
                    continue

                client_meta = self.client_metadata.get(websocket, {})

                if method == "authenticate":
                    # This method is now redundant for clients who passed handshake
                    is_valid = self._validate_token(token)
                    if is_valid:
                        client_meta["authenticated"] = True
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"authenticated": True}
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32000, "message": "Invalid token."}
                        }))
                    continue

                if method == "refresh_token":
                    client_token = params.get("token", "")
                    # Accept if the supplied token is current OR the connection is
                    # already authenticated (token was valid at handshake).
                    if self._validate_token(client_token) or client_meta.get("authenticated"):
                        old_scopes = list(client_meta.get("scopes", self._FULL_SCOPES))
                        # Issue a fresh token scoped to what this connection already
                        # held -- never the global admin bridge token. Minting the
                        # admin token here would let any authenticated (even
                        # read-only) client hand itself full admin scope on a new
                        # connection.
                        new_token = self.add_scoped_token(old_scopes)
                        client_meta["scopes"] = old_scopes
                        client_meta["session_start"] = time.time()
                        expires_at = client_meta["session_start"] + self._TOKEN_LIFETIME
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "token": new_token,
                                "expires_at": expires_at,
                            },
                        }))
                        logger.info(
                            "Token refreshed for client %s. New expiry in %ds.",
                            client_meta.get("id", "?"),
                            int(self._TOKEN_LIFETIME),
                        )
                    else:
                        await self._send_rpc_error(
                            websocket, -32000, req_id, message="Invalid token for refresh."
                        )
                    continue

                # Scope enforcement — verify the client's token carries the
                # required scope for this method before dispatching.
                required_scope = self.METHOD_SCOPES.get(method)
                if required_scope is not None:
                    client_scopes = client_meta.get("scopes", [])
                    if required_scope not in client_scopes:
                        await self._send_rpc_error(
                            websocket,
                            -32001,
                            req_id,
                            message=f"Permission Denied: Missing scope {required_scope}",
                        )
                        continue

                try:
                    if method == "get_runtime_status":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._runtime_status()
                        }))

                    elif method == "list_models":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._list_models()
                        }))

                    elif method == "set_active_model":
                        filename = params.get("filename")
                        adapter = params.get("adapter")
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._set_active_model(filename, adapter)
                        }))

                    elif method == "list_prompt_pairs":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._list_prompt_pairs()
                        }))

                    elif method == "get_prompt_pair":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._get_prompt_pair(params.get("name", ""))
                        }))

                    elif method == "save_prompt_pair":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._save_prompt_pair(params)
                        }))

                    elif method == "delete_prompt_pair":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._delete_prompt_pair(params.get("name", ""))
                        }))

                    elif method == "list_kb_sources":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._kb_snapshot()
                        }))

                    elif method == "ingest_path":
                        path = params.get("path", "")
                        if not self._is_safe_path(path):
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32001,
                                    "message": f"Security Error: Ingesting a sensitive system path is blocked: {path}"
                                }
                            }))
                            continue
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._start_kb_ingest(params)
                        }))

                    elif method == "search_kb":
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": self._search_kb(params)
                        }))

                    elif method == "submit_task":
                        objective = params.get("objective")
                        workspace_path = params.get("workspace_path")
                        test_command = params.get("test_command", "python run_tests.py")

                        if not objective or not workspace_path:
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: objective and workspace_path are required."
                                }
                            }))
                            continue

                        if not self._is_safe_path(workspace_path):
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32001,
                                    "message": f"Security Error: Targeting a sensitive system path is blocked: {workspace_path}"
                                }
                            }))
                            continue

                        with self._threads_lock:
                            # If there is an active orchestrator, request stop and wait
                            if self.orchestrator and self.orchestrator.isRunning():
                                self.orchestrator.request_stop()
                                self.orchestrator.wait()

                            # Start orchestrator QThread
                            hyperparams = params.get("hyperparams", {})
                            self.orchestrator = SwarmOrchestratorThread(
                                workspace_path=workspace_path,
                                objective=objective,
                                test_command=test_command,
                                hyperparams=hyperparams
                            )

                            # Bind PyQt signals with DirectConnection to bypass thread event loop queues
                            self.orchestrator.status_update.connect(
                                lambda msg: self._send_notification("status_update", {"message": msg}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.orchestrator.task_plan_created.connect(
                                lambda plan: self._send_notification("task_plan_created", {"plan": plan}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.orchestrator.file_edited.connect(
                                lambda path, content: self._send_notification(
                                    "file_edited", {"filepath": path, "content": content}
                                ),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.orchestrator.test_result.connect(
                                lambda passed, trace: self._send_notification(
                                    "test_result", {"passed": passed, "error_trace": trace}
                                ),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.orchestrator.finished_swarm.connect(
                                lambda success, summary: self._send_notification(
                                    "finished_swarm", {"success": success, "summary": summary}
                                ),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.orchestrator.edits_proposed.connect(
                                lambda proposals: [
                                    self._send_notification("edits_proposed", {"proposals": proposals}),
                                    self.orchestrator.commit_selected_edits([p["filepath"] for p in proposals])
                                ],
                                Qt.ConnectionType.DirectConnection
                            )

                            self.orchestrator.start()
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"status": "started"}
                        }))

                    elif method == "submit_chat":
                        message = params.get("message")
                        workspace_path = params.get("workspace_path")
                        hyperparams = params.get("hyperparams", {})

                        if not message:
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: message is required."
                                }
                            }))
                            continue

                        with self._threads_lock:
                            # Stop orchestrator if running
                            if self.orchestrator and self.orchestrator.isRunning():
                                self.orchestrator.request_stop()
                                self.orchestrator.wait()

                            # Stop chat thread if running
                            if self.chat_thread and self.chat_thread.isRunning():
                                if hasattr(self.chat_thread, "request_stop"):
                                    self.chat_thread.request_stop()
                                self.chat_thread.wait()

                        # Get client history
                        history = self.client_histories.setdefault(websocket, [])
                        history.append({"role": "user", "content": message})

                        # Retrieve RAG chunks if enabled
                        retrieved_chunks = []
                        if hyperparams.get("rag_enabled", True):
                            try:
                                self.rag._load_index()
                                rag_top_k = int(hyperparams.get("rag_top_k", 3))
                                rag_threshold = float(hyperparams.get("rag_threshold", 0.0))
                                retrieved_chunks = self.rag.retrieve(
                                    query=message,
                                    top_k=rag_top_k,
                                    threshold=rag_threshold,
                                )
                            except Exception as re:
                                logger.warning(f"RAG retrieval error: {re}")

                        system_prompt = hyperparams.get("system_prompt")
                        if not system_prompt:
                            system_prompt = (
                                "You are Karl, a precise and thoughtful AI assistant. "
                                "Always respond in English. "
                                "Analyze and break down problems step-by-step. "
                                "Write down your detailed thoughts and calculations inside <think>...</think> blocks. "
                                "Double-check your derivations and arithmetic before writing the final answer."
                            )

                        # Resolve agent profile overrides (model / adapter / system prompt prefix)
                        agent_id = params.get("agent")
                        agent_model_name: str | None = None
                        agent_adapter_name: str | None = None
                        if agent_id:
                            from app.ui.workspaces.workbench.profiles import AGENT_PROFILES
                            profile = AGENT_PROFILES.get(agent_id, {})
                            agent_model_name = profile.get("base_model") or None
                            agent_adapter_name = profile.get("adapter") or None
                            # Prepend profile system-prompt prefix if present
                            profile_prompt = profile.get("prompt", "")
                            if profile_prompt and not system_prompt.startswith(profile_prompt):
                                system_prompt = profile_prompt + "\n" + system_prompt

                        _history_ref = history

                        def _on_chat_finished(
                            thought: str, response: str, diagnostics: dict
                        ) -> None:
                            self._record_generation_metrics(diagnostics)
                            if response:
                                _history_ref.append(
                                    {"role": "assistant", "content": response}
                                )
                            self._send_notification("chat_finished", {})

                        def _on_chat_error(err: str) -> None:
                            message_text = str(err)
                            self._send_notification(
                                "status_update",
                                {"message": message_text},
                            )
                            self._send_notification(
                                "chat_finished",
                                {"error": message_text},
                            )

                        try:
                            chat_thread = self._inference_service.run_generation(
                                prompt=message,
                                system_prompt=system_prompt,
                                chat_history=history,
                                hyperparams=hyperparams,
                                on_thought_token_cb=lambda token: self._send_notification(
                                    "chat_thought_token", {"token": token}
                                ),
                                on_token_cb=lambda token: self._send_notification(
                                    "chat_response_token", {"token": token}
                                ),
                                on_finished_cb=_on_chat_finished,
                                on_error_cb=_on_chat_error,
                                retrieved_chunks=retrieved_chunks,
                                model_name=agent_model_name,
                                adapter_name=agent_adapter_name,
                                connection_type=Qt.ConnectionType.DirectConnection,
                            )
                        except CircuitBreakerOpenException as exc:
                            await websocket.send(json.dumps(
                                self._rpc_error_response(
                                    -32603,
                                    req_id,
                                    message=str(exc),
                                )
                            ))
                            continue

                        with self._threads_lock:
                            self.chat_thread = chat_thread
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"status": "started"}
                        }))

                    elif method == "create_custom_agent":
                        # Validate params
                        name = params.get("name", "")
                        label = params.get("label", "")
                        prompt_text = params.get("prompt", "")
                        import re as _re
                        if not _re.match(r'^[a-z0-9_]+$', name):
                            await websocket.send(json.dumps(self._rpc_error_response(
                                -32602, req_id,
                                message=f"Invalid params: name '{name}' must be alphanumeric lowercase (a-z, 0-9, _)."
                            )))
                            continue
                        from app.ui.workspaces.workbench.profiles import (
                            AGENT_PROFILES, DEFAULT_PROFILES, reload_profiles
                        )
                        if name in DEFAULT_PROFILES:
                            await websocket.send(json.dumps(self._rpc_error_response(
                                -32602, req_id,
                                message=f"Invalid params: '{name}' is a default profile name and cannot be overridden."
                            )))
                            continue
                        if name in AGENT_PROFILES and name not in DEFAULT_PROFILES:
                            await websocket.send(json.dumps(self._rpc_error_response(
                                -32602, req_id,
                                message=f"Invalid params: custom agent '{name}' already exists."
                            )))
                            continue

                        # Validate optional model/adapter paths
                        base_model = params.get("base_model") or None
                        adapter = params.get("adapter") or None
                        if base_model:
                            model_path = os.path.join("data", "models", base_model)
                            if not os.path.isfile(model_path):
                                await websocket.send(json.dumps(self._rpc_error_response(
                                    -32602, req_id,
                                    message=f"Invalid params: model file not found: {model_path}"
                                )))
                                continue
                        if adapter:
                            adapter_path = os.path.join("data", "adapters", adapter)
                            if not os.path.isdir(adapter_path):
                                await websocket.send(json.dumps(self._rpc_error_response(
                                    -32602, req_id,
                                    message=f"Invalid params: adapter directory not found: {adapter_path}"
                                )))
                                continue

                        # Build and persist the new profile
                        new_profile: dict = {
                            "label": label or name,
                            "description": params.get("description", ""),
                            "prompt": prompt_text,
                        }
                        if base_model:
                            new_profile["base_model"] = base_model
                        if adapter:
                            new_profile["adapter"] = adapter
                        if "rag_enabled" in params:
                            new_profile["rag_enabled"] = bool(params["rag_enabled"])
                        if "rag_top_k" in params:
                            new_profile["rag_top_k"] = int(params["rag_top_k"])

                        # Load existing custom agents, add new entry, save
                        custom_agents_path = os.path.join("data", "custom_agents.json")
                        existing: dict = {}
                        if os.path.isfile(custom_agents_path):
                            try:
                                with open(custom_agents_path, "r", encoding="utf-8") as _f:
                                    existing = json.load(_f) or {}
                            except (json.JSONDecodeError, OSError):
                                existing = {}
                        existing[name] = new_profile
                        os.makedirs("data", exist_ok=True)
                        with open(custom_agents_path, "w", encoding="utf-8") as _f:
                            json.dump(existing, _f, indent=2)

                        reload_profiles()

                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0", "id": req_id,
                            "result": {"status": "success", "name": name}
                        }))
                        # Broadcast profile update to all connected clients
                        self._send_notification("agent_profiles_updated", {
                            "name": name, "profile": new_profile
                        })

                    elif method == "list_custom_agents":
                        from app.ui.workspaces.workbench.profiles import (
                            AGENT_PROFILES, DEFAULT_PROFILES
                        )
                        custom_only = {
                            k: v for k, v in AGENT_PROFILES.items()
                            if k not in DEFAULT_PROFILES
                        }
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0", "id": req_id,
                            "result": custom_only
                        }))

                    elif method == "list_codex_topics":
                        library_dir = "data/codex_library"
                        topics = []
                        if os.path.exists(library_dir):
                            topics = [os.path.splitext(f)[0] for f in sorted(os.listdir(library_dir)) if f.endswith((".html", ".md"))]
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"topics": topics}
                        }))

                    elif method == "get_codex_content":
                        topic = params.get("topic", "")
                        content = ""
                        if topic:
                            library_dir = "data/codex_library"
                            safe_name = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip()
                            filepath = os.path.join(library_dir, f"{safe_name}.html")
                            if os.path.exists(filepath):
                                try:
                                    with open(filepath, "r", encoding="utf-8") as f:
                                        content = f.read()
                                except Exception as e:
                                    content = f"Error reading topic content: {e}"
                            else:
                                content = f"Guide not found for: {topic}"
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"content": content}
                        }))

                    elif method == "compute_diff":
                        text_a = params.get("text_a", "")
                        text_b = params.get("text_b", "")
                        diff_html = generate_char_diff_html(text_a, text_b)
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"diff_html": diff_html}
                        }))

                    elif method == "start_auto_train":
                        topic = params.get("topic")
                        adapter_name = params.get("adapter_name")
                        count = params.get("count", 15)
                        epochs = params.get("epochs", 3)
                        lr = params.get("lr", 2e-4)

                        if not topic or not adapter_name:
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: topic and adapter_name are required."
                                }
                            }))
                            continue

                        import subprocess
                        import sys
                        
                        def run_auto_train():
                            cmd = [
                                sys.executable,
                                "auto_train.py",
                                "--topic", topic,
                                "--adapter_name", adapter_name,
                                "--count", str(count),
                                "--epochs", str(epochs),
                                "--lr", str(lr)
                            ]
                            try:
                                proc = subprocess.Popen(
                                    cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True,
                                    bufsize=1,
                                    universal_newlines=True
                                )
                                for line in proc.stdout:
                                    self._send_notification("auto_train_log", {
                                        "adapter_name": adapter_name,
                                        "message": line.strip()
                                    })
                                rc = proc.wait()
                                self._send_notification("auto_train_finished", {
                                    "adapter_name": adapter_name,
                                    "success": rc == 0,
                                    "message": f"Process exited with code {rc}"
                                })
                            except Exception as e:
                                self._send_notification("auto_train_finished", {
                                    "adapter_name": adapter_name,
                                    "success": False,
                                    "message": str(e)
                                })
                        
                        threading.Thread(target=run_auto_train, daemon=True).start()
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"status": "started"}
                        }))

                    elif method == "fit_vectorizer":
                        documents = params.get("documents", [])
                        if not documents:
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: documents list is required."
                                }
                            }))
                            continue
                        
                        from app.utils.custom_embeddings import TfidfEmbedder
                        tfidf = TfidfEmbedder()
                        tfidf.fit(documents)
                        
                        vectors = []
                        for doc in documents:
                            v = tfidf.transform(doc)
                            vectors.append(v.tolist())
                            
                        vocab_sorted = [word for word, idx in sorted(tfidf.vocabulary.items(), key=lambda item: item[1])]
                        
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "vocabulary": vocab_sorted,
                                "vectors": vectors
                            }
                        }))

                    elif method == "start_mini_train":
                        lr = float(params.get("lr", 0.001))
                        max_iters = int(params.get("max_iters", 100))
                        batch_size = int(params.get("batch_size", 16))
                        
                        shakespeare_path = "data/tiny_shakespeare.txt"
                        if os.path.exists(shakespeare_path):
                            with open(shakespeare_path, "r", encoding="utf-8") as f:
                                dataset_text = f.read()
                        else:
                            dataset_text = (
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
                            ) * 20
                            os.makedirs("data", exist_ok=True)
                            with open(shakespeare_path, "w", encoding="utf-8") as f:
                                f.write(dataset_text)

                        config = {
                            "batch_size": batch_size,
                            "block_size": 64,
                            "n_embd": 128,
                            "n_heads": 4,
                            "n_layers": 4,
                            "lr": lr,
                            "max_iters": max_iters,
                            "eval_interval": 20,
                            "sample_interval": 50
                        }

                        with self._threads_lock:
                            if hasattr(self, "mini_train_thread") and self.mini_train_thread and self.mini_train_thread.isRunning():
                                self.mini_train_thread.stop()
                                self.mini_train_thread.wait()
                            
                            from app.engine.mini_train_thread import MiniTrainThread
                            self.mini_train_thread = MiniTrainThread(
                                dataset_text=dataset_text,
                                config=config
                            )
                            
                            self.mini_train_thread.log.connect(
                                lambda msg: self._send_notification("status_update", {"message": msg}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.mini_train_thread.loss.connect(
                                lambda step, loss_val: self._send_notification("status_update", {"message": f"Step {step} | Loss: {loss_val:.4f}"}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.mini_train_thread.progress.connect(
                                lambda step, max_steps, sample_text: self._send_notification("status_update", {"message": f"--- Generation Output (Step {step} / {max_steps}) ---\n{sample_text}"}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.mini_train_thread.done.connect(
                                lambda save_dir: self._send_notification("status_update", {"message": f"Training completed. Saved to {save_dir}"}),
                                Qt.ConnectionType.DirectConnection
                            )
                            self.mini_train_thread.error.connect(
                                lambda err: self._send_notification("status_update", {"message": f"[Mini-GPT Error] {err}"}),
                                Qt.ConnectionType.DirectConnection
                            )
                            
                            self.mini_train_thread.start()
                            
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "status": "started",
                                "task_id": "mini-gpt-train"
                            }
                        }))

                    elif method == "stop_task":
                        with self._threads_lock:
                            status = "idle"
                            if self.orchestrator and self.orchestrator.isRunning():
                                self.orchestrator.request_stop()
                                status = "stopping"
                            elif self.chat_thread and self.chat_thread.isRunning():
                                if hasattr(self.chat_thread, "request_stop"):
                                    self.chat_thread.request_stop()
                                status = "stopping"
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"status": status}
                        }))

                    else:
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        }))

                except Exception as inner_e:
                    logger.exception("Error handling WebSocket RPC method %r", method)
                    await self._send_rpc_error(websocket, -32603, req_id, data=str(inner_e))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.client_metadata.pop(websocket, None)
            self.client_histories.pop(websocket, None)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    def get_client_info(self) -> list[dict]:
        """Return metadata for all connected clients. Thread-safe snapshot."""
        info = []
        for ws, meta in list(self.client_metadata.items()):
            latency = -1.0
            try:
                # websockets.connection.latency is in seconds
                latency = ws.latency * 1000.0 # ms
            except Exception:
                pass
            
            info.append({
                "id": meta.get("id"),
                "ip": meta.get("ip"),
                "latency_ms": latency,
                "connected_at": meta.get("connected_at")
            })
        return info

    def _send_notification(self, method: str, params: dict):
        """Dispatches notification thread-safely into the background event loop."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_notification(method, params), self.loop
            )

    def client_count(self) -> int:
        """Return the connected client count under the clients lock."""
        if not hasattr(self, "_clients_lock"):
            self._clients_lock = threading.Lock()
        with self._clients_lock:
            return len(self.clients)

    async def _broadcast_notification(self, method: str, params: dict):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })
        if self.clients:
            # Broadcast to all registered websocket connections
            if not hasattr(self, "_clients_lock"):
                self._clients_lock = threading.Lock()
            with self._clients_lock:
                clients = list(self.clients)
            results = await asyncio.gather(
                *[client.send(payload) for client in clients],
                return_exceptions=True,
            )
            failed = [
                client for client, result in zip(clients, results)
                if isinstance(result, Exception)
            ]
            if failed:
                with self._clients_lock:
                    for client in failed:
                        self.clients.discard(client)
                        self.client_metadata.pop(client, None)
                        self.client_histories.pop(client, None)
