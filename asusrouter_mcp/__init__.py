"""AsusRouter MCP Server package.

This package provides a Model Context Protocol (MCP) server for AsusRouter,
enabling AI assistants to interact with ASUS routers for device management,
parental controls, and network monitoring.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "AsusRouter Contributors"

# Import main server functions for convenience
from asusrouter_mcp.server import call_tool, list_resources, list_tools

__all__ = [
    "call_tool",
    "list_resources",
    "list_tools",
    "__version__",
    "__author__",
]
