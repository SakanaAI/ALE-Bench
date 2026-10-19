"""ALE-Bench MCP server, enabled by the ``mcp`` installation extra."""

import importlib

try:
    importlib.import_module("mcp.server.mcpserver")
except ImportError as exc:
    msg = "Missing dependencies. Please install the `mcp` extra requirements: pip install 'ale-bench[mcp]'"
    raise ImportError(msg) from exc
