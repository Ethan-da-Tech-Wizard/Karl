"""
Mock MCP Server for Testing — Karl Workbench
===========================================
A standard stdio-based MCP server using FastMCP. Registers basic tools for integration testing.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MockServer")


@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


@mcp.tool()
def get_version() -> str:
    """Get mock server version."""
    return "1.0.0"


if __name__ == "__main__":
    mcp.run()
