"""Port forwarding module."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

KEY_PORT_FORWARDING_LIST = "vts_rulelist"
KEY_PORT_FORWARDING_STATE = "vts_enable_x"


@dataclass(frozen=True)
class PortForwardingRule:
    """Port forwarding class"""

    name: str = str()
    ip_address: str = str()
    port: str = str()
    protocol: str = str()
    ip_external: str = str()
    port_external: str = str()


class AsusPortForwarding(IntEnum):
    """Asus port forwarding state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusPortForwarding,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
) -> bool:
    """Set the parental control state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    arguments[KEY_PORT_FORWARDING_STATE] = 1 if state == AsusPortForwarding.ON else 0

    # Get the correct service call
    service = "restart_firewall"

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )
