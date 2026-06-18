"""Tests for the NVRAM module."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
import asusrouter.modules.nvram as nvram_module
from asusrouter.modules.nvram import ARNvramType, get_state, translate_state
from asusrouter.tools.identifiers import MacAddress


class TestGetState:
    """Tests for get_state."""

    @pytest.mark.asyncio
    async def test_filters_invalid_keys(self) -> None:
        """Keys not in ARNvramType enum are dropped from the result."""

        callback = AsyncMock(
            return_value={"label_mac": "00:11:22:33:44:55", "bad_key": "x"}
        )
        result = await get_state(callback, ARNvramType.MAC)
        assert result == {ARNvramType.MAC: "00:11:22:33:44:55"}
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_filters_unknown_member(self) -> None:
        """Keys mapping to ARNvramType.UNKNOWN are dropped from the result."""

        callback = AsyncMock(
            return_value={"label_mac": "00:11:22:33:44:55", "unknown": "x"}
        )
        result = await get_state(callback, ARNvramType.MAC)
        assert ARNvramType.UNKNOWN not in result
        assert result == {ARNvramType.MAC: "00:11:22:33:44:55"}

    @pytest.mark.parametrize("response", [None, "string", 42, []])
    @pytest.mark.asyncio
    async def test_non_dict_response_returns_empty(
        self, response: Any
    ) -> None:
        """Non-dict response returns an empty dict."""

        callback = AsyncMock(return_value=response)
        result = await get_state(callback, ARNvramType.MAC)
        assert result == {}

    @pytest.mark.asyncio
    async def test_list_source(self) -> None:
        """get_state accepts an iterable of ARNvramType (multicall mode)."""

        callback = AsyncMock(
            return_value={
                "label_mac": "00:11:22:33:44:55",
                "productid": "RT-AX88U",
            }
        )
        result = await get_state(
            callback, [ARNvramType.MAC, ARNvramType.MODEL]
        )
        assert result == {
            ARNvramType.MAC: "00:11:22:33:44:55",
            ARNvramType.MODEL: "RT-AX88U",
        }


class TestTranslateState:
    """Tests for translate_state."""

    def test_preserves_untranslated_values(self) -> None:
        """Keys without a translator are kept as-is."""

        data = {
            ARNvramType.MODEL: "RT-AX88U",
            ARNvramType.SERIAL: "12345",
        }
        assert translate_state(data) == data

    @pytest.mark.parametrize(
        "nvram_key",
        [ARNvramType.MAC, ARNvramType.MAC_LAN, ARNvramType.MAC_WAN],
    )
    def test_converts_mac_keys_to_mac_address(
        self, nvram_key: ARNvramType
    ) -> None:
        """All MAC keys in _TRANSLATION_TABLE are converted to MacAddress."""

        data = {nvram_key: "00:11:22:33:44:55"}
        result = translate_state(data)
        assert isinstance(result[nvram_key], MacAddress)
        assert str(result[nvram_key]) == "00:11:22:33:44:55"

    def test_mixed_translated_and_plain(self) -> None:
        """MAC key is translated while non-MAC key is preserved."""

        data: dict[ARNvramType, Any] = {
            ARNvramType.MAC: "AA:BB:CC:11:22:33",
            ARNvramType.MODEL: "RT-AX88U",
        }
        result = translate_state(data)
        assert isinstance(result[ARNvramType.MAC], MacAddress)
        assert result[ARNvramType.MODEL] == "RT-AX88U"

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty dict."""

        assert translate_state({}) == {}


def test_module_registers_callables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module registers callables with ARCallReg on import."""

    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register", mock_register
    )
    importlib.reload(nvram_module)

    mock_register.assert_called_once()
    args, kwargs = mock_register.call_args
    assert args[0] is nvram_module.ARNvramType
    assert kwargs[AR_CALL_GET_STATE] == (nvram_module.get_state, True)
    expected_translate = (nvram_module.translate_state, True)
    assert kwargs[AR_CALL_TRANSLATE_STATE] == expected_translate
