"""
MCP Client Manager — Karl Workbench
====================================
Manages the lifecycle of multiple stdio-based Model Context Protocol (MCP) servers
configured in data/mcp_config.json. Exposes synchronous and asynchronous methods
to list tools and invoke them from sync codebases (like QThreads).
"""

import logging
import os
import json
import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


logger = logging.getLogger("karl.mcp")

_SYNC_TIMEOUT_SECONDS = 8.0
_CONNECT_TIMEOUT_SECONDS = 5.0
_INITIALIZE_TIMEOUT_SECONDS = 5.0


class MCPClientManager:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, config_path: str = "data/mcp_config.json") -> "MCPClientManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config_path)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Forces recreation of the singleton on the next call."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.stop()
                cls._instance = None

    def __init__(self, config_path: str = "data/mcp_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        self._start_loop_thread()

    def _start_loop_thread(self):
        """Starts a background daemon thread running an asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    # ── Synchronous Entrypoints ───────────────────────────────────────────────

    def _await_future(self, future):
        try:
            return future.result(timeout=_SYNC_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            future.cancel()
            raise

    def start(self):
        """Synchronously starts all configured MCP servers."""
        if not self.loop:
            raise RuntimeError("Event loop not initialized.")
        future = asyncio.run_coroutine_threadsafe(self.async_start(), self.loop)
        return self._await_future(future)

    def stop(self):
        """Synchronously stops all running MCP servers and shuts down the loop."""
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.async_stop(), self.loop)
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.warning(f"Error waiting for servers to stop: {e}")
            
            # Stop the loop and join the thread
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.loop_thread:
                self.loop_thread.join(timeout=2.0)
        self.servers.clear()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Synchronously lists all tools across all connected servers."""
        if not self.loop:
            return []
        future = asyncio.run_coroutine_threadsafe(self.async_list_tools(), self.loop)
        return self._await_future(future)

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronously invokes a tool and returns the response dictionary."""
        if not self.loop:
            return {"is_error": True, "error": "Event loop not running."}
        future = asyncio.run_coroutine_threadsafe(
            self.async_call_tool(server_name, tool_name, arguments), self.loop
        )
        return self._await_future(future)

    # ── Asynchronous Implementation ───────────────────────────────────────────

    async def async_start(self):
        """Loads configuration and initiates server connections."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
            return

        servers_config = config.get("mcpServers", {})
        for name, cfg in servers_config.items():
            command = cfg.get("command")
            args = cfg.get("args", [])
            env = cfg.get("env")

            if not command:
                logger.warning(f"Server '{name}' configuration missing command.")
                continue

            try:
                await self.async_connect_server(name, command, args, env)
            except Exception as e:
                logger.warning(f"Failed to connect to server '{name}': {e}")

    async def async_connect_server(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Spawns stdio process for a server and performs MCP initialization."""
        if name in self.servers:
            return

        # Start the task context manager thread safely
        task = asyncio.create_task(self._run_server_lifecycle(name, command, args, env))
        
        try:
            await asyncio.wait_for(
                self._wait_for_server_registration(name, task),
                timeout=_CONNECT_TIMEOUT_SECONDS,
            )
        except Exception:
            task.cancel()
            raise

    async def _wait_for_server_registration(self, name: str, task: asyncio.Task):
        """Wait until a lifecycle task registers a server or exits."""
        while name not in self.servers:
            if task.done():
                exc = task.exception()
                if exc:
                    raise exc
                raise RuntimeError("Server lifecycle task exited before registering.")
            await asyncio.sleep(0.01)

    async def _run_server_lifecycle(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]]):
        """Runs the context manager lifetime loop inside a single dedicated task."""
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await asyncio.wait_for(
                        session.initialize(),
                        timeout=_INITIALIZE_TIMEOUT_SECONDS,
                    )
                    
                    # Set up stop signal and record server session
                    stop_event = asyncio.Event()
                    self.servers[name] = {
                        "session": session,
                        "command": command,
                        "args": args,
                        "stop_event": stop_event,
                    }
                    logger.info(f"Successfully connected to server: {name}")
                    
                    # Yield execution until stop is explicitly requested
                    await stop_event.wait()
        except Exception as e:
            logger.warning(f"Server '{name}' lifecycle terminated: {e}")
        finally:
            self.servers.pop(name, None)

    async def async_stop(self):
        """Tears down all active server connections by setting their stop event."""
        for name in list(self.servers.keys()):
            server = self.servers.get(name)
            if server and "stop_event" in server:
                server["stop_event"].set()

        # Wait up to 1 second for all sessions to cleanup and pop
        for _ in range(20):
            if not self.servers:
                break
            await asyncio.sleep(0.05)
        logger.info("All MCP servers stopped.")

    async def async_list_tools(self) -> List[Dict[str, Any]]:
        """Collects tools across all active servers."""
        all_tools = []
        for server_name, server in self.servers.items():
            session = server["session"]
            try:
                res = await session.list_tools()
                for tool in res.tools:
                    all_tools.append({
                        "server_name": server_name,
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema or {},
                    })
            except Exception as e:
                logger.warning(f"Error listing tools for server '{server_name}': {e}")
        return all_tools

    async def async_call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calls a tool asynchronously and returns a normalized response dict."""
        if server_name not in self.servers:
            return {"is_error": True, "error": f"Server '{server_name}' is not connected."}

        session = self.servers[server_name]["session"]
        try:
            res = await session.call_tool(tool_name, arguments)
            
            # Format content list
            formatted_content = []
            if hasattr(res, "content") and res.content:
                for content_block in res.content:
                    if hasattr(content_block, "text"):
                        formatted_content.append({"type": "text", "text": content_block.text})
                    else:
                        formatted_content.append({"type": "other", "data": str(content_block)})

            return {
                "is_error": getattr(res, "isError", False),
                "content": formatted_content,
                "structured_content": getattr(res, "structuredContent", None),
            }
        except Exception as e:
            return {"is_error": True, "error": f"Tool execution failed: {str(e)}"}
