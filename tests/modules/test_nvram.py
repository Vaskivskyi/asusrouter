"""Tests for the NVRAM module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.nvram import ARNvramType, get_state, translate_state
from asusrouter.tools.identifiers import MacAddress


@pytest.mark.asyncio
async def test_get_state_filters_invalid_keys() -> None:
    """Test get_state ignores invalid NVRAM keys."""

    callback = AsyncMock(
        return_value={"label_mac": "00:11:22:33:44:55", "bad": "x"}
    )

    result = await get_state(callback, ARNvramType.MAC)

    assert result == {ARNvramType.MAC: "00:11:22:33:44:55"}
    callback.assert_awaited_once()


def test_translate_state_preserves_string_values() -> None:
    """Test translate_state preserves string values."""

    data = {
        ARNvramType.MODEL: "RT-AX88U",
        ARNvramType.SERIAL: "12345",
    }

    result = translate_state(data)

    assert result == data


def test_translate_state_converts_mac_address() -> None:
    """Test translate_state converts MAC values using MacAddress."""

    data = {ARNvramType.MAC: "00:11:22:33:44:55"}

    result = translate_state(data)

    assert isinstance(result[ARNvramType.MAC], MacAddress)
    assert str(result[ARNvramType.MAC]) == "00:11:22:33:44:55"
