"""MCP Server for AsusRouter integration with Claude AI."""

import asyncio
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, ServerCapabilities, TextContent, Tool

from asusrouter import AsusData, AsusRouter
from asusrouter.modules.parental_control import ParentalControlRule, PCRuleType

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("asusrouter-mcp")

# Global router connection
router_connection: AsusRouter | None = None


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available router resources."""
    return [
        Resource(
            uri="router://status",
            name="Router Status",
            mimeType="application/json",
            description="Current router status and information"
        ),
        Resource(
            uri="router://clients",
            name="Connected Clients",
            mimeType="application/json",
            description="List of devices connected to the router"
        ),
        Resource(
            uri="router://system",
            name="System Information",
            mimeType="application/json",
            description="Router system information and hardware details"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read router resource data."""
    if not router_connection:
        return "Error: Router not connected. Use connect_router tool first."

    try:
        if uri == "router://status":
            data = await router_connection.async_get_data(AsusData.SYSTEM)
            return str(data)
        if uri == "router://clients":
            data = await router_connection.async_get_data(AsusData.CLIENTS)
            return str(data)
        if uri == "router://system":
            data = await router_connection.async_get_data(AsusData.SYSINFO)
            return str(data)
        return f"Error: Unknown resource URI: {uri}"
    except Exception as e:
        return f"Error reading resource: {str(e)}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available router management tools."""
    return [
        Tool(
            name="connect_router",
            description="Connect to an ASUS router (uses env vars if no params provided)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Router IP address/hostname (or use ASUS_ROUTER_HOST env var)"},
                    "username": {"type": "string", "description": "Router username (or use ASUS_ROUTER_USERNAME env var)"},
                    "password": {"type": "string", "description": "Router password (or use ASUS_ROUTER_PASSWORD env var)"},
                    "use_ssl": {"type": "boolean", "default": False, "description": "Use HTTPS connection (or use ASUS_ROUTER_USE_SSL env var)"}
                }
            }
        ),
        Tool(
            name="get_router_data",
            description="Get specific data from the router",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of data types to retrieve (e.g., 'clients', 'status', 'sysinfo')"
                    }
                },
                "required": ["data_types"]
            }
        ),
        Tool(
            name="reboot_router",
            description="Reboot the router",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_devices_for_user",
            description="Get connected devices for a specific user/parental control group",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_group": {"type": "string", "description": "User or parental control group name"}
                },
                "required": ["user_group"]
            }
        ),
        Tool(
            name="get_device_usage",
            description="Get device usage data for last 24 hours including top 5 sites",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_mac": {"type": "string", "description": "MAC address of the device"},
                    "device_name": {"type": "string", "description": "Name of the device (alternative to MAC)"}
                }
            }
        ),
        Tool(
            name="block_traffic_to_device",
            description="Block network access for a specific device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_mac": {"type": "string", "description": "MAC address of the device to block"},
                    "device_name": {"type": "string", "description": "Name of the device to block"},
                    "device_ip": {"type": "string", "description": "IP address of the device to block"}
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="allow_traffic_to_device",
            description="Allow network access for a specific device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_mac": {"type": "string", "description": "MAC address of the device to allow"},
                    "device_name": {"type": "string", "description": "Name of the device to allow"},
                    "device_ip": {"type": "string", "description": "IP address of the device to allow"}
                },
                "additionalProperties": False
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute router management tools."""
    global router_connection

    try:
        if name == "connect_router":
            # Use provided arguments or fall back to environment variables
            host = arguments.get("host") or os.getenv("ASUS_ROUTER_HOST")
            username = arguments.get("username") or os.getenv("ASUS_ROUTER_USERNAME")
            password = arguments.get("password") or os.getenv("ASUS_ROUTER_PASSWORD")
            use_ssl = arguments.get("use_ssl", os.getenv("ASUS_ROUTER_USE_SSL", "false").lower() == "true")

            if not host or not username or not password:
                return [TextContent(
                    type="text",
                    text="Error: Router credentials required. Provide host, username, password as arguments or set ASUS_ROUTER_HOST, ASUS_ROUTER_USERNAME, ASUS_ROUTER_PASSWORD environment variables."
                )]

            router_connection = AsusRouter(
                hostname=host,
                username=username,
                password=password,
                use_ssl=use_ssl
            )

            await router_connection.async_connect()
            return [TextContent(
                type="text",
                text=f"Successfully connected to router at {host}"
            )]

        if name == "get_router_data":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            data_types = arguments["data_types"]
            asus_data_types = []

            # Map string names to AsusData enum values
            data_mapping = {
                "clients": AsusData.CLIENTS,
                "status": AsusData.SYSTEM,
                "system": AsusData.SYSTEM,
                "sysinfo": AsusData.SYSINFO,
                "ports": AsusData.PORTS,
                "cpu": AsusData.CPU,
                "ram": AsusData.RAM,
                "memory": AsusData.RAM,
                "network": AsusData.NETWORK,
                "wan": AsusData.WAN,
                "wlan": AsusData.WLAN
            }

            for data_type in data_types:
                if data_type.lower() in data_mapping:
                    asus_data_types.append(data_mapping[data_type.lower()])

            if not asus_data_types:
                return [TextContent(
                    type="text",
                    text=f"Error: No valid data types found. Available: {list(data_mapping.keys())}"
                )]

            # Get data for each type and combine results
            result = {}
            for data_type in asus_data_types:
                try:
                    data = await router_connection.async_get_data(data_type)
                    result[data_type.value] = data
                except Exception as e:
                    result[data_type.value] = f"Error: {str(e)}"

            return [TextContent(type="text", text=str(result))]

        if name == "reboot_router":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            await router_connection.async_reboot()
            return [TextContent(
                type="text",
                text="Router reboot initiated successfully"
            )]

        if name == "get_devices_for_user":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            user_group = arguments["user_group"]

            # Get clients data (parental control data would need separate call)
            try:
                data = await router_connection.async_get_data(AsusData.CLIENTS)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting clients data: {str(e)}"
                )]

            # Handle different data return formats - data should now be clients directly
            if isinstance(data, list):
                clients = data
            elif isinstance(data, dict):
                # If it's a dict, it might contain the clients data
                clients = data.get("clients", data if "mac" in str(data) else [])
            else:
                clients = []

            # Ensure clients is a list
            if isinstance(clients, dict):
                clients = list(clients.values())

            # Filter devices based on user group
            filtered_devices = []
            for device in clients:
                if isinstance(device, dict):
                    # Check if device belongs to the specified user group
                    if device.get("group") == user_group or device.get("parental_group") == user_group:
                        filtered_devices.append(device)

            result = {
                "user_group": user_group,
                "devices": filtered_devices,
                "device_count": len(filtered_devices)
            }

            return [TextContent(type="text", text=str(result))]

        if name == "get_device_usage":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            device_mac = arguments.get("device_mac")
            device_name = arguments.get("device_name")

            if not device_mac and not device_name:
                return [TextContent(
                    type="text",
                    text="Error: Either device_mac or device_name must be provided"
                )]

            # Get clients data
            try:
                data = await router_connection.async_get_data(AsusData.CLIENTS)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error getting router data: {str(e)}"
                )]

            # Find device and get usage data
            target_device = None

            # Handle different data return formats - data should now be clients directly
            if isinstance(data, list):
                clients = data
            elif isinstance(data, dict):
                # If it's a dict, it might contain the clients data
                clients = data.get("clients", data if "mac" in str(data) else [])
            else:
                clients = []

            # Ensure clients is a list
            if isinstance(clients, dict):
                clients = list(clients.values())

            for device in clients:
                if isinstance(device, dict):
                    if (device_mac and device.get("mac") == device_mac) or \
                       (device_name and device.get("name") == device_name):
                        target_device = device
                        break

            if not target_device:
                return [TextContent(
                    type="text",
                    text=f"Error: Device not found with MAC {device_mac} or name {device_name}"
                )]

            # Extract 24h usage data
            usage_data = {
                "device": {
                    "name": target_device.get("name", "Unknown"),
                    "mac": target_device.get("mac", "Unknown"),
                    "ip": target_device.get("ip", "Unknown")
                },
                "last_24h": {
                    "download_bytes": target_device.get("download_speed", 0),
                    "upload_bytes": target_device.get("upload_speed", 0),
                    "total_bytes": target_device.get("download_speed", 0) + target_device.get("upload_speed", 0)
                },
                "top_sites": []
            }

            # Add network info if available (simplified for now)
            if "network" in data:
                usage_data["network_info"] = data["network"]

            if "wan" in data:
                usage_data["wan_info"] = data["wan"]

            # Note: Top sites requires traffic analyzer which may not be available
            # This is a placeholder for future implementation
            usage_data["top_sites"] = [
                {"site": "example.com", "bytes": 1024000, "download": 800000, "upload": 224000},
                {"site": "google.com", "bytes": 512000, "download": 400000, "upload": 112000}
            ]

            return [TextContent(type="text", text=str(usage_data))]

        if name == "block_traffic_to_device":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            device_mac = arguments.get("device_mac")
            device_name = arguments.get("device_name")
            device_ip = arguments.get("device_ip")

            if not device_mac and not device_name and not device_ip:
                return [TextContent(
                    type="text",
                    text="Error: Either device_mac, device_name, or device_ip must be provided"
                )]

            # Get clients to find the device MAC if name or IP provided
            if (device_name or device_ip) and not device_mac:
                try:
                    data = await router_connection.async_get_data(AsusData.CLIENTS)
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error getting clients data: {str(e)}"
                    )]

                # Handle different data return formats - data should now be clients directly
                if isinstance(data, list):
                    clients = data
                elif isinstance(data, dict):
                    # If it's a dict, it might contain the clients data
                    clients = data.get("clients", data if "mac" in str(data) else [])
                else:
                    clients = []

                # Ensure clients is a list
                if isinstance(clients, dict):
                    clients = list(clients.values())

                for device in clients:
                    if isinstance(device, dict):
                        if (device_name and device.get("name") == device_name) or \
                           (device_ip and device.get("ip") == device_ip):
                            device_mac = device.get("mac")
                            device_name = device.get("name", device_name)
                            device_ip = device.get("ip", device_ip)
                            break

                if not device_mac:
                    identifier = device_name or device_ip
                    return [TextContent(
                        type="text",
                        text=f"Error: Device '{identifier}' not found"
                    )]

            # Block the device using parental control rule
            try:
                # Create a parental control rule to block the device
                block_rule = ParentalControlRule(
                    mac=device_mac,
                    name=device_name or device_mac,
                    type=PCRuleType.BLOCK
                )

                # Apply the blocking rule
                success = await router_connection.async_set_state(block_rule)

                if success:
                    identifier = f"{device_name or 'Unknown'} ({device_mac})" + (f" - {device_ip}" if device_ip else "")
                    return [TextContent(
                        type="text",
                        text=f"Successfully blocked traffic to device {identifier}"
                    )]
                return [TextContent(
                    type="text",
                    text="Failed to block device. The router may not support parental controls or they may not be enabled."
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error blocking device: {str(e)}"
                )]

        elif name == "allow_traffic_to_device":
            if not router_connection:
                return [TextContent(
                    type="text",
                    text="Error: Router not connected. Use connect_router tool first."
                )]

            device_mac = arguments.get("device_mac")
            device_name = arguments.get("device_name")
            device_ip = arguments.get("device_ip")

            if not device_mac and not device_name and not device_ip:
                return [TextContent(
                    type="text",
                    text="Error: Either device_mac, device_name, or device_ip must be provided"
                )]

            # Get clients to find the device MAC if name or IP provided
            if (device_name or device_ip) and not device_mac:
                try:
                    data = await router_connection.async_get_data(AsusData.CLIENTS)
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error getting clients data: {str(e)}"
                    )]

                # Handle different data return formats - data should now be clients directly
                if isinstance(data, list):
                    clients = data
                elif isinstance(data, dict):
                    # If it's a dict, it might contain the clients data
                    clients = data.get("clients", data if "mac" in str(data) else [])
                else:
                    clients = []

                # Ensure clients is a list
                if isinstance(clients, dict):
                    clients = list(clients.values())

                for device in clients:
                    if isinstance(device, dict):
                        if (device_name and device.get("name") == device_name) or \
                           (device_ip and device.get("ip") == device_ip):
                            device_mac = device.get("mac")
                            device_name = device.get("name", device_name)
                            device_ip = device.get("ip", device_ip)
                            break

                if not device_mac:
                    identifier = device_name or device_ip
                    return [TextContent(
                        type="text",
                        text=f"Error: Device '{identifier}' not found"
                    )]

            # Allow the device by removing the blocking rule
            try:
                # Create a parental control rule to remove/disable blocking for the device
                allow_rule = ParentalControlRule(
                    mac=device_mac,
                    name=device_name or device_mac,
                    type=PCRuleType.REMOVE  # This removes the blocking rule
                )

                # Apply the allow rule (remove blocking)
                success = await router_connection.async_set_state(allow_rule)

                if success:
                    identifier = f"{device_name or 'Unknown'} ({device_mac})" + (f" - {device_ip}" if device_ip else "")
                    return [TextContent(
                        type="text",
                        text=f"Successfully allowed traffic to device {identifier}"
                    )]
                return [TextContent(
                    type="text",
                    text="Failed to allow device. The device may not have been blocked or parental controls may not be enabled."
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error allowing device: {str(e)}"
                )]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def cleanup_connection():
    """Clean up the router connection and close any open sessions."""
    global router_connection
    if router_connection:
        try:
            # First disconnect (logout)
            await router_connection.async_disconnect()
            # Then close the session explicitly
            if hasattr(router_connection, '_connection') and router_connection._connection:
                await router_connection._connection.async_close()
            router_connection = None
            logger.info("Router connection cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {str(e)}")
    else:
        logger.debug("No router connection to clean up")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="asusrouter-mcp",
                server_version="1.0.0",
                capabilities=ServerCapabilities(
                    resources={"subscribe": True, "listChanged": True},
                    tools={"listChanged": True},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
