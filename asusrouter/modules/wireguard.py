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


def _get_arguments(**kwargs: Any) -> Optional[int]:
    """Get the arguments from kwargs."""

    arguments = kwargs.get("arguments", {})

    # Get the id from arguments
    wlan_id = arguments.get("id") if arguments else kwargs.get("id")
    if wlan_id is None:
        wlan_id = 1
        _LOGGER.debug("Using default id 1")

    return wlan_id


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusWireGuardClient | AsusWireGuardServer,
    **kwargs: Any,
) -> bool:
    """Set the WireGuard state."""

    # Get the arguments
    wlan_id = _get_arguments(**kwargs)

    # WireGuard unit type (server or client)
    wg_unit = "wgs" if isinstance(state, AsusWireGuardServer) else "wgc"

    # Callback arguments
    callback_arguments = {
        "id": wlan_id,
        f"{wg_unit}_enable": 1
        if state in (AsusWireGuardClient.ON, AsusWireGuardServer.ON)
        else 0,
        f"{wg_unit}_unit": wlan_id,
    }

    # Get the expect_modify argument
    expect_modify = kwargs.get("expect_modify", False)

    # Get the correct service call
    service_map: dict[Any, str] = {
        (AsusWireGuardClient, AsusWireGuardClient.ON): f"start_wgc {wlan_id}",
        (AsusWireGuardClient, AsusWireGuardClient.OFF): f"stop_wgc {wlan_id}",
        (AsusWireGuardServer, AsusWireGuardServer.ON): "restart_wgs;restart_dnsmasq",
        (AsusWireGuardServer, AsusWireGuardServer.OFF): "restart_wgs;restart_dnsmasq",
    }

    service = service_map.get((type(state), state))

    if not service:
        _LOGGER.debug("Unknown state %s", state)
        return False

    # Call the service
    return await callback(
        service=service,
        arguments=callback_arguments,
        apply=True,
        expect_modify=expect_modify,
    )
