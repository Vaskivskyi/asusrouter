"""Tests for the static DHCP source."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.static_dhcp import (
    STATIC_DHCP_REQUEST,
    ARStaticDHCPField,
    ARStaticDHCPSourceUniversal,
    fetch_state,
    translate_state,
)


async def test_fetch_state_uses_nvram_pipeline() -> None:
    """The source fetches both authoritative NVRAM values."""

    values = {
        ARNvramType.STATIC_DHCP_STATE: "1",
        ARNvramType.STATIC_DHCP_LIST: "",
    }
    get_data = AsyncMock(return_value=values)
    callback = AsyncMock()

    result = await fetch_state(
        callback,
        ARStaticDHCPSourceUniversal,
        fetch_data_callback=get_data,
    )

    assert result == values
    get_data.assert_awaited_once_with(STATIC_DHCP_REQUEST)
    callback.assert_not_awaited()


def test_disabled_source_preserves_saved_leases() -> None:
    """A disabled toggle does not mean its saved reservations are empty."""

    result = translate_state(
        {
            ARNvramType.STATIC_DHCP_STATE: "0",
            ARNvramType.STATIC_DHCP_LIST: (
                "<AA:BB:CC:DD:EE:FF>192.168.1.2>printer"
            ),
        }
    )

    assert result[ARStaticDHCPField.STATE] is False
    assert result[ARStaticDHCPField.COMPLETE] is True
    assert len(result[ARStaticDHCPField.LEASES]) == 1


def test_missing_value_is_not_an_empty_snapshot() -> None:
    """A partial NVRAM read cannot authorize a whole-list mutation."""

    result = translate_state({ARNvramType.STATIC_DHCP_STATE: "1"})
    assert result[ARStaticDHCPField.COMPLETE] is False

    result = translate_state(
        {
            ARNvramType.STATIC_DHCP_STATE: "1",
            ARNvramType.STATIC_DHCP_LIST: None,
        }
    )
    assert result[ARStaticDHCPField.COMPLETE] is False


def test_malformed_row_disables_mutation() -> None:
    """Unknown rows make the snapshot incomplete instead of being dropped."""

    result = translate_state(
        {
            ARNvramType.STATIC_DHCP_STATE: "1",
            ARNvramType.STATIC_DHCP_LIST: (
                "<AA:BB:CC:DD:EE:FF>192.168.1.2<opaque>"
            ),
        }
    )
    assert result[ARStaticDHCPField.COMPLETE] is False
    assert result[ARStaticDHCPField.LEASES] == []
