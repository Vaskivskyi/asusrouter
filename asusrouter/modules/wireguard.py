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
    state: AsusWireGuardServer,
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

    arguments["wgs_enable"] = 1 if state == AsusWireGuardServer.ON else 0
    arguments["wgs_unit"] = arguments["id"]

    # Get the correct service call
    service = "restart_wgs;restart_dnsmasq"

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )
