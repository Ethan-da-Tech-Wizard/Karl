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
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import websockets
from typing import Set, Optional, Any
from PyQt6.QtCore import Qt

from app.engine import config_store
from app.engine.swarm_orchestrator import SwarmOrchestratorThread
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.engine.model_loader import ModelLoader
from app.utils.rag_pipeline import RAGPipeline
from app.ui.workspaces.docs_data import DEFAULT_LIBRARY
from app.ui.workspaces.prompt_lab import generate_char_diff_html
from app.utils.keychain_manager import save_cached_token


logger = logging.getLogger("karl.websocket")


class WebSocketServerManager:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, port: int = 8080) -> "WebSocketServerManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(port)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Forces recreation of the singleton on the next call."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.stop()
                cls._instance = None

    def __init__(self, port: int = 8080):
        self.port = port
        self.clients: Set[Any] = set()
        self.client_metadata = {} # client -> {id, ip, latency}
        self.client_histories = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self.orchestrator: Optional[SwarmOrchestratorThread] = None
        self.chat_thread = None
        self.mini_train_thread = None
        # Guards orchestrator/chat_thread hand-off: the asyncio handler
        # (loop thread) and stop() (Qt thread) both stop/replace them.
        self._threads_lock = threading.Lock()
        self.kb_ingest_thread: Optional[threading.Thread] = None
        self.rag = RAGPipeline()
        self._seed_codex()
        self._init_security()
        self._ensure_ssl_certs()
        self.server = None
        self.started_event = threading.Event()
        self._start_loop_thread()

    _TOKEN_LIFETIME = 43_200  # 12 hours in seconds
    _TOKEN_PATH = "data/bridge_token.json"
    _SSL_CERT_PATH = "data/ssl/localhost.crt"
    _SSL_KEY_PATH = "data/ssl/localhost.key"

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
        """Initializes security token (JSON with timestamp) and safe path rules."""
        self.bridge_token: str = ""
        self._token_created_at: float = 0.0

        if os.path.exists(self._TOKEN_PATH):
            try:
                with open(self._TOKEN_PATH, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                self.bridge_token = payload["token"]
                self._token_created_at = float(payload["created_at"])
                # Rotate immediately if the stored token has already expired
                if time.time() - self._token_created_at > self._TOKEN_LIFETIME:
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
        """Generates a fresh token, persists it to data/bridge_token.json."""
        self.bridge_token = self._generate_token()
        self._token_created_at = time.time()
        try:
            os.makedirs("data", exist_ok=True)
            with open(self._TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump({"token": self.bridge_token, "created_at": self._token_created_at}, f)
            save_cached_token(self.bridge_token)
        except Exception as e:
            logger.warning(f"Could not save bridge token: {e}")

    def _validate_token(self, token: str) -> bool:
        """Returns True if token matches and has not exceeded the 12-hour lifetime.
        Silently rotates an expired token so the next connection uses the new one.
        """
        if not token:
            return False
        
        # Check expiry first
        if time.time() - self._token_created_at > self._TOKEN_LIFETIME:
            logger.info("Bridge token expired (12h). Rotating.")
            self._rotate_token()
            return False  # Force the client to re-read the new token file
            
        if not self.bridge_token:
            return False
            
        return token == self.bridge_token

    def _is_safe_path(self, path: str) -> bool:
        """Checks if a path is outside sensitive system directories."""
        if not path:
            return False
        abs_path = os.path.abspath(os.path.expanduser(path))
        
        # Check against blocked paths
        for blocked in self.blocked_paths:
            if abs_path == blocked or abs_path.startswith(blocked + os.sep):
                # Allow the project directory itself even if it's in a subfolder of home
                project_root = os.getcwd()
                if abs_path.startswith(project_root):
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
            total_chunks = 0
            per_file = []
            errors = []
            total = len(files)
            for index, filepath in enumerate(files, 1):
                filename = os.path.basename(filepath)
                self._send_notification("kb_ingest_progress", {
                    "task_id": task_id,
                    "current": index,
                    "total": total,
                    "filename": filename,
                    "status": "ingesting",
                })
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

            self._send_notification("kb_ingest_finished", {
                "task_id": task_id,
                "files": per_file,
                "errors": errors,
                "file_count": len(per_file),
                "error_count": len(errors),
                "chunks_added": total_chunks,
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

    def _start_loop_thread(self):
        """Starts a background daemon thread running an asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        # Start server inside loop
        self.loop.run_until_complete(self._start_server())
        self.loop.run_forever()

    async def _start_server(self):
        try:
            ssl_context = None
            if os.path.exists(self._SSL_CERT_PATH) and os.path.exists(self._SSL_KEY_PATH):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self._SSL_CERT_PATH, self._SSL_KEY_PATH)
                logger.info("WSS Secure WebSockets enabled.")
            else:
                logger.error("WSS SSL certificates missing. Server will NOT start without WSS.")
                raise RuntimeError("SSL context required for WSS enforcement.")

            self.server = await websockets.serve(
                self._handler, "localhost", self.port, ssl=ssl_context
            )
            logger.info(f"Server running on wss://localhost:{self.port}")
        except Exception as e:
            logger.warning(f"Failed to start server: {e}")
        finally:
            self.started_event.set()

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
            except Exception as e:
                logger.warning(f"Error closing server connection: {e}")

            # Stop the loop and join thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.loop_thread:
                self.loop_thread.join(timeout=2.0)
        self.clients.clear()

    async def _stop_server(self):
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
        
        if not self._validate_token(url_token):
            remote = getattr(websocket, "remote_address", "unknown")
            logger.warning("Rejected connection from %s: invalid or expired token (path: %s)", remote, raw_path)
            # Close with 4001 Unauthorized
            await websocket.close(4001, "Unauthorized: invalid or expired token")
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
            "authenticated": True  # Token was validated at handshake
        }
        self.client_histories[websocket] = []
        logger.info(f"Client connected: {websocket.remote_address} (ID: {client_id})")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
                    continue

                method = data.get("method")
                params = data.get("params", {})
                req_id = data.get("id")
                token = params.get("token")

                # Authentication check
                client_meta = self.client_metadata.get(websocket, {})
                authenticated = client_meta.get("authenticated", False)

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

                # Block sensitive methods if not authenticated
                sensitive_methods = {
                    "submit_task", "submit_chat", "ingest_path", 
                    "set_active_model", "start_auto_train", "save_prompt_pair",
                    "delete_prompt_pair"
                }
                
                if method in sensitive_methods and not authenticated:
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32000, 
                            "message": "Authentication required. Call 'authenticate' with the token found in 'data/bridge_token.json'."
                        }
                    }))
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

                        agentic = hyperparams.get("agentic_loop_enabled", False)
                        if agentic:
                            chat_thread = AgenticThread(
                                system_prompt=system_prompt,
                                initial_history=history,
                                hyperparams=hyperparams,
                                retrieved_chunks=retrieved_chunks
                            )
                        else:
                            chat_thread = LLMThread(
                                system_prompt=system_prompt,
                                chat_history=history,
                                hyperparams=hyperparams,
                                retrieved_chunks=retrieved_chunks
                            )

                        # Wire signals to broadcast methods (DirectConnection)
                        chat_thread.new_thought_token.connect(
                            lambda token: self._send_notification("chat_thought_token", {"token": token}),
                            Qt.ConnectionType.DirectConnection
                        )
                        chat_thread.new_chat_token.connect(
                            lambda token: self._send_notification("chat_response_token", {"token": token}),
                            Qt.ConnectionType.DirectConnection
                        )

                        def make_on_finished(ws, hist, is_agentic, thread_ref):
                            def on_finished(*args):
                                response_text = ""
                                if not is_agentic and len(args) >= 2:
                                    response_text = args[1]
                                elif is_agentic and thread_ref is not None:
                                    th = getattr(thread_ref, "chat_history", [])
                                    if th and th[-1].get("role") == "assistant":
                                        response_text = th[-1].get("content", "")

                                if response_text:
                                    hist.append({"role": "assistant", "content": response_text})

                                self._send_notification("chat_finished", {})
                            return on_finished

                        if agentic:
                            chat_thread.loop_finished.connect(
                                make_on_finished(websocket, history, True, chat_thread),
                                Qt.ConnectionType.DirectConnection
                            )
                        else:
                            chat_thread.generation_finished.connect(
                                make_on_finished(websocket, history, False, chat_thread),
                                Qt.ConnectionType.DirectConnection
                            )

                        chat_thread.error_occurred.connect(
                            lambda err: self._send_notification("status_update", {"message": f"[Error] {err}"}),
                            Qt.ConnectionType.DirectConnection
                        )

                        with self._threads_lock:
                            self.chat_thread = chat_thread
                            self.chat_thread.start()
                        await websocket.send(json.dumps({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"status": "started"}
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
                    logger.warning(f"Error handling method '{method}': {inner_e}")
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal swarm error: {inner_e}"
                        }
                    }))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.client_metadata.pop(websocket, None)
            self.client_histories.pop(websocket, None)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    def get_client_info(self) -> list[dict]:
        """Returns metadata for all connected clients. Thread-safe."""
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

    async def _broadcast_notification(self, method: str, params: dict):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })
        if self.clients:
            # Broadcast to all registered websocket connections
            await asyncio.gather(
                *[client.send(payload) for client in self.clients],
                return_exceptions=True
            )
