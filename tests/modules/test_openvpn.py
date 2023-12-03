"""Tests for the openvpn module."""

from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.firmware import Firmware
from asusrouter.modules.identity import AsusDevice
from asusrouter.modules.openvpn import AsusOVPNClient, AsusOVPNServer, set_state

FW_MAJOR = "3.0.0.4"
FW_MINOR_OLD = 386
FW_MINOR_NEW = 388

identity_mock = {
    "merlin_new": AsusDevice(merlin=True, firmware=Firmware(FW_MAJOR, FW_MINOR_NEW, 0)),
    "merlin_old": AsusDevice(merlin=True, firmware=Firmware(FW_MAJOR, FW_MINOR_OLD, 0)),
    "stock_new": AsusDevice(merlin=False, firmware=Firmware(FW_MAJOR, FW_MINOR_NEW, 0)),
    "stock_old": AsusDevice(merlin=False, firmware=Firmware(FW_MAJOR, FW_MINOR_OLD, 0)),
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, vpn_id, identity, expect_modify, expect_call, expected_args, expected_service",
    [
        # Correct states
        (AsusOVPNClient.ON, 1, "merlin_new", True, True, {"id": 1}, "start_vpnclient1"),
        (
            AsusOVPNClient.OFF,
            1,
            "merlin_new",
            False,
            True,
            {"id": 1},
            "stop_vpnclient1",
        ),
        (AsusOVPNServer.ON, 1, "merlin_new", True, True, {"id": 1}, "start_vpnserver1"),
        (
            AsusOVPNServer.OFF,
            1,
            "merlin_new",
            False,
            True,
            {"id": 1},
            "stop_vpnserver1",
        ),
        # Different identity - merlin old
        (AsusOVPNClient.ON, 1, "merlin_old", True, True, {"id": 1}, "start_vpnclient1"),
        (
            AsusOVPNClient.OFF,
            1,
            "merlin_old",
            False,
            True,
            {"id": 1},
            "stop_vpnclient1",
        ),
        # Different identity - stock old
        (AsusOVPNClient.ON, 1, "stock_old", True, True, {"id": 1}, "start_vpnclient1"),
        (
            AsusOVPNClient.OFF,
            1,
            "stock_old",
            False,
            True,
            {"id": 1},
            "stop_vpnclient1",
        ),
        # Get to modern API - stock new
        (
            AsusOVPNServer.ON,
            1,
            "stock_new",
            True,
            True,
            {"id": 1, "VPNServer_enable": "1"},
            "restart_openvpnd;restart_chpass;restart_samba;restart_dnsmasq;",
        ),
        (
            AsusOVPNServer.OFF,
            1,
            "stock_new",
            False,
            True,
            {"id": 1, "VPNServer_enable": "0"},
            "stop_openvpnd;restart_samba;restart_dnsmasq;",
        ),
        # Modern API with unknown state - this should not happen but is handled
        (
            AsusOVPNClient.ON,
            1,
            "stock_new",
            True,
            False,
            {},
            None,
        ),
        # Wrong states
        (AsusOVPNClient.UNKNOWN, 1, "merlin_new", False, False, {}, None),
        (None, 1, "merlin_new", False, False, {}, None),
        # No ID
        (AsusOVPNClient.ON, None, "merlin_new", True, False, {}, None),
        # No identity - should use legacy service
        (AsusOVPNClient.ON, 1, None, True, True, {"id": 1}, "start_vpnclient1"),
    ],
)
async def test_set_state(
    state, vpn_id, identity, expect_modify, expect_call, expected_args, expected_service
):
    """Test set_state."""

    # Create a mock callback function
    callback = AsyncMock()

    # Compile the kwargs
    kwargs = {"id": vpn_id, "identity": identity_mock[identity] if identity else None}

    # Call the set_state function
    await set_state(
        callback=callback, state=state, expect_modify=expect_modify, **kwargs
    )

    # Check if the callback function was called
    if expect_call:
        callback.assert_called_once_with(
            service=expected_service,
            arguments=expected_args,
            apply=True,
            expect_modify=expect_modify,
        )
    else:
        callback.assert_not_called()
