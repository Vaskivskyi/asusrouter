"""Port forwarding module."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

KEY_PORT_FORWARDING_LIST = "vts_rulelist"
KEY_PORT_FORWARDING_STATE = "vts_enable_x"


@dataclass(frozen=True)
class PortForwardingRule:
    """Port forwarding class."""

    name: str = ""
    ip_address: str = ""
    port: str = ""
    protocol: str = ""
    ip_external: str = ""
    port_external: str = ""


class AsusPortForwarding(IntEnum):
    """Asus port forwarding state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusPortForwarding,
    **kwargs: Any,
) -> bool:
    """Set the parental control state."""

    # Check if state is available and valid
    if not isinstance(state, AsusPortForwarding) or state.value not in (0, 1):
        _LOGGER.debug("No state found in arguments")
        return False

    arguments = {
        KEY_PORT_FORWARDING_STATE: 1 if state == AsusPortForwarding.ON else 0
    }

    # Get the correct service call
    service = "restart_firewall"

    # Call the service
    return await callback(
        service=service,
        arguments=arguments,
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )
