"""
WebSocket Server Manager — Karl Workbench
==========================================
Hosts a local WebSocket server to bridge communication between Karl's Multi-Agent Swarm
and editor extensions (such as VS Code/Code OSS).
"""

import json
import asyncio
import threading
import websockets
from typing import Set, Optional, Any
from PyQt6.QtCore import Qt
from app.engine.swarm_orchestrator import SwarmOrchestratorThread


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
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self.orchestrator: Optional[SwarmOrchestratorThread] = None
        self.server = None
        self.started_event = threading.Event()
        self._start_loop_thread()

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
                    if method == "submit_task":
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
                        self.orchestrator = SwarmOrchestratorThread(
                            workspace_path=workspace_path,
                            objective=objective,
                            test_command=test_command
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

                    elif method == "stop_task":
                        if self.orchestrator and self.orchestrator.isRunning():
                            self.orchestrator.request_stop()
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
