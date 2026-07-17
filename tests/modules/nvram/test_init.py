"""Tests for the NVRAM module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_FETCH_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.common.connection import ARConnectionStatus
from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
    async_expire_values,
    async_fetch_values,
    async_get_value,
    fetch_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import IpAddress, MacAddress


class TestGetState:
    """Tests for fetch_state."""

    @pytest.mark.asyncio
    async def test_filters_invalid_keys(self) -> None:
        """Keys not in ARNvramType enum are dropped from the result."""

        callback = AsyncMock(
            return_value={"label_mac": "00:11:22:33:44:55", "bad_key": "x"}
        )
        result = await fetch_state(callback, ARNvramType.MAC)
        assert result == {ARNvramType.MAC: "00:11:22:33:44:55"}
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_filters_unknown_member(self) -> None:
        """Keys mapping to ARNvramType.UNKNOWN are dropped from the result."""

        callback = AsyncMock(
            return_value={"label_mac": "00:11:22:33:44:55", "unknown": "x"}
        )
        result = await fetch_state(callback, ARNvramType.MAC)
        assert ARNvramType.UNKNOWN not in result
        assert result == {ARNvramType.MAC: "00:11:22:33:44:55"}

    @pytest.mark.parametrize("response", [None, "string", 42, []])
    @pytest.mark.asyncio
    async def test_non_dict_response_returns_empty(
        self, response: Any
    ) -> None:
        """Non-dict response returns an empty dict."""

        callback = AsyncMock(return_value=response)
        result = await fetch_state(callback, ARNvramType.MAC)
        assert result == {}

    @pytest.mark.asyncio
    async def test_list_source(self) -> None:
        """fetch_state accepts an iterable of ARNvramType (multicall mode)."""

        callback = AsyncMock(
            return_value={
                "label_mac": "00:11:22:33:44:55",
                "productid": "RT-AX88U",
            }
        )
        result = await fetch_state(
            callback, [ARNvramType.MAC, ARNvramType.MODEL]
        )
        assert result == {
            ARNvramType.MAC: "00:11:22:33:44:55",
            ARNvramType.MODEL: "RT-AX88U",
        }

    @pytest.mark.asyncio
    async def test_request_built_from_hooks(self) -> None:
        """The request renders each item as an `nvram_get` hook call."""

        callback = AsyncMock(return_value={})
        await fetch_state(callback, [ARNvramType.MAC, ARNvramType.MODEL])
        kwargs = callback.await_args.kwargs
        assert (
            kwargs["request"]
            == "hook=nvram_get(label_mac);nvram_get(productid)"
        )


class TestAsHook:
    """Tests for as_hook rendering."""

    def test_type(self) -> None:
        """A flat NVRAM type renders its raw key."""

        assert ARNvramType.MAC.as_hook() == (ARHook.NVRAM_GET, "label_mac")

    def test_index_source(self) -> None:
        """An indexed source renders its resolved key."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_IPADDR, 1)
        assert source.as_hook() == (ARHook.NVRAM_GET, "wan1_ipaddr")


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


class TestARNvramIndexSource:
    """Tests for ARNvramIndexSource."""

    def test_key(self) -> None:
        """The key resolves the template with the index."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_IPADDR, 0)
        assert source.key == "wan0_ipaddr"

    def test_equality_and_hash(self) -> None:
        """Sources are equal and hash alike by kind and index."""

        a = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 1)
        b = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 1)
        c = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 0)

        assert a == b
        assert a != c
        assert hash(a) == hash(b)

    def test_equality_other_type(self) -> None:
        """Comparison with a non-source returns NotImplemented / False."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 0)
        assert source.__eq__("x") is NotImplemented
        assert (source == "x") is False

    def test_repr(self) -> None:
        """The repr contains the resolved key."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_GATEWAY, 1)
        assert repr(source) == "<ARNvramIndexSource wan1_gateway>"


class TestGetStateIndexed:
    """Tests for fetch_state with indexed sources."""

    @pytest.mark.asyncio
    async def test_single_indexed(self) -> None:
        """An indexed source maps its resolved key back to itself."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_IPADDR, 0)
        callback = AsyncMock(return_value={"wan0_ipaddr": "1.2.3.4"})
        result = await fetch_state(callback, source)
        assert result == {source: "1.2.3.4"}

    @pytest.mark.asyncio
    async def test_mixed_flat_and_indexed(self) -> None:
        """Flat and indexed items are both mapped back to their requesters."""

        flat = ARNvramType.MAC
        indexed = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 1)
        callback = AsyncMock(
            return_value={
                "label_mac": "00:11:22:33:44:55",
                "wan1_state_t": "2",
            }
        )
        result = await fetch_state(callback, [flat, indexed])
        assert result == {flat: "00:11:22:33:44:55", indexed: "2"}

    @pytest.mark.asyncio
    async def test_unrequested_key_dropped(self) -> None:
        """Response keys that were not requested are dropped."""

        source = ARNvramIndexSource(ARNvramIndexType.WAN_IPADDR, 0)
        callback = AsyncMock(
            return_value={"wan0_ipaddr": "1.2.3.4", "other": "x"}
        )
        result = await fetch_state(callback, source)
        assert result == {source: "1.2.3.4"}


class TestTranslateStateIndexed:
    """Tests for translate_state with indexed and WAN values."""

    def test_indexed_keyed_on_template(self) -> None:
        """Indexed values translate via their template type."""

        state = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 0)
        ipaddr = ARNvramIndexSource(ARNvramIndexType.WAN_IPADDR, 0)
        result = translate_state({state: "2", ipaddr: "1.2.3.4"})

        assert result[state] is ARConnectionStatus.CONNECTED
        assert result[ipaddr] == IpAddress.from_value("1.2.3.4")

    def test_indexed_untranslated_preserved(self) -> None:
        """An indexed member without a translator is kept as-is."""

        source = ARNvramIndexSource(ARNvramIndexType.UNKNOWN, 0)
        assert translate_state({source: "raw"}) == {source: "raw"}

    def test_flat_wan_values(self) -> None:
        """Flat WAN members translate via the table."""

        result = translate_state(
            {
                ARNvramType.LINK_INTERNET: "2",
                ARNvramType.DUAL_WAN_CONFIG: "lan usb",
            }
        )
        assert result[ARNvramType.LINK_INTERNET] is (
            ARConnectionStatus.CONNECTED
        )
        assert result[ARNvramType.DUAL_WAN_CONFIG] == ["lan", "usb"]


class TestAsyncExpireValues:
    """Tests for async_expire_values."""

    @pytest.mark.asyncio
    async def test_expires_each_item(self) -> None:
        """Every requested item is expired individually."""

        expire = AsyncMock()
        request = (ARNvramType.MAC, ARNvramType.WAN_UNIT)
        await async_expire_values(expire, request)

        assert expire.await_count == 2
        expire.assert_any_await(ARNvramType.MAC)
        expire.assert_any_await(ARNvramType.WAN_UNIT)

    @pytest.mark.asyncio
    async def test_single_item(self) -> None:
        """A single item works without wrapping it in an iterable."""

        expire = AsyncMock()
        source = ARNvramIndexSource(ARNvramIndexType.WAN_STATE, 0)
        await async_expire_values(expire, source)

        expire.assert_awaited_once_with(source)

    @pytest.mark.asyncio
    async def test_no_callback(self) -> None:
        """Without a callback nothing happens."""

        await async_expire_values(None, ARNvramType.MAC)


class TestAsyncFetchValues:
    """Tests for async_fetch_values."""

    @pytest.mark.asyncio
    async def test_no_callback(self) -> None:
        """Without a callback an empty dict is returned."""

        assert await async_fetch_values(None, ARNvramType.MAC) == {}

    @pytest.mark.asyncio
    async def test_returns_dict(self) -> None:
        """A dict result is passed through."""

        callback = AsyncMock(return_value={ARNvramType.MAC: "x"})
        result = await async_fetch_values(callback, ARNvramType.MAC)
        assert result == {ARNvramType.MAC: "x"}

    @pytest.mark.parametrize("response", [None, "string", 42, []])
    @pytest.mark.asyncio
    async def test_non_dict_returns_empty(self, response: Any) -> None:
        """A non-dict result yields an empty dict."""

        callback = AsyncMock(return_value=response)
        assert await async_fetch_values(callback, ARNvramType.MAC) == {}


class TestAsyncGetValue:
    """Tests for async_get_value."""

    @pytest.mark.asyncio
    async def test_returns_item_value(self) -> None:
        """The value for the requested item is returned."""

        callback = AsyncMock(return_value={ARNvramType.MAC: "aa:bb"})
        assert await async_get_value(callback, ARNvramType.MAC) == "aa:bb"

    @pytest.mark.asyncio
    async def test_missing_item_returns_none(self) -> None:
        """A missing item yields None."""

        callback = AsyncMock(return_value={})
        assert await async_get_value(callback, ARNvramType.MAC) is None


@pytest.mark.parametrize("cls", [ARNvramType, ARNvramIndexSource])
def test_module_registers_callables(cls: type) -> None:
    """Both source classes register the batched callables on import."""

    assert ARCallReg.get_callable(cls, AR_CALL_FETCH_STATE) is fetch_state
    assert (
        ARCallReg.get_callable(cls, AR_CALL_TRANSLATE_STATE) is translate_state
    )
    assert ARCallReg.get_callable_flag(cls, AR_CALL_FETCH_STATE) is True
    assert ARCallReg.get_callable_flag(cls, AR_CALL_TRANSLATE_STATE) is True
