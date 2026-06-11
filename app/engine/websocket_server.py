"""
WebSocket Server Manager — Karl Workbench
==========================================
Hosts a local WebSocket server to bridge communication between Karl's Multi-Agent Swarm
and editor extensions (such as VS Code/Code OSS).
"""

import os
import json
import asyncio
import threading
import re
import websockets
from typing import Set, Optional, Any
from PyQt6.QtCore import Qt
from app.engine.swarm_orchestrator import SwarmOrchestratorThread
from app.engine.llm_thread import LLMThread
from app.engine.agentic_thread import AgenticThread
from app.engine.model_loader import ModelLoader
from app.utils.rag_pipeline import RAGPipeline
from app.ui.workspaces.docs_data import DEFAULT_LIBRARY
from app.ui.workspaces.prompt_lab import generate_char_diff_html


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
        self.client_histories = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self.orchestrator: Optional[SwarmOrchestratorThread] = None
        self.chat_thread = None
        self.rag = RAGPipeline()
        self._seed_codex()
        self.server = None
        self.started_event = threading.Event()
        self._start_loop_thread()

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
            except Exception:
                pass

        if needs_upgrade or not [f for f in os.listdir(library_dir) if f.endswith((".html", ".md"))]:
            for topic, content in DEFAULT_LIBRARY.items():
                safe_name = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip()
                filepath = os.path.join(library_dir, f"{safe_name}.html")
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception:
                    pass
            try:
                with open(version_filepath, "w", encoding="utf-8") as vf:
                    vf.write(current_version)
            except Exception:
                pass

    def _active_model_config(self) -> dict:
        filename = "deepseek-r1-1.5b.gguf"
        adapter = None
        active_path = os.path.join("data", "active_model.json")
        if os.path.exists(active_path):
            try:
                with open(active_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                filename = data.get("filename") or data.get("model") or filename
                adapter = data.get("adapter")
            except Exception:
                pass
        return {"filename": filename, "adapter": adapter}

    def _read_model_registry(self) -> list[dict]:
        registry_path = os.path.join("data", "model_registry.json")
        if not os.path.exists(registry_path):
            return []
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

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
                except Exception:
                    pass
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
                    except Exception:
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
            except Exception:
                pass

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

        os.makedirs("data", exist_ok=True)
        with open(os.path.join("data", "active_model.json"), "w", encoding="utf-8") as f:
            json.dump(active, f)

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
            except Exception:
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
            self.server = await websockets.serve(self._handler, "localhost", self.port)
            print(f"[WebSocket] Server running on ws://localhost:{self.port}")
        except Exception as e:
            print(f"[WebSocket] Failed to start server: {e}")
        finally:
            self.started_event.set()

    def stop(self):
        """Synchronously shuts down the server and joins the background thread."""
        if self.loop and self.loop.is_running():
            # Stop the orchestrator if running
            if self.orchestrator and self.orchestrator.isRunning():
                self.orchestrator.request_stop()
                self.orchestrator.wait()

            # Stop chat thread if running
            if self.chat_thread and self.chat_thread.isRunning():
                if hasattr(self.chat_thread, "request_stop"):
                    self.chat_thread.request_stop()
                self.chat_thread.wait()

            # Stop websockets server
            future = asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)
            try:
                future.result(timeout=5.0)
            except Exception as e:
                print(f"[WebSocket] Error closing server connection: {e}")

            # Stop the loop and join thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.loop_thread:
                self.loop_thread.join(timeout=2.0)
        self.clients.clear()

    async def _stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[WebSocket] Server stopped.")

    async def _handler(self, websocket, path=None):
        self.clients.add(websocket)
        self.client_histories[websocket] = []
        print(f"[WebSocket] Client connected: {websocket.remote_address}")
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
                                retrieved_chunks = self.rag.retrieve(query=message, top_k=3)
                            except Exception as re:
                                print(f"[WebSocket] RAG retrieval error: {re}")

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
                            self.chat_thread = AgenticThread(
                                system_prompt=system_prompt,
                                initial_history=history,
                                hyperparams=hyperparams,
                                retrieved_chunks=retrieved_chunks
                            )
                        else:
                            self.chat_thread = LLMThread(
                                system_prompt=system_prompt,
                                chat_history=history,
                                hyperparams=hyperparams,
                                retrieved_chunks=retrieved_chunks
                            )

                        # Wire signals to broadcast methods (DirectConnection)
                        self.chat_thread.new_thought_token.connect(
                            lambda token: self._send_notification("chat_thought_token", {"token": token}),
                            Qt.ConnectionType.DirectConnection
                        )
                        self.chat_thread.new_chat_token.connect(
                            lambda token: self._send_notification("chat_response_token", {"token": token}),
                            Qt.ConnectionType.DirectConnection
                        )

                        def make_on_finished(ws, hist, is_agentic):
                            def on_finished(*args):
                                response_text = ""
                                if not is_agentic and len(args) >= 2:
                                    response_text = args[1]
                                elif is_agentic and self.chat_thread:
                                    th = getattr(self.chat_thread, "chat_history", [])
                                    if th and th[-1].get("role") == "assistant":
                                        response_text = th[-1].get("content", "")

                                if response_text:
                                    hist.append({"role": "assistant", "content": response_text})

                                self._send_notification("chat_finished", {})
                            return on_finished

                        if agentic:
                            self.chat_thread.loop_finished.connect(
                                make_on_finished(websocket, history, True),
                                Qt.ConnectionType.DirectConnection
                            )
                        else:
                            self.chat_thread.generation_finished.connect(
                                make_on_finished(websocket, history, False),
                                Qt.ConnectionType.DirectConnection
                            )

                        self.chat_thread.error_occurred.connect(
                            lambda err: self._send_notification("status_update", {"message": f"[Error] {err}"}),
                            Qt.ConnectionType.DirectConnection
                        )

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

                    elif method == "stop_task":
                        if self.orchestrator and self.orchestrator.isRunning():
                            self.orchestrator.request_stop()
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {"status": "stopping"}
                            }))
                        elif self.chat_thread and self.chat_thread.isRunning():
                            if hasattr(self.chat_thread, "request_stop"):
                                self.chat_thread.request_stop()
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {"status": "stopping"}
                            }))
                        else:
                            await websocket.send(json.dumps({
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {"status": "idle"}
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
                    print(f"[WebSocket] Error handling method '{method}': {inner_e}")
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
            self.client_histories.pop(websocket, None)
            print(f"[WebSocket] Client disconnected: {websocket.remote_address}")

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
