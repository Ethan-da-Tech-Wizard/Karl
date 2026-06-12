"""
tool_executor.py — MCP tool call execution for LLMThread.
Provides build_tool_schema_prompt() and execute_tool_call() for the chat loop.
"""
from __future__ import annotations
import logging
import re
from typing import Any

logger = logging.getLogger("karl.tool_executor")


def build_tool_schema_prompt(tools: list[dict]) -> str:
    """Convert MCP tool list to a prompt-injectable XML schema block."""
    if not tools:
        return ""
    lines = ["<available_tools>"]
    for t in tools:
        schema = t.get("input_schema", {})
        props = schema.get("properties", {})
        param_strs = [
            f"    {k}: {v.get('description', v.get('type', 'any'))}"
            for k, v in props.items()
        ]
        lines.append(f"  <tool name='{t['name']}' server='{t['server_name']}'>")
        lines.append(f"    {t['description']}")
        if param_strs:
            lines.append("    Parameters:")
            lines.extend(param_strs)
        lines.append("  </tool>")
    lines.append("</available_tools>")
    lines.append(
        "\nTo call a tool: <tool_call server='SERVER' name='TOOL'>\n"
        "  param: value\n"
        "</tool_call>\n"
        "Tool results will be returned to you. Call done() when finished.\n"
        "<tool_call name='done'></tool_call>"
    )
    return "\n".join(lines)


def parse_tool_calls(text: str) -> list[dict]:
    """Extract all <tool_call> blocks from model output."""
    calls = []
    for m in re.finditer(r"<tool_call(?:\s+server='([^']*)')?(?:\s+name='([^']*)')>(.*?)</tool_call>", text, re.DOTALL):
        server = m.group(1) or ""
        name = m.group(2) or ""
        body = m.group(3).strip()
        args: dict[str, Any] = {}
        for line in body.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                args[k.strip()] = v.strip()
        calls.append({"server": server, "name": name, "args": args})
    return calls


def execute_tool_calls(calls: list[dict]) -> list[str]:
    """Execute a list of parsed tool calls via MCPClientManager. Returns result strings."""
    from app.engine.mcp_client import MCPClientManager
    results = []
    try:
        manager = MCPClientManager.get_instance()
    except Exception as e:
        return [f"<tool_result>ERROR: MCP manager unavailable: {e}</tool_result>"]

    for call in calls:
        if call["name"] == "done":
            results.append("<tool_result name='done'>OK</tool_result>")
            continue
        try:
            resp = manager.call_tool(call["server"], call["name"], call["args"])
            if resp.get("is_error"):
                text = resp.get("error", "Unknown error")
            else:
                content = resp.get("content", [])
                text = "\n".join(c.get("text", "") for c in content if "text" in c)
            results.append(f"<tool_result server='{call['server']}' name='{call['name']}'>\n{text}\n</tool_result>")
        except Exception as e:
            results.append(f"<tool_result name='{call['name']}'>ERROR: {e}</tool_result>")
    return results
