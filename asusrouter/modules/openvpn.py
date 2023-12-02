"""OpenVPN module for AsusRouter."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Awaitable, Callable

from asusrouter.modules.firmware import Firmware
from asusrouter.tools.converters import get_arguments

_LOGGER = logging.getLogger(__name__)

REQUIRE_IDENTITY = True


class AsusOVPNClient(IntEnum):
    """Asus OpenVPN client state."""

    UNKNOWN = -999
    ERROR = -1
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

    OFF = DISCONNECTED
    ON = CONNECTING


class AsusOVPNServer(IntEnum):
    """Asus OpenVPN server state."""

    UNKNOWN = -999
    ERROR = -1
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

    OFF = DISCONNECTED
    ON = CONNECTING


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusOVPNClient | AsusOVPNServer,
    **kwargs: Any,
) -> bool:
    """Set the OpenVPN state."""

    # Check if state is available
    if not isinstance(state, (AsusOVPNClient, AsusOVPNServer)) or not state.value in (
        0,
        1,
    ):
        _LOGGER.debug("No state found in arguments")
        return False

    # Get the arguments
    vpn_id, identity = get_arguments(("id", "identity"), **kwargs)

    if not vpn_id:
        _LOGGER.debug("No VPN id found in arguments")
        return False

    service_arguments = {"id": vpn_id}

    service_map: dict[Any, str]

    # Get the correct service call
    # This will be firmware dependent
    if (
        not identity
        or identity.merlin
        or identity.firmware < Firmware(major="3.0.0.4", minor=388, build=0)
    ):
        service_map = {
            (AsusOVPNClient, AsusOVPNClient.ON): f"start_vpnclient{vpn_id}",
            (AsusOVPNClient, AsusOVPNClient.OFF): f"stop_vpnclient{vpn_id}",
            (AsusOVPNServer, AsusOVPNServer.ON): f"start_vpnserver{vpn_id}",
            (AsusOVPNServer, AsusOVPNServer.OFF): f"stop_vpnserver{vpn_id}",
        }
        service = service_map.get((type(state), state))
    else:
        service_map = {
            AsusOVPNServer.ON: (
                "restart_openvpnd;restart_chpass;restart_samba;restart_dnsmasq;"
            ),
            AsusOVPNServer.OFF: "stop_openvpnd;restart_samba;restart_dnsmasq;",
        }
        service = service_map.get(state) if isinstance(state, AsusOVPNServer) else None
        service_arguments["VPNServer_enable"] = (
            "1" if state == AsusOVPNServer.ON else "0"
        )

    if not service:
        _LOGGER.debug("Unknown state %s", state)
        return False

    _LOGGER.debug(
        "Triggering state set with parameters: service=%s, arguments=%s",
        service,
        service_arguments,
    )

    # Run the service
    return await callback(
        service=service,
        arguments=service_arguments,
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )
