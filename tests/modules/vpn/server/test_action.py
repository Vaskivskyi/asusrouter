"""Tests for the VPN server action module."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.vpn.enums import ARVpnProtocol
from asusrouter.modules.vpn.server.action import ARVpnServerAction, run_action
from asusrouter.registry import ARCallableRegistry as ARCallReg


def _modern_identity() -> ARDeviceIdentity:
    """Build an identity on modern stock firmware (388)."""

    identity = ARDeviceIdentity()
    identity._firmware = ARFirmware(major=(3, 0, 0, 4), minor=388, build=0)
    return identity


class TestARVpnServerAction:
    """Tests for ARVpnServerAction."""

    def test_stores_fields(self) -> None:
        """The protocol, unit and desired state are stored as given."""

        action = ARVpnServerAction(ARVpnProtocol.WIREGUARD, True)
        assert action.protocol is ARVpnProtocol.WIREGUARD
        assert action.unit == 1
        assert action.state is True

    def test_equality_and_hash(self) -> None:
        """Actions are equal by protocol, unit and state."""

        base = ARVpnServerAction(ARVpnProtocol.WIREGUARD, True)
        assert base == ARVpnServerAction(ARVpnProtocol.WIREGUARD, True)
        assert hash(base) == hash(
            ARVpnServerAction(ARVpnProtocol.WIREGUARD, True)
        )
        assert base != ARVpnServerAction(ARVpnProtocol.WIREGUARD, False)
        assert base != ARVpnServerAction(ARVpnProtocol.WIREGUARD, True, unit=2)
        assert base != ARVpnServerAction(ARVpnProtocol.OPENVPN, True)
        assert base != object()

    def test_registered(self) -> None:
        """The action resolves a run_action callable via the registry."""

        assert (
            ARCallReg.get_callable(
                ARVpnServerAction(ARVpnProtocol.WIREGUARD, True),
                AR_CALL_RUN_ACTION,
            )
            is run_action
        )


class TestRunAction:
    """Tests for VPN server run_action."""

    async def test_wireguard_pushes(self) -> None:
        """WireGuard toggles the server and restarts dnsmasq."""

        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnServerAction(ARVpnProtocol.WIREGUARD, True)

        result = await run_action(
            AsyncMock(), action, fetch_raw_callback=fetch_raw_callback
        )

        assert result.success is True
        push = fetch_raw_callback.await_args.kwargs
        assert push["endpoint"] is AREndpoint.PUSH_DATA
        assert '"rc_service":"restart_wgs;restart_dnsmasq"' in push["request"]
        assert '"wgs_enable":1' in push["request"]
        assert '"wgs_unit":1' in push["request"]

    async def test_openvpn_modern_pushes(self) -> None:
        """Modern OpenVPN toggles the enable flag with a service chain."""

        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnServerAction(ARVpnProtocol.OPENVPN, True)

        result = await run_action(
            AsyncMock(),
            action,
            fetch_raw_callback=fetch_raw_callback,
            identity=_modern_identity(),
        )

        assert result.success is True
        request = fetch_raw_callback.await_args.kwargs["request"]
        assert (
            '"rc_service":"restart_openvpnd;restart_chpass;'
            'restart_samba;restart_dnsmasq"' in request
        )
        assert '"VPNServer_enable":1' in request

    async def test_openvpn_legacy_pushes(self) -> None:
        """Without an identity OpenVPN uses the per-unit start service."""

        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnServerAction(ARVpnProtocol.OPENVPN, True, unit=2)

        result = await run_action(
            AsyncMock(), action, fetch_raw_callback=fetch_raw_callback
        )

        assert result.success is True
        request = fetch_raw_callback.await_args.kwargs["request"]
        assert '"rc_service":"start_vpnserver2"' in request

    async def test_unsupported_protocol_fails(self) -> None:
        """A protocol without a backend fails without a push."""

        fetch_raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARVpnServerAction(ARVpnProtocol.IPSEC, True),
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result == ARServiceResult(success=False)
        fetch_raw_callback.assert_not_awaited()

    async def test_falls_back_to_callback(self) -> None:
        """Without a raw callback the plain callback posts the request."""

        callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnServerAction(ARVpnProtocol.WIREGUARD, False)

        result = await run_action(callback, action)

        assert result.success is True
        assert callback.await_args.kwargs["endpoint"] is AREndpoint.PUSH_DATA
        assert '"wgs_enable":0' in callback.await_args.kwargs["request"]
