"""
WebSocket Bridge Tests — Karl Workbench
========================================
Integration tests verifying JSON-RPC task submission, signal-to-socket routing,
and connection teardown using a local mock client.
"""

import tests.qt_test_helper  # noqa: F401

import os
import sys
import json
import tempfile
import asyncio
import time
import unittest
from unittest.mock import patch, MagicMock

import websockets
from PyQt6.QtCore import QCoreApplication
from app.engine.websocket_server import WebSocketServerManager


def _running_under_bwrap() -> bool:
    try:
        with open("/proc/1/comm", "r", encoding="utf-8") as f:
            return f.read().strip() == "bwrap"
    except OSError:
        return False


class FakeBridgeRAG:
    def __init__(self):
        self.documents = []

    def _load_index(self):
        return None

    @property
    def total_chunks(self):
        return len(self.documents)

    def ingest_file(self, filepath, chunk_size=200, overlap=50):
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        self.documents.append({
            "text": text,
            "source_file": filename,
            "chunk_id": len(self.documents),
            "ingested_at": "2026-06-11T00:00:00Z",
        })
        return 1

    def retrieve(self, query, top_k=3, source_filter=None, threshold=0.0):
        results = self.retrieve_with_metadata(query, top_k=top_k, source_filter=source_filter)
        if threshold > 0:
            results = [r for r in results if r["distance"] <= threshold]
        return [r["text"] for r in results]

    def retrieve_with_metadata(self, query, top_k=3, source_filter=None):
        results = []
        for idx, doc in enumerate(self.documents):
            if source_filter and doc.get("source_file") != source_filter:
                continue
            distance = 0.05 if query.lower() in doc.get("text", "").lower() else 1.5
            results.append({
                **doc,
                "rank": idx,
                "distance": distance,
            })
        return results[:top_k]


class TestWebSocketBridge(unittest.TestCase):
    def setUp(self):
        if _running_under_bwrap():
            self.skipTest("Codex sandbox blocks reliable localhost WebSocket tests")

        # Initialize a PyQt application instance for QObject/QThread creation safety
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        # Start server on unique port (8081) to avoid local workspace collisions
        self.port = 8081
        self.manager = WebSocketServerManager.get_instance(port=self.port)
        self.manager.started_event.wait(timeout=5.0)

        # Set up a sandbox directory
        self.sandbox_dir = tempfile.TemporaryDirectory()
        self.workspace_path = self.sandbox_dir.name

        # Create a dummy python test runner script that succeeds instantly
        self.test_script_path = os.path.join(self.workspace_path, "run_tests.py")
        with open(self.test_script_path, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.dont_write_bytecode = True\nsys.exit(0)\n")

    def tearDown(self):
        self.sandbox_dir.cleanup()
        # Clean shutdown and reset the singleton
        WebSocketServerManager.reset_instance()

    def _get_uri(self):
        token = self.manager.bridge_token
        proto = "ws"
        if os.path.exists(self.manager._SSL_CERT_PATH):
            proto = "wss"
        return f"{proto}://localhost:{self.port}/?token={token}"

    def _get_ssl_context(self):
        import ssl
        if os.path.exists(self.manager._SSL_CERT_PATH):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        return None

    def test_runtime_status_rpc(self):
        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 30,
                    "method": "get_runtime_status"
                }
                await ws.send(json.dumps(payload))

                raw_resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                resp = json.loads(raw_resp)

                self.assertEqual(resp.get("id"), 30)
                self.assertIn("result", resp)
                result = resp["result"]
                self.assertEqual(result["bridge"]["port"], self.port)
                self.assertEqual(result["runtime"]["state"], "idle")
                self.assertIn("model", result)
                self.assertIn("adapter", result)
                self.assertIn("system", result)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()

    def test_model_registry_rpc(self):
        active_path = os.path.join("data", "active_model.json")
        model_dir = os.path.join("data", "models")
        model_name = "test-websocket-model.gguf"
        model_path = os.path.join(model_dir, model_name)
        previous_active = None
        if os.path.exists(active_path):
            with open(active_path, "r", encoding="utf-8") as f:
                previous_active = f.read()

        os.makedirs(model_dir, exist_ok=True)
        with open(model_path, "wb") as f:
            f.write(b"test")

        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 31,
                    "method": "list_models"
                }))
                list_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(list_resp.get("id"), 31)
                filenames = [m["filename"] for m in list_resp["result"]["models"]]
                self.assertIn(model_name, filenames)

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 32,
                    "method": "set_active_model",
                    "params": {"filename": model_name}
                }))
                set_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(set_resp.get("id"), 32)
                self.assertEqual(set_resp["result"]["active"]["filename"], model_name)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()
            if previous_active is None:
                try:
                    os.remove(active_path)
                except FileNotFoundError:
                    pass
            else:
                with open(active_path, "w", encoding="utf-8") as f:
                    f.write(previous_active)
            try:
                os.remove(model_path)
            except FileNotFoundError:
                pass

    def test_prompt_pair_rpc(self):
        pair_dir = os.path.join("data", "prompt_pairs")
        pair_name = "websocket_pair_test"
        pair_path = os.path.join(pair_dir, f"{pair_name}.json")
        os.makedirs(pair_dir, exist_ok=True)
        try:
            os.remove(pair_path)
        except FileNotFoundError:
            pass

        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "save_prompt_pair",
                    "params": {
                        "name": pair_name,
                        "system_a": "A system",
                        "user_a": "same input",
                        "system_b": "B system",
                        "user_b": "same input",
                        "output_a_raw": "alpha",
                        "output_b_raw": "beta"
                    }
                }))
                save_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(save_resp.get("id"), 42)
                self.assertTrue(save_resp["result"]["saved"])

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 40,
                    "method": "list_prompt_pairs"
                }))
                list_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                names = [p["name"] for p in list_resp["result"]["pairs"]]
                self.assertIn(pair_name, names)

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 41,
                    "method": "get_prompt_pair",
                    "params": {"name": pair_name}
                }))
                get_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(get_resp["result"]["system_a"], "A system")
                self.assertEqual(get_resp["result"]["system_b"], "B system")

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 43,
                    "method": "delete_prompt_pair",
                    "params": {"name": pair_name}
                }))
                delete_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertTrue(delete_resp["result"]["deleted"])

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()
            try:
                os.remove(pair_path)
            except FileNotFoundError:
                pass

    def test_knowledge_base_rpc(self):
        self.manager.rag = FakeBridgeRAG()
        doc_path = os.path.join(self.workspace_path, "notes.md")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Karl retrieves local project knowledge for prompt context.")

        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 50,
                    "method": "list_kb_sources"
                }))
                initial_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(initial_resp.get("id"), 50)
                self.assertEqual(initial_resp["result"]["total_chunks"], 0)

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 51,
                    "method": "ingest_path",
                    "params": {
                        "path": doc_path,
                        "chunk_size": 100,
                        "overlap": 10,
                    }
                }))
                ingest_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(ingest_resp.get("id"), 51)
                self.assertEqual(ingest_resp["result"]["status"], "started")
                self.assertEqual(ingest_resp["result"]["file_count"], 1)

                notifications = []
                finished = None
                for _ in range(10):
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                    method = msg.get("method")
                    if method:
                        notifications.append(method)
                    if method == "kb_ingest_finished":
                        finished = msg["params"]
                        break

                self.assertIn("kb_ingest_progress", notifications)
                self.assertIn("kb_ingest_finished", notifications)
                self.assertIsNotNone(finished)
                self.assertEqual(finished["chunks_added"], 1)
                self.assertEqual(finished["snapshot"]["total_chunks"], 1)

                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 52,
                    "method": "search_kb",
                    "params": {
                        "query": "project knowledge",
                        "top_k": 5,
                        "threshold": 0.2,
                    }
                }))
                search_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(search_resp.get("id"), 52)
                self.assertEqual(len(search_resp["result"]["results"]), 1)
                result = search_resp["result"]["results"][0]
                self.assertEqual(result["source_file"], "notes.md")
                self.assertLessEqual(result["distance"], 0.2)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_websocket_bridge_flow(self, mock_get_llm):
        # Mock LLM to return simple JSON plan and script contents
        def mock_llm(prompt, **kwargs):
            if "tasks" in prompt:
                plan = {
                    "explanation": "Create dummy python file",
                    "tasks": [
                        {
                            "filepath": "dummy.py",
                            "instructions": "Write print('hello')"
                        }
                    ]
                }
                return {"choices": [{"text": json.dumps(plan)}]}
            return {"choices": [{"text": "print('hello')\n"}]}

        mock_get_llm.return_value = MagicMock(side_effect=mock_llm)

        async def qt_event_loop_spinner():
            """Periodically processes Qt events to deliver cross-thread signals."""
            while True:
                QCoreApplication.processEvents()
                await asyncio.sleep(0.01)

        async def run_client():
            # Spawn the Qt event loop spinner task in the background
            spinner = asyncio.create_task(qt_event_loop_spinner())

            try:
                # Connect to Karl's WebSocket Server
                async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                    # 1. Submit the swarm task
                    task_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "submit_task",
                        "params": {
                            "objective": "Write a dummy python file",
                            "workspace_path": self.workspace_path,
                            "test_command": f"{sys.executable} run_tests.py"
                        }
                    }
                    await ws.send(json.dumps(task_payload))

                    # Check response with timeout
                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    resp = json.loads(raw_resp)

                    self.assertEqual(resp.get("id"), 1)
                    self.assertIn("result", resp)
                    self.assertEqual(resp["result"]["status"], "started")

                    # 2. Consume progress notifications until finished_swarm is received
                    notifications = []
                    for _ in range(50):  # Safety iteration ceiling
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=15.0)

                        msg = json.loads(raw_msg)
                        method = msg.get("method")
                        if method:
                            notifications.append(method)
                            if method == "finished_swarm":
                                break

                    # Validate expected notifications were broadcast
                    self.assertIn("task_plan_created", notifications)
                    self.assertIn("file_edited", notifications)
                    self.assertIn("finished_swarm", notifications)
            finally:
                # Clean shutdown of the spinner task
                spinner.cancel()
                try:
                    await spinner
                except asyncio.CancelledError:
                    pass

        # Run async client loop in main thread
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_websocket_chat_flow(self, mock_get_llm):
        def mock_llm_stream(prompt, **kwargs):
            if kwargs.get("stream"):
                if prompt.count("</think>") > 1:
                    return [
                        {"choices": [{"text": "Hello world", "finish_reason": "stop"}]}
                    ]
                return [
                    {"choices": [{"text": "<think>", "finish_reason": None}]},
                    {"choices": [{"text": "Thinking", "finish_reason": None}]},
                    {"choices": [{"text": "</think>", "finish_reason": None}]},
                    {"choices": [{"text": "Hello world", "finish_reason": "stop"}]}
                ]
            return {"choices": [{"text": "Response"}]}

        mock_llm_instance = MagicMock()
        mock_llm_instance.tokenize.return_value = [1, 2, 3]
        mock_llm_instance.side_effect = mock_llm_stream
        mock_get_llm.return_value = mock_llm_instance

        async def qt_event_loop_spinner():
            while True:
                QCoreApplication.processEvents()
                await asyncio.sleep(0.01)

        async def run_client():
            spinner = asyncio.create_task(qt_event_loop_spinner())
            try:
                async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                    chat_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "submit_chat",
                        "params": {
                            "message": "Hello Karl",
                            "workspace_path": self.workspace_path,
                            "hyperparams": {
                                "temperature": 0.7,
                                "top_p": 0.95,
                                "max_tokens": 100,
                                "rag_enabled": False,
                                "agentic_loop_enabled": False
                            }
                        }
                    }
                    await ws.send(json.dumps(chat_payload))

                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    resp = json.loads(raw_resp)
                    self.assertEqual(resp.get("id"), 1)
                    self.assertEqual(resp["result"]["status"], "started")

                    notifications = []
                    for _ in range(50):
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                        msg = json.loads(raw_msg)
                        method = msg.get("method")
                        if method:
                            notifications.append(method)
                            if method == "chat_finished":
                                break

                    self.assertIn("chat_thought_token", notifications)
                    self.assertIn("chat_response_token", notifications)
                    self.assertIn("chat_finished", notifications)
            finally:
                spinner.cancel()
                try:
                    await spinner
                except asyncio.CancelledError:
                    pass

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_client())
        finally:
            loop.close()

    def test_status_bar_reflection(self):
        from app.ui.widgets.status_bar import StatusBar

        # Instantiate StatusBar
        status_bar = StatusBar()

        # The WebSocketServerManager is currently listening on port 8081 (from setUp)
        status_bar._tick()
        self.assertEqual(status_bar._vscode_lbl.text(), "VS Code: listening")

        # Reset the server instance
        WebSocketServerManager.reset_instance()

        # Tick again - should show offline
        status_bar._tick()
        self.assertEqual(status_bar._vscode_lbl.text(), "VS Code: offline")

    def test_token_connection_success(self):
        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                payload = {"jsonrpc": "2.0", "id": 1, "method": "get_runtime_status"}
                await ws.send(json.dumps(payload))
                resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                self.assertIn("result", resp)

        asyncio.new_event_loop().run_until_complete(run_client())

    @patch("time.time")
    def test_token_expiry_fail(self, mock_time):
        # 1. Set current time to a fixed point
        now = 1700000000.0
        mock_time.return_value = now
        
        # 2. Force token initialization at this time
        self.manager._rotate_token()
        expired_token = self.manager.bridge_token
        
        # 3. Fast-forward time by 13 hours (46800 seconds)
        mock_time.return_value = now + 46800.0
        
        async def run_client():
            uri = f"ws://localhost:{self.port}/?token={expired_token}"
            if os.path.exists(self.manager._SSL_CERT_PATH):
                uri = uri.replace("ws://", "wss://")
            
            import websockets.exceptions
            try:
                # We expect the server to close the connection with 4001
                async with websockets.connect(uri, ssl=self._get_ssl_context(), close_timeout=2) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=2.0)
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidStatusCode) as e:
                # Some versions of websockets raise ConnectionClosedError, others InvalidStatusCode during handshake
                code = getattr(e, "code", getattr(e, "status_code", None))
                self.assertEqual(code, 4001)
                return
            except Exception as e:
                # If it's a generic ConnectionClosed, check the code
                if hasattr(e, "code") and e.code == 4001:
                    return
                raise e
            
            self.fail("Connection was not rejected with 4001")

        asyncio.new_event_loop().run_until_complete(run_client())

    @patch("time.time")
    def test_token_rotation_on_disk(self, mock_time):
        # 1. Start at a fixed time
        now = 1700000000.0
        mock_time.return_value = now
        self.manager._rotate_token()
        old_token = self.manager.bridge_token
        
        # 2. Expire the token
        mock_time.return_value = now + 50000.0
        
        # Attempting a connection with the old token should trigger rotation
        async def run_client():
            uri = f"ws://localhost:{self.port}/?token={old_token}"
            if os.path.exists(self.manager._SSL_CERT_PATH):
                uri = uri.replace("ws://", "wss://")
            try:
                import websockets.exceptions
                async with websockets.connect(uri, ssl=self._get_ssl_context(), close_timeout=2):
                    pass
            except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.ConnectionClosedError):
                pass
        
        asyncio.new_event_loop().run_until_complete(run_client())
            
        # 3. Verify token has changed on disk
        with open("data/bridge_token.json", "r") as f:
            data = json.load(f)
            self.assertNotEqual(data["token"], old_token)
            self.assertEqual(data["created_at"], now + 50000.0)

if __name__ == "__main__":
    unittest.main()
