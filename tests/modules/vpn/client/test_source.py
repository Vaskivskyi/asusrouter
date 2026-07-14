"""Tests for the VPN client data source."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_GET_STATE
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.vpn.client.source import (
    ARVpnClientSource,
    ARVpnClientSourceUniversal,
    get_state,
    translate_state,
)
from asusrouter.modules.vpn.enums import ARVpnClientField, ARVpnProtocol
from asusrouter.registry import ARCallableRegistry as ARCallReg


class TestGetState:
    """Tests for get_state."""

    async def test_fusion_skips_vpn_cgi(self) -> None:
        """When a clientlist is present, the classic vpn.cgi is not fetched."""

        callback = AsyncMock(return_value={"vpnc_clientlist": "x"})
        await get_state(callback, ARVpnClientSourceUniversal)

        request = callback.await_args.kwargs["request"]
        assert callback.await_args.kwargs["endpoint"] is AREndpoint.FETCH_DATA
        assert "get_vpnc_status()" in request
        assert "vpnc_clientlist" in request
        assert "vpn_client1_state" in request  # classic keys fetched too
        callback.assert_awaited_once()

    async def test_classic_fetches_vpn_cgi(self) -> None:
        """Without a clientlist, the classic vpn.cgi status is fetched too."""

        callback = AsyncMock(side_effect=[{}, {"vpn_client1_status": "None"}])
        data = await get_state(callback, ARVpnClientSourceUniversal)

        assert callback.await_count == 2
        assert (
            callback.await_args.kwargs["endpoint"]
            is AREndpoint.FETCH_VPN_STATUS
        )
        assert "_vpn_status" in data


class TestTranslateState:
    """Tests for translate_state."""

    def test_non_dict(self) -> None:
        """Non-dict raw data yields an empty result."""

        assert translate_state(None) == {}

    def test_delegates_to_fusion(self) -> None:
        """A clientlist routes to the Fusion backend."""

        data = {"vpnc_clientlist": "P>OpenVPN>3>u>p>1>6>>>0>0>Web"}
        result = translate_state(data)
        assert set(result) == {ARVpnProtocol.OPENVPN}

    def test_delegates_to_classic(self) -> None:
        """No clientlist routes to the classic per-unit backend."""

        data = {"vpn_client1_state": "2", "vpn_client1_desc": "C"}
        result = translate_state(data)
        assert set(result) == {ARVpnProtocol.OPENVPN}
        profile = result[ARVpnProtocol.OPENVPN][1]
        assert profile[ARVpnClientField.NAME] == "C"


class TestRegistration:
    """Tests for source registration."""

    def test_registered(self) -> None:
        """The source resolves a get_state callable via the registry."""

        assert (
            ARCallReg.get_callable(ARVpnClientSource(), AR_CALL_GET_STATE)
            is get_state
        )
