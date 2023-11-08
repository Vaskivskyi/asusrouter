"""WireGuard module."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

_LOGGER = logging.getLogger(__name__)


class AsusWireGuardClient(IntEnum):
    """Asus WireGuard client state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


class AsusWireGuardServer(IntEnum):
    """Asus WireGuard server state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusWireGuardClient | AsusWireGuardServer,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    _: Optional[Any] = None,
) -> bool:
    """Set the WireGuard state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    # Get the id from arguments
    arguments["id"] = arguments.get("id", 1)
    if arguments["id"] == 1:
        _LOGGER.debug("Using default id 1")

    wg_unit = "wgs" if isinstance(state, AsusWireGuardServer) else "wgc"

    arguments[f"{wg_unit}_enable"] = (
        1 if state in (AsusWireGuardClient.ON, AsusWireGuardServer.ON) else 0
    )
    arguments[f"{wg_unit}_unit"] = arguments["id"]

    # Get the correct service call
    service_map: dict[Any, str] = {
        (AsusWireGuardClient, AsusWireGuardClient.ON): f"start_wgc {arguments['id']}",
        (AsusWireGuardClient, AsusWireGuardClient.OFF): f"stop_wgc {arguments['id']}",
        (AsusWireGuardServer, AsusWireGuardServer.ON): "restart_wgs;restart_dnsmasq",
        (AsusWireGuardServer, AsusWireGuardServer.OFF): "restart_wgs;restart_dnsmasq",
    }

    service = service_map.get((type(state), state))

    if not service:
        _LOGGER.debug("Unknown state %s", state)
        return False

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )
