"""LED module."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import IntEnum
from typing import Any

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.firmware import ARFirmwareType


class AsusLED(IntEnum):
    """Asus LED state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusLED,
    **kwargs: Any,
) -> bool:
    """Set the LED state."""

    # Prepare the arguments
    arguments = {"led_val": state.value}

    # Run the service
    return await callback(
        service="start_ctrl_led",
        arguments=arguments,
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )


async def keep_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusLED = AsusLED.ON,
    **kwargs: Any,
) -> bool:
    """Keep the LED state."""

    description = kwargs.get("identity") or ARDeviceIdentity()

    if description.firmware.firmware_type not in (
        ARFirmwareType.MERLIN,
        ARFirmwareType.GNUTON,
    ):
        return False

    if state == AsusLED.ON:
        return False

    # Toggle the LED
    await set_state(callback, AsusLED.ON, **kwargs)
    await set_state(callback, AsusLED.OFF, **kwargs)

    return True
