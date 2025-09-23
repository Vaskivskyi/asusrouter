#!/usr/bin/env python3
"""Interactive MCP server testing."""

import asyncio


async def interactive_test():
    """Interactive testing of MCP tools."""
    print("AsusRouter MCP Interactive Test")
    print("=" * 35)

    try:
        from asusrouter_mcp.server import call_tool, list_tools

        # Show available tools
        tools = await list_tools()
        print("Available tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.name} - {tool.description}")

        print("\nExample usage:")
        print("1. Connect: await call_tool('connect_router', {'host': '192.168.1.1', 'username': 'admin', 'password': 'pass'})")
        print("2. Get data: await call_tool('get_router_data', {'data_types': ['clients', 'status']})")
        print("3. Block device: await call_tool('block_traffic_to_device', {'device_ip': '192.168.1.100'})")
        print("4. Allow device: await call_tool('allow_traffic_to_device', {'device_name': 'iPhone'})")

        # Example tool call (will fail without router connection)
        print("\nTesting example call (will fail without router):")
        result = await call_tool("get_router_data", {"data_types": ["clients"]})
        print(f"Result: {result[0].text}")

    except Exception as e:
        print(f"Error: {e}")

    print("\nTo use interactively:")
    print("1. Start Python REPL: uv run python")
    print("2. Import: from asusrouter_mcp.server import call_tool")
    print("3. Use: await call_tool('tool_name', {'param': 'value'})")


if __name__ == "__main__":
    asyncio.run(interactive_test())
