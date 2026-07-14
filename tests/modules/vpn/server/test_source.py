"""Tests for the VPN server data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.vpn.enums import ARVpnProtocol, ARVpnServerField
from asusrouter.modules.vpn.server.openvpn import CLIENT_STATUS_KEY
from asusrouter.modules.vpn.server.source import (
    ARVpnServerSource,
    ARVpnServerSourceUniversal,
    get_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg


class TestGetState:
    """Tests for get_state."""

    async def test_fetches_appget(self) -> None:
        """The request carries the WG hook and nvram keys."""

        callback = AsyncMock(return_value={"VPNServer_enable": "0"})
        await get_state(callback, ARVpnServerSourceUniversal)

        args = callback.call_args.kwargs
        assert args["endpoint"] is AREndpoint.FETCH_DATA
        assert args["request"].startswith("hook=get_wgsc_status();")
        assert "nvram_get(wgs_enable)" in args["request"]

    async def test_ovpn_disabled_single_call(self) -> None:
        """A disabled OpenVPN server skips the extra status fetch."""

        callback = AsyncMock(return_value={"VPNServer_enable": "0"})
        await get_state(callback, ARVpnServerSourceUniversal)

        assert callback.call_count == 1

    async def test_ovpn_enabled_second_call(self) -> None:
        """An enabled OpenVPN server fetches the connected-client status."""

        callback = AsyncMock(
            side_effect=[
                {"VPNServer_enable": "1"},
                {"connected": []},
            ]
        )
        result = await get_state(callback, ARVpnServerSourceUniversal)

        assert callback.call_count == 2
        second = callback.call_args_list[1].kwargs
        assert second["endpoint"] is AREndpoint.FETCH_VPN_OPENVPN_STATUS
        assert result[CLIENT_STATUS_KEY] == {"connected": []}

    async def test_non_dict_response(self) -> None:
        """A non-dict response is returned untouched, no extra call."""

        callback = AsyncMock(return_value=None)
        result = await get_state(callback, ARVpnServerSourceUniversal)

        assert result is None
        assert callback.call_count == 1


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, "text", 42, []])
    def test_bad_data(self, data: Any) -> None:
        """Non-dict data yields an empty result."""

        assert translate_state(data) == {}

    def test_groups_by_protocol(self) -> None:
        """Both backends contribute, grouped by protocol."""

        data = {
            "wgs_enable": "1",
            "VPNServer_enable": "1",
            "vpn_server_unit": "1",
            "vpn_server1_state": "2",
        }
        result = translate_state(data)

        assert set(result) == {ARVpnProtocol.WIREGUARD, ARVpnProtocol.OPENVPN}

    def test_empty_backend_dropped(self) -> None:
        """A protocol with no data is omitted."""

        result = translate_state({"wgs_enable": "1"})
        assert set(result) == {ARVpnProtocol.WIREGUARD}
        assert result[ARVpnProtocol.WIREGUARD][1][ARVpnServerField.ENABLED]


def test_source_is_registered() -> None:
    """The source registers get_state and translate_state."""

    assert (
        ARCallReg.get_callable(ARVpnServerSourceUniversal, AR_CALL_GET_STATE)
        is get_state
    )
    assert (
        ARCallReg.get_callable(ARVpnServerSource, AR_CALL_TRANSLATE_STATE)
        is translate_state
    )
