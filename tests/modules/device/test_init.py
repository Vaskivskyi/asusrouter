"""Tests for the device module __init__."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.modules.device import (
    DEVICE_REQUEST,
    DeviceOperationMode,
    get_state,
    translate_state,
)
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.nvram import ARNvramType


class TestDeviceOperationMode:
    """Tests for the DeviceOperationMode enum."""

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("UNKNOWN", UNKNOWN_MEMBER),
            ("ROUTER", 1),
            ("REPEATER", 2),
            ("ACCESS_POINT", 3),
            ("MEDIA_BRIDGE", 4),
            ("AIMESH_NODE", 5),
        ],
    )
    def test_enum_members_and_values(self, name: str, value: int) -> None:
        """Enum members exist and have the expected integer values."""

        member = getattr(DeviceOperationMode, name)
        assert member.name == name
        assert member.value == value


class TestGetState:
    """Tests for get_state."""

    @pytest.mark.asyncio
    async def test_calls_get_data_callback_with_device_request(self) -> None:
        """get_state delegates to get_data_callback with DEVICE_REQUEST."""

        expected = {"key": "value"}
        get_data_callback = AsyncMock(return_value=expected)
        result = await get_state(MagicMock(), MagicMock(), get_data_callback)
        get_data_callback.assert_called_once_with(DEVICE_REQUEST)
        assert result == expected

    @pytest.mark.asyncio
    async def test_ignores_callback_and_source(self) -> None:
        """get_state ignores the callback and source arguments."""

        get_data_callback = AsyncMock(return_value=None)
        await get_state(None, None, get_data_callback)
        get_data_callback.assert_called_once_with(DEVICE_REQUEST)


class TestTranslateState:
    """Tests for translate_state."""

    def test_returns_device_identity(self) -> None:
        """translate_state returns an ARDeviceIdentity instance."""

        result = translate_state({})
        assert isinstance(result, ARDeviceIdentity)

    def test_passes_data_to_build(self) -> None:
        """translate_state builds identity from provided data dict."""

        data = {ARNvramType.MODEL: "RT-AX88U"}
        result = translate_state(data)
        assert isinstance(result, ARDeviceIdentity)
        assert result.model == "RT-AX88U"

    def test_extra_kwargs_ignored(self) -> None:
        """translate_state accepts and ignores extra kwargs."""

        result = translate_state({}, extra_arg="ignored")
        assert isinstance(result, ARDeviceIdentity)
