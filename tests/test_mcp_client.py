"""
MCP Client Manager Tests — Karl Workbench
==========================================
Integration tests verifying the lifecycle, tool listing, and execution routines
using a local, stdio-based mock Python MCP server.
"""

import tests.qt_test_helper  # noqa: F401

import os
import json
import tempfile
import sys
import unittest
import pytest

from app.engine.mcp_client import MCPClientManager


def _running_under_bwrap() -> bool:
    try:
        with open("/proc/1/comm", "r", encoding="utf-8") as f:
            return f.read().strip() == "bwrap"
    except OSError:
        return False


class TestMCPClient(unittest.TestCase):
    def setUp(self):
        # Create a temporary config file pointing to mock_mcp_server.py
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "mcp_config.json")
        
        # Determine current python interpreter and absolute mock server path
        python_exe = sys.executable
        mock_server_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "mock_mcp_server.py")
        )
        
        config_data = {
            "mcpServers": {
                "mock_server": {
                    "command": python_exe,
                    "args": [mock_server_path]
                }
            }
        }
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

    def tearDown(self):
        # Clean up temporary files
        self.temp_dir.cleanup()
        # Ensure any active client manager instance is stopped and cleared
        MCPClientManager.reset_instance()

    def test_mcp_client_lifecycle_and_tools(self):
        if _running_under_bwrap():
            pytest.skip("Codex sandbox blocks the mock MCP stdio handshake")

        # Retrieve singleton instance configured with temp config
        manager = MCPClientManager.get_instance(self.config_path)
        
        # 1. Start all configured servers
        manager.start()
        self.assertIn("mock_server", manager.servers)
        
        # 2. List tools across all servers
        tools = manager.list_tools()
        self.assertEqual(len(tools), 2)
        
        tool_names = [t["name"] for t in tools]
        self.assertIn("hello", tool_names)
        self.assertIn("get_version", tool_names)
        
        # 3. Call tool 'hello' with parameters
        res = manager.call_tool("mock_server", "hello", {"name": "TestUser"})
        self.assertFalse(res["is_error"])
        self.assertTrue(len(res["content"]) > 0)
        self.assertEqual(res["content"][0]["text"], "Hello, TestUser!")
        
        # 4. Call tool 'get_version' (no params)
        res = manager.call_tool("mock_server", "get_version", {})
        self.assertFalse(res["is_error"])
        self.assertTrue(len(res["content"]) > 0)
        self.assertEqual(res["content"][0]["text"], "1.0.0")
        
        # 5. Clean shutdown
        manager.stop()
        self.assertEqual(len(manager.servers), 0)


if __name__ == "__main__":
    unittest.main()
