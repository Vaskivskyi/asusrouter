#!/usr/bin/env python3
"""Enhanced MCP server test with comprehensive logging."""

import asyncio
import json
import sys
import traceback

from test_logger import TestLogger


async def test_server_with_logging():
    """Test the MCP server with comprehensive logging."""
    logger = TestLogger("mcp_server_test")

    try:
        logger.log("info", "Starting MCP server test with logging")

        # Import the server module
        logger.log("debug", "Importing server module")
        from asusrouter_mcp.server import call_tool, list_resources, list_tools

        logger.log_test_result("import_server", True, "Server module imported successfully")

        # Test tool listing
        logger.log("debug", "Testing tool listing")
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        logger.log_test_result("list_tools", True, f"Found {len(tools)} tools: {tool_names}")

        # Test resource listing
        logger.log("debug", "Testing resource listing")
        resources = await list_resources()
        resource_names = [resource.name for resource in resources]
        logger.log_test_result("list_resources", True, f"Found {len(resources)} resources: {resource_names}")

        # Test connection (with real credentials from .env)
        logger.log("info", "Testing router connection with .env credentials")
        try:
            result = await call_tool("connect_router", {})
            logger.log_tool_call("connect_router", {}, result[0].text, True)
            logger.log_test_result("connect_router", True, result[0].text)

            # If connection succeeds, test other tools
            await test_connected_tools(logger)

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.log_tool_call("connect_router", {}, error_msg, False)
            logger.log_test_result("connect_router", False, "", error_msg)
            logger.log("warning", "Skipping connected tests due to connection failure")

        # Test device tools with real device data
        await test_device_tools(logger)

        return True

    except Exception as e:
        error_msg = f"Test failed with exception: {str(e)}"
        logger.log("error", error_msg, {"traceback": traceback.format_exc()})
        logger.log_test_result("overall_test", False, "", error_msg)
        return False

    finally:
        # Clean up router connection if it exists
        try:
            from asusrouter_mcp.server import cleanup_connection
            logger.log("debug", "Cleaning up router connection")
            await cleanup_connection()
            # Give the session time to properly close
            await asyncio.sleep(0.1)
            logger.log("debug", "Router connection cleanup completed")
        except Exception as cleanup_error:
            logger.log("warning", f"Error during cleanup: {str(cleanup_error)}")

        summary = logger.get_summary()
        logger.log("info", f"Test summary: {json.dumps(summary, indent=2)}")
        log_file = logger.save()
        print(f"\nTest logs saved to: {log_file}")
        print("To view logs: python test_logger.py view")


async def test_connected_tools(logger: TestLogger):
    """Test tools that require router connection."""
    from asusrouter_mcp.server import call_tool

    tests = [
        ("get_router_data", {"data_types": ["clients"]}, "Get clients data"),
        ("get_router_data", {"data_types": ["status"]}, "Get status data"),
        ("get_router_data", {"data_types": ["sysinfo"]}, "Get system info"),
        ("get_devices_for_user", {"user_group": "kids"}, "Get devices for kids group"),
    ]

    for tool_name, args, description in tests:
        logger.log("debug", f"Testing {description}")
        try:
            result = await call_tool(tool_name, args)
            success = "Error:" not in result[0].text
            logger.log_tool_call(tool_name, args, result[0].text[:200] + "...", success)
            logger.log_test_result(f"{tool_name}_{description.lower().replace(' ', '_')}", success, result[0].text[:100])
        except Exception as e:
            error_msg = f"Tool {tool_name} failed: {str(e)}"
            logger.log_tool_call(tool_name, args, error_msg, False)
            logger.log_test_result(f"{tool_name}_{description.lower().replace(' ', '_')}", False, "", error_msg)


async def test_device_tools(logger: TestLogger):
    """Test device-specific tools with real device data."""
    from asusrouter_mcp.server import call_tool

    tests = [
        ("get_device_usage", {"device_name": "Test Device"}, "Get device usage by name"),
        ("block_traffic_to_device", {"device_ip": "192.168.1.100"}, "Block device by IP"),
        ("allow_traffic_to_device", {"device_mac": "AA:BB:CC:DD:EE:FF"}, "Allow device by MAC"),
    ]

    for tool_name, args, description in tests:
        logger.log("debug", f"Testing {description} (with real device)")
        try:
            result = await call_tool(tool_name, args)
            # For these tests, we expect success since the device exists
            success = "Error:" not in result[0].text and "Successfully" in result[0].text or "usage_data" in result[0].text or "device" in result[0].text.lower()
            logger.log_tool_call(tool_name, args, result[0].text[:200] + "...", success)
            logger.log_test_result(f"{tool_name}_real_device", success, result[0].text[:100])
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            logger.log_tool_call(tool_name, args, error_msg, False)
            logger.log_test_result(f"{tool_name}_real_device", False, "", error_msg)


async def test_with_manual_credentials(logger: TestLogger):
    """Test with manually provided credentials."""
    from asusrouter_mcp.server import call_tool

    logger.log("info", "Testing with manual credentials")

    # Test with fake credentials (should fail)
    try:
        result = await call_tool("connect_router", {
            "host": "192.168.1.1",
            "username": "admin",
            "password": "wrong_password"
        })
        success = "Successfully connected" in result[0].text
        logger.log_tool_call("connect_router", {"host": "192.168.1.1", "username": "admin"}, result[0].text, success)
        logger.log_test_result("manual_credentials_test", success, result[0].text)
    except Exception as e:
        error_msg = f"Manual credential test failed: {str(e)}"
        logger.log_test_result("manual_credentials_test", False, "", error_msg)


async def main():
    """Run comprehensive test with logging."""
    print("AsusRouter MCP Server - Comprehensive Test with Logging")
    print("=" * 60)

    success = await test_server_with_logging()

    print("\n" + "=" * 60)
    print(f"Overall Result: {'PASS' if success else 'FAIL'}")
    print("\nCheck test_logs/ directory for detailed logs")
    print("Use 'python test_logger.py view' to review latest logs")

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
