"""
Unit and Integration Tests for Custom Agent Profiles
===================================================
Verifies profile reloading, JSON-RPC validation, and correct model/adapter configuration.
"""

import tests.qt_test_helper  # noqa: F401
import os
import json
import asyncio
import unittest
import sys
from unittest.mock import patch, MagicMock

import websockets
import pytest
from PyQt6.QtCore import QCoreApplication

from app.engine.websocket_server import WebSocketServerManager
from app.ui.workspaces.workbench.profiles import AGENT_PROFILES, reload_profiles, DEFAULT_PROFILES
from app.engine.llm_thread import LLMThread


def _running_under_bwrap() -> bool:
    try:
        with open("/proc/1/comm", "r", encoding="utf-8") as f:
            return f.read().strip() == "bwrap"
    except OSError:
        return False


class TestCustomAgents(unittest.TestCase):
    def setUp(self):
        # Back up existing custom_agents.json
        self.custom_agents_path = os.path.join("data", "custom_agents.json")
        self.backup_content = None
        if os.path.exists(self.custom_agents_path):
            with open(self.custom_agents_path, "r", encoding="utf-8") as f:
                self.backup_content = f.read()

        # Reset AGENT_PROFILES to defaults
        reload_profiles()

        # Dummy assets required by create_custom_agent path validation
        self._dummy_model = os.path.join("data", "models", "coder-v1.gguf")
        self._dummy_adapter = os.path.join("data", "adapters", "lora-coder")
        os.makedirs(os.path.dirname(self._dummy_model), exist_ok=True)
        os.makedirs(self._dummy_adapter, exist_ok=True)
        self._dummy_model_existed = os.path.exists(self._dummy_model)
        if not self._dummy_model_existed:
            open(self._dummy_model, "wb").close()

        if _running_under_bwrap():
            return

        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.port = 8082
        self.manager = WebSocketServerManager.get_instance(port=self.port)
        self.manager.started_event.wait(timeout=5.0)

    def tearDown(self):
        # Remove dummy test assets if we created them
        if not self._dummy_model_existed and os.path.exists(self._dummy_model):
            os.remove(self._dummy_model)
        if os.path.isdir(self._dummy_adapter) and not os.listdir(self._dummy_adapter):
            os.rmdir(self._dummy_adapter)

        # Restore backup or remove custom_agents.json
        if os.path.exists(self.custom_agents_path):
            try:
                os.remove(self.custom_agents_path)
            except OSError:
                pass

        if self.backup_content is not None:
            os.makedirs("data", exist_ok=True)
            with open(self.custom_agents_path, "w", encoding="utf-8") as f:
                f.write(self.backup_content)

        reload_profiles()

        if not _running_under_bwrap():
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

    def test_profile_reloading(self):
        """Verifies custom profile loading and reloading logic."""
        # Ensure only default profiles exist initially
        self.assertEqual(list(AGENT_PROFILES.keys()), list(DEFAULT_PROFILES.keys()))

        # Write a mock custom agent config
        mock_custom = {
            "testagent": {
                "label": "Test Agent",
                "description": "Mock Custom Agent for Testing",
                "prompt": "Test Agent Prompt Integration",
                "base_model": "test-model.gguf",
                "adapter": "test-adapter",
                "rag_enabled": True,
                "rag_top_k": 5
            }
        }
        os.makedirs("data", exist_ok=True)
        with open(self.custom_agents_path, "w", encoding="utf-8") as f:
            json.dump(mock_custom, f)

        # Trigger reload
        reload_profiles()

        # Check merge
        self.assertIn("testagent", AGENT_PROFILES)
        self.assertEqual(AGENT_PROFILES["testagent"]["label"], "Test Agent")
        self.assertEqual(AGENT_PROFILES["testagent"]["description"], "Mock Custom Agent for Testing")
        self.assertEqual(AGENT_PROFILES["testagent"]["prompt"], "Test Agent Prompt Integration")
        self.assertEqual(AGENT_PROFILES["testagent"]["base_model"], "test-model.gguf")
        self.assertEqual(AGENT_PROFILES["testagent"]["adapter"], "test-adapter")
        self.assertTrue(AGENT_PROFILES["testagent"]["rag_enabled"])
        self.assertEqual(AGENT_PROFILES["testagent"]["rag_top_k"], 5)

        # Test cleanup reload back to defaults
        if os.path.exists(self.custom_agents_path):
            os.remove(self.custom_agents_path)
        reload_profiles()
        self.assertNotIn("testagent", AGENT_PROFILES)

    @pytest.mark.integration
    @pytest.mark.websocket
    def test_json_rpc_validation_and_listing(self):
        """Verifies validation rules and list/create RPC functionality."""
        if _running_under_bwrap():
            self.skipTest("Bwrap blocks localhost websocket testing")

        async def run_client():
            async with websockets.connect(self._get_uri(), ssl=self._get_ssl_context(), close_timeout=2) as ws:
                # 1. Test invalid name (non-alphanumeric)
                payload_invalid = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "create_custom_agent",
                    "params": {
                        "name": "invalid-name!",
                        "label": "Invalid Agent",
                        "prompt": "prompt"
                    }
                }
                await ws.send(json.dumps(payload_invalid))
                resp_invalid = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertIn("error", resp_invalid)
                self.assertEqual(resp_invalid["error"]["code"], -32602)
                self.assertIn("name", resp_invalid["error"]["message"])

                # 2. Test conflict with default profile
                payload_conflict_default = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "create_custom_agent",
                    "params": {
                        "name": "karl",
                        "label": "Fake Karl",
                        "prompt": "prompt"
                    }
                }
                await ws.send(json.dumps(payload_conflict_default))
                resp_conflict_default = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertIn("error", resp_conflict_default)
                self.assertEqual(resp_conflict_default["error"]["code"], -32602)
                self.assertIn("default", resp_conflict_default["error"]["message"])

                # 3. Test successful creation
                payload_success = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "create_custom_agent",
                    "params": {
                        "name": "supercoder",
                        "label": "Super Coder",
                        "description": "Advanced coding agent",
                        "prompt": "Always output optimized, readable code.",
                        "base_model": "coder-v1.gguf",
                        "adapter": "lora-coder",
                        "rag_enabled": True,
                        "rag_top_k": 4
                    }
                }
                await ws.send(json.dumps(payload_success))
                resp_success = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertIn("result", resp_success)
                self.assertEqual(resp_success["result"]["status"], "success")

                # Verify broadcast notification was received
                notify_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertEqual(notify_msg.get("method"), "agent_profiles_updated")
                self.assertEqual(notify_msg["params"]["name"], "supercoder")
                self.assertEqual(notify_msg["params"]["profile"]["label"], "Super Coder")

                # 4. Test conflict with existing custom profile
                await ws.send(json.dumps(payload_success))
                resp_conflict_custom = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertIn("error", resp_conflict_custom)
                self.assertEqual(resp_conflict_custom["error"]["code"], -32602)
                self.assertIn("already exists", resp_conflict_custom["error"]["message"])

                # 5. Test list_custom_agents
                await ws.send(json.dumps({
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "list_custom_agents"
                }))
                resp_list = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                self.assertIn("result", resp_list)
                self.assertIn("supercoder", resp_list["result"])
                self.assertEqual(resp_list["result"]["supercoder"]["base_model"], "coder-v1.gguf")

        asyncio.new_event_loop().run_until_complete(run_client())

    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_llm_thread_custom_model_and_adapter(self, mock_get_llm):
        """Verifies LLMThread loads the custom model and adapter specified in custom agent."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.tokenize.return_value = [1, 2, 3]
        mock_llm_instance.side_effect = lambda *args, **kwargs: [{"choices": [{"text": "Hello", "finish_reason": "stop"}]}]
        mock_get_llm.return_value = mock_llm_instance

        # Instantiate LLMThread with a custom model and adapter
        thread = LLMThread(
            system_prompt="Test System Prompt",
            chat_history=[],
            hyperparams={"temperature": 0.7},
            model_name="custom-model.gguf",
            adapter_name="custom-adapter"
        )
        
        # We call the generation loop synchronously (or run its target block)
        # to ensure it resolves model_path and calls ModelLoader.get_instance.
        with patch.object(thread, "generation_finished") as mock_finished:
            # Running the main execution path of LLMThread
            thread.run()
            
            # Verify ModelLoader.get_instance was called with the correct args
            expected_model_path = os.path.join("data", "models", "custom-model.gguf")
            mock_get_llm.assert_called_with(model_path=expected_model_path, adapter_name="custom-adapter")

    @pytest.mark.integration
    @pytest.mark.websocket
    @patch("app.engine.model_loader.ModelLoader.get_instance")
    def test_websocket_chat_custom_agent_routing(self, mock_get_llm):
        """Verifies websocket submit_chat routes custom agent model and adapter parameters to LLMThread."""
        if _running_under_bwrap():
            self.skipTest("Bwrap blocks localhost websocket testing")

        mock_llm_instance = MagicMock()
        mock_llm_instance.tokenize.return_value = [1, 2, 3]
        mock_llm_instance.side_effect = lambda *args, **kwargs: [
            {"choices": [{"text": "Hello world", "finish_reason": "stop"}]}
        ]
        mock_get_llm.return_value = mock_llm_instance

        # Write custom profile
        mock_custom = {
            "routingagent": {
                "label": "Routing Agent",
                "description": "Description",
                "prompt": "Custom system prompt addition",
                "base_model": "routing-model.gguf",
                "adapter": "routing-adapter",
                "rag_enabled": False,
                "rag_top_k": 3
            }
        }
        with open(self.custom_agents_path, "w", encoding="utf-8") as f:
            json.dump(mock_custom, f)
        reload_profiles()

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
                            "message": "Hello routing agent",
                            "agent": "routingagent",
                            "hyperparams": {
                                "temperature": 0.7,
                                "agentic_loop_enabled": False
                            }
                        }
                    }
                    await ws.send(json.dumps(chat_payload))
                    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                    self.assertEqual(resp["result"]["status"], "started")

                    # Wait for finished response or stream end
                    for _ in range(50):
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                        if msg.get("method") == "chat_finished":
                            break

                    # Verify ModelLoader was called with routing-model.gguf
                    expected_model_path = os.path.join("data", "models", "routing-model.gguf")
                    mock_get_llm.assert_called_with(model_path=expected_model_path, adapter_name="routing-adapter")
            finally:
                spinner.cancel()
                try:
                    await spinner
                except asyncio.CancelledError:
                    pass

        asyncio.new_event_loop().run_until_complete(run_client())


if __name__ == "__main__":
    unittest.main()
