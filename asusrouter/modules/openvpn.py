"""OpenVPN module for AsusRouter."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.firmware import Firmware
from asusrouter.modules.identity import AsusDevice

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
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    identity: Optional[AsusDevice] = None,
) -> bool:
    """Set the OpenVPN state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    # Get the id from arguments
    vpn_id = arguments.get("id")
    if not vpn_id:
        _LOGGER.debug("No VPN id found in arguments")
        return False

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
        arguments = {
            "VPNServer_enable": "1" if state == AsusOVPNServer.ON else "0",
        }

    # Add `id` to arguments for proper state save
    arguments["id"] = vpn_id

    if not service:
        _LOGGER.debug("Unknown state %s", state)
        return False

    _LOGGER.debug(
        "Triggering state set with parameters: service=%s, arguments=%s",
        service,
        arguments,
    )

    # Run the service
    return await callback(
        service=service,
        arguments=arguments,
        apply=True,
        expect_modify=expect_modify,
    )
