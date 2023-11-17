"""LED module."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.endpoint import Endpoint
from asusrouter.modules.identity import AsusDevice


class AsusLED(IntEnum):
    """Asus LED state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusLED,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
    _: Optional[dict[Any, Any]] = None,
) -> bool:
    """Set the LED state."""

    # Prepare the arguments
    arguments = {"led_val": state.value}

    # Run the service
    return await callback(
        service="start_ctrl_led",
        arguments=arguments,
        apply=True,
        expect_modify=expect_modify,
    )


async def keep_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusLED = AsusLED.ON,
    identity: Optional[AsusDevice] = None,
) -> bool:
    """Keep the LED state."""

    # Check if identity is available and if endpoints are defined
    if identity is None or not identity.endpoints:
        return False

    # Get the sysinfo
    sysinfo = identity.endpoints.get(Endpoint.SYSINFO)

    # Only when LEDs are off and if sysinfo is available
    if not sysinfo or state == AsusLED.ON:
        return False

    # Toggle the LED
    await set_state(callback, AsusLED.ON)
    await set_state(callback, AsusLED.OFF)

    return True
