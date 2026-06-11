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
import unittest
from unittest.mock import patch, MagicMock

import websockets
from PyQt6.QtCore import QCoreApplication
from app.engine.websocket_server import WebSocketServerManager


class TestWebSocketBridge(unittest.TestCase):
    def setUp(self):
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
                async with websockets.connect(f"ws://localhost:{self.port}", close_timeout=2) as ws:
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
                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    resp = json.loads(raw_resp)
                    
                    self.assertEqual(resp.get("id"), 1)
                    self.assertIn("result", resp)
                    self.assertEqual(resp["result"]["status"], "started")

                    # 2. Consume progress notifications until finished_swarm is received
                    notifications = []
                    for _ in range(50):  # Safety iteration ceiling
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
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

    def test_status_bar_reflection(self):
        from app.ui.widgets.status_bar import StatusBar
        
        # Instantiate StatusBar
        status_bar = StatusBar()
        
        # The WebSocketServerManager is currently listening on port 8081 (from setUp)
        status_bar._tick()
        self.assertEqual(status_bar._vscode_lbl.text(), "🔌 VS Code: listening")
        
        # Reset the server instance
        WebSocketServerManager.reset_instance()
        
        # Tick again - should show offline
        status_bar._tick()
        self.assertEqual(status_bar._vscode_lbl.text(), "🔌 VS Code: offline")


if __name__ == "__main__":
    unittest.main()
