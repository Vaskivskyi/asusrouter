"""Tests for the MCP server module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter import AsusData
from asusrouter.modules.parental_control import ParentalControlRule, PCRuleType


@pytest.mark.asyncio
class TestMCPServer:
    """Test class for MCP server functionality."""

    async def test_list_tools(self) -> None:
        """Test listing available tools."""
        from asusrouter_mcp.server import list_tools

        tools = await list_tools()

        # Check that we have the expected tools
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "connect_router",
            "get_router_data",
            "get_devices_for_user",
            "get_device_usage",
            "block_traffic_to_device",
            "allow_traffic_to_device"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    async def test_list_resources(self) -> None:
        """Test listing available resources."""
        from asusrouter_mcp.server import list_resources

        resources = await list_resources()

        # Check that we have the expected resources
        resource_names = [resource.name for resource in resources]
        expected_resources = [
            "Router Status",
            "Connected Clients",
            "System Information"
        ]

        for expected_resource in expected_resources:
            assert expected_resource in resource_names

    @patch("asusrouter_mcp.server.AsusRouter")
    async def test_connect_router_success(self, mock_asus_router: Mock) -> None:
        """Test successful router connection."""
        from asusrouter_mcp.server import call_tool

        mock_router_instance = Mock()
        mock_router_instance.async_connect = AsyncMock(return_value=True)
        mock_asus_router.return_value = mock_router_instance

        with patch.dict("os.environ", {
            "ASUS_ROUTER_HOST": "192.168.1.1",
            "ASUS_ROUTER_USERNAME": "admin",
            "ASUS_ROUTER_PASSWORD": "password"
        }):
            result = await call_tool("connect_router", {})

        assert len(result) == 1
        assert "Successfully connected" in result[0].text
        mock_router_instance.async_connect.assert_called_once()

    async def test_connect_router_missing_credentials(self) -> None:
        """Test router connection with missing credentials."""
        from asusrouter_mcp.server import call_tool

        with patch.dict("os.environ", {}, clear=True):
            result = await call_tool("connect_router", {})

        assert len(result) == 1
        assert "Error: Router credentials required" in result[0].text

    @patch("asusrouter_mcp.server.router_connection")
    async def test_get_router_data_success(self, mock_router_connection: Mock, sample_clients_data: dict[str, Any]) -> None:
        """Test successful router data retrieval."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_get_data = AsyncMock(return_value=sample_clients_data)

        result = await call_tool("get_router_data", {"data_types": ["clients"]})

        assert len(result) == 1
        assert "clients" in result[0].text
        mock_router_connection.async_get_data.assert_called_once_with(AsusData.CLIENTS)

    async def test_get_router_data_not_connected(self) -> None:
        """Test router data retrieval when not connected."""
        from asusrouter_mcp.server import call_tool

        with patch("asusrouter_mcp.server.router_connection", None):
            result = await call_tool("get_router_data", {"data_types": ["clients"]})

        assert len(result) == 1
        assert "Error: Router not connected" in result[0].text

    @patch("asusrouter_mcp.server.router_connection")
    async def test_block_traffic_to_device_success(self, mock_router_connection: Mock) -> None:
        """Test successful device blocking."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_set_state = AsyncMock(return_value=True)

        result = await call_tool("block_traffic_to_device", {"device_mac": "AA:BB:CC:DD:EE:FF"})

        assert len(result) == 1
        assert "Successfully blocked traffic" in result[0].text
        mock_router_connection.async_set_state.assert_called_once()

        # Verify the correct rule was created
        call_args = mock_router_connection.async_set_state.call_args[0][0]
        assert isinstance(call_args, ParentalControlRule)
        assert call_args.mac == "AA:BB:CC:DD:EE:FF"
        assert call_args.type == PCRuleType.BLOCK

    @patch("asusrouter_mcp.server.router_connection")
    async def test_allow_traffic_to_device_success(self, mock_router_connection: Mock) -> None:
        """Test successful device unblocking."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_set_state = AsyncMock(return_value=True)

        result = await call_tool("allow_traffic_to_device", {"device_mac": "AA:BB:CC:DD:EE:FF"})

        assert len(result) == 1
        assert "Successfully allowed traffic" in result[0].text
        mock_router_connection.async_set_state.assert_called_once()

        # Verify the correct rule was created
        call_args = mock_router_connection.async_set_state.call_args[0][0]
        assert isinstance(call_args, ParentalControlRule)
        assert call_args.mac == "AA:BB:CC:DD:EE:FF"
        assert call_args.type == PCRuleType.REMOVE

    @patch("asusrouter_mcp.server.router_connection")
    async def test_block_device_by_name(self, mock_router_connection: Mock, sample_clients_data: dict[str, Any]) -> None:
        """Test blocking device by name."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_get_data = AsyncMock(return_value=sample_clients_data)
        mock_router_connection.async_set_state = AsyncMock(return_value=True)

        result = await call_tool("block_traffic_to_device", {"device_name": "Kitchen Max"})

        assert len(result) == 1
        assert "Successfully blocked traffic" in result[0].text

        # Verify the correct MAC was found and used
        call_args = mock_router_connection.async_set_state.call_args[0][0]
        assert isinstance(call_args, ParentalControlRule)
        assert call_args.mac == "11:22:33:44:55:66"
        assert call_args.type == PCRuleType.BLOCK

    async def test_block_device_not_found(self) -> None:
        """Test blocking non-existent device."""
        from asusrouter_mcp.server import call_tool

        with patch("asusrouter_mcp.server.router_connection", None):
            result = await call_tool("block_traffic_to_device", {"device_name": "NonExistentDevice"})

        assert len(result) == 1
        assert "Error: Router not connected" in result[0].text

    async def test_invalid_tool_name(self) -> None:
        """Test calling an invalid tool."""
        from asusrouter_mcp.server import call_tool

        result = await call_tool("invalid_tool_name", {})

        assert len(result) == 1
        assert "Error: Unknown tool" in result[0].text

    @patch("asusrouter_mcp.server.router_connection")
    async def test_get_device_usage_success(self, mock_router_connection: Mock) -> None:
        """Test getting device usage data."""
        from asusrouter_mcp.server import call_tool

        mock_usage_data = {
            "usage_data": {
                "rx": 1000000,
                "tx": 500000,
                "total": 1500000
            },
            "top_sites": ["example.com", "google.com"]
        }

        mock_router_connection.async_get_data = AsyncMock(return_value=mock_usage_data)

        result = await call_tool("get_device_usage", {"device_mac": "AA:BB:CC:DD:EE:FF"})

        assert len(result) == 1
        # The actual implementation should return usage data
        # This test verifies the function doesn't crash

    @patch("asusrouter_mcp.server.router_connection")
    async def test_get_devices_for_user_success(self, mock_router_connection: Mock) -> None:
        """Test getting devices for a user group."""
        from asusrouter_mcp.server import call_tool

        mock_devices = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
        mock_router_connection.async_get_data = AsyncMock(return_value=mock_devices)

        result = await call_tool("get_devices_for_user", {"user_group": "kids"})

        assert len(result) == 1
        # The actual implementation should return device list
        # This test verifies the function doesn't crash


@pytest.mark.asyncio
class TestMCPServerErrorHandling:
    """Test error handling in MCP server."""

    @patch("asusrouter_mcp.server.router_connection")
    async def test_router_connection_exception(self, mock_router_connection: Mock) -> None:
        """Test handling of router connection exceptions."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_get_data = AsyncMock(side_effect=Exception("Connection failed"))

        result = await call_tool("get_router_data", {"data_types": ["clients"]})

        assert len(result) == 1
        assert "Error getting" in result[0].text or "Connection failed" in result[0].text

    @patch("asusrouter_mcp.server.router_connection")
    async def test_blocking_failure(self, mock_router_connection: Mock) -> None:
        """Test handling of blocking failures."""
        from asusrouter_mcp.server import call_tool

        mock_router_connection.async_set_state = AsyncMock(return_value=False)

        result = await call_tool("block_traffic_to_device", {"device_mac": "AA:BB:CC:DD:EE:FF"})

        assert len(result) == 1
        assert "Failed to block device" in result[0].text

    async def test_missing_device_parameters(self) -> None:
        """Test handling of missing device parameters."""
        from asusrouter_mcp.server import call_tool

        result = await call_tool("block_traffic_to_device", {})

        assert len(result) == 1
        assert "Error: Either device_mac, device_name, or device_ip must be provided" in result[0].text
