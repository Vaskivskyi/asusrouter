"""OpenVPN module for AsusRouter."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

_LOGGER = logging.getLogger(__name__)


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

    # Get the correct service call
    party = "client" if isinstance(state, AsusOVPNClient) else "server"
    match state:
        case AsusOVPNClient.ON:
            service = f"start_vpn{party}{vpn_id}"
        case AsusOVPNClient.OFF:
            service = f"stop_vpn{party}{vpn_id}"
        case _:
            _LOGGER.debug("Unknown state %s", state)
            return False

    # Prepare the arguments
    arguments = {}

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
