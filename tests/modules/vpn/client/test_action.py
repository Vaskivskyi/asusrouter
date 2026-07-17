"""Tests for the VPN client action module."""

from __future__ import annotations

from unittest.mock import AsyncMock

from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.service.action import ARServiceResult
from asusrouter.modules.vpn.client.action import ARVpnClientAction, run_action
from asusrouter.modules.vpn.enums import ARVpnProtocol
from asusrouter.registry import ARCallableRegistry as ARCallReg

# Real device clientlist (entity-encoded): WG Proton + OVPN, both server 5
_CLIENTLIST = (
    "Proton&#62WireGuard&#625&#62&#62&#621&#625&#62&#62&#620&#620&#62Web"
    "&#60Prtn&#62OpenVPN&#625&#62u&#62p&#621&#626&#62&#62&#620&#620&#62Web"
)


class TestARVpnClientAction:
    """Tests for ARVpnClientAction."""

    def test_stores_fields(self) -> None:
        """Protocol, unit and desired state are stored as given."""

        action = ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=5)
        assert action.protocol is ARVpnProtocol.WIREGUARD
        assert action.unit == 5
        assert action.state is True

    def test_unit_defaults(self) -> None:
        """`unit` defaults to 1 and is keyword-only."""

        assert ARVpnClientAction(ARVpnProtocol.OPENVPN, False).unit == 1

    def test_equality_and_hash(self) -> None:
        """Actions are equal by protocol, unit and state."""

        base = ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=5)
        assert base == ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=5)
        assert hash(base) == hash(
            ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=5)
        )
        assert base != ARVpnClientAction(
            ARVpnProtocol.WIREGUARD, False, unit=5
        )
        assert base != ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=1)
        assert base != ARVpnClientAction(ARVpnProtocol.OPENVPN, True, unit=5)
        assert base != object()

    def test_registered(self) -> None:
        """The action resolves a run_action callable via the registry."""

        assert (
            ARCallReg.get_callable(
                ARVpnClientAction(ARVpnProtocol.WIREGUARD, True),
                AR_CALL_RUN_ACTION,
            )
            is run_action
        )


class TestRunAction:
    """Tests for VPN client run_action."""

    async def test_fusion_rewrites_clientlist(self) -> None:
        """A Fusion device flips the activate flag and runs restart_vpnc."""

        fetch_data_callback = AsyncMock(
            return_value={ARNvramType.VPNC_CLIENTLIST: _CLIENTLIST}
        )
        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnClientAction(ARVpnProtocol.WIREGUARD, False, unit=5)

        result = await run_action(
            AsyncMock(),
            action,
            fetch_data_callback=fetch_data_callback,
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result.success is True
        fetch_data_callback.assert_awaited_once_with(
            ARNvramType.VPNC_CLIENTLIST
        )
        push = fetch_raw_callback.await_args.kwargs
        assert push["endpoint"] is AREndpoint.PUSH_DATA
        assert '"rc_service":"stop_vpnc"' in push["request"]
        assert '"vpnc_unit":0' in push["request"]

    async def test_classic_openvpn(self) -> None:
        """Without a clientlist, OpenVPN uses the per-unit service."""

        fetch_data_callback = AsyncMock(return_value={})
        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnClientAction(ARVpnProtocol.OPENVPN, True, unit=2)

        result = await run_action(
            AsyncMock(),
            action,
            fetch_data_callback=fetch_data_callback,
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result.success is True
        request = fetch_raw_callback.await_args.kwargs["request"]
        assert '"rc_service":"start_vpnclient2"' in request

    async def test_classic_wireguard(self) -> None:
        """Classic WireGuard flips the enable flag with `start_wgc`."""

        fetch_data_callback = AsyncMock(return_value={})
        fetch_raw_callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=3)

        await run_action(
            AsyncMock(),
            action,
            fetch_data_callback=fetch_data_callback,
            fetch_raw_callback=fetch_raw_callback,
        )

        request = fetch_raw_callback.await_args.kwargs["request"]
        assert '"rc_service":"start_wgc 3"' in request
        assert '"wgc_enable":1' in request

    async def test_unknown_client_fails(self) -> None:
        """A Fusion device without the target profile fails without a push."""

        fetch_data_callback = AsyncMock(
            return_value={ARNvramType.VPNC_CLIENTLIST: _CLIENTLIST}
        )
        fetch_raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARVpnClientAction(ARVpnProtocol.WIREGUARD, True, unit=9),
            fetch_data_callback=fetch_data_callback,
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result == ARServiceResult(success=False)
        fetch_raw_callback.assert_not_awaited()

    async def test_non_dict_read_uses_classic(self) -> None:
        """A non-dict clientlist read falls back to the classic backend."""

        fetch_data_callback = AsyncMock(return_value="not-a-dict")
        callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnClientAction(ARVpnProtocol.OPENVPN, True, unit=1)

        result = await run_action(
            callback, action, fetch_data_callback=fetch_data_callback
        )

        assert result.success is True
        assert (
            '"rc_service":"start_vpnclient1"'
            in callback.await_args.kwargs["request"]
        )

    async def test_no_data_callback_fails(self) -> None:
        """Without a data callback no backend is known; nothing is pushed."""

        callback = AsyncMock()
        result = await run_action(
            callback, ARVpnClientAction(ARVpnProtocol.WIREGUARD, True)
        )

        assert result == ARServiceResult(success=False)
        callback.assert_not_awaited()

    async def test_unsupported_protocol_fails(self) -> None:
        """A classic protocol without a toggle fails without a push."""

        fetch_data_callback = AsyncMock(return_value={})
        fetch_raw_callback = AsyncMock()
        result = await run_action(
            AsyncMock(),
            ARVpnClientAction(ARVpnProtocol.PPTP, True),
            fetch_data_callback=fetch_data_callback,
            fetch_raw_callback=fetch_raw_callback,
        )

        assert result == ARServiceResult(success=False)
        fetch_raw_callback.assert_not_awaited()

    async def test_falls_back_to_callback(self) -> None:
        """Without a raw callback the plain callback posts the request."""

        fetch_data_callback = AsyncMock(return_value={})
        callback = AsyncMock(return_value="NOT MODIFIED")
        action = ARVpnClientAction(ARVpnProtocol.OPENVPN, False, unit=1)

        result = await run_action(
            callback, action, fetch_data_callback=fetch_data_callback
        )

        assert result.success is True
        callback.assert_awaited_once()
        assert (
            '"rc_service":"stop_vpnclient1"'
            in callback.await_args.kwargs["request"]
        )
