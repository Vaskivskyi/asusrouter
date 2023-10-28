"""Parental control module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.tools.converters import safe_int, safe_return

KEY_PARENTAL_CONTROL_MAC = "MULTIFILTER_MAC"
KEY_PARENTAL_CONTROL_NAME = "MULTIFILTER_DEVICENAME"
KEY_PARENTAL_CONTROL_STATE = "MULTIFILTER_ALL"
KEY_PARENTAL_CONTROL_TIMEMAP = "MULTIFILTER_MACFILTER_DAYTIME_V2"
KEY_PARENTAL_CONTROL_TYPE = "MULTIFILTER_ENABLE"

MAP_PARENTAL_CONTROL_ITEM = [
    (KEY_PARENTAL_CONTROL_MAC, "mac", safe_return),
    (KEY_PARENTAL_CONTROL_NAME, "name", safe_return),
    (KEY_PARENTAL_CONTROL_TIMEMAP, "timemap", safe_return),
    (KEY_PARENTAL_CONTROL_TYPE, "type", safe_int),
]

MAP_PARENTAL_CONTROL_TYPE = {
    0: "disable",
    1: "time",
    2: "block",
}

DEFAULT_PARENTAL_CONTROL_TIMEMAP = "W03E21000700<W04122000800"


@dataclass(frozen=True)
class ParentalControlRule:
    """Parental control rule class."""

    mac: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    timemap: Optional[str] = DEFAULT_PARENTAL_CONTROL_TIMEMAP


class AsusParentalControl(IntEnum):
    """Asus parental control state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusParentalControl,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
) -> bool:
    """Set the parental control state."""

    # Check if arguments are available
    if not arguments:
        arguments = {}

    arguments[KEY_PARENTAL_CONTROL_STATE] = 1 if state == AsusParentalControl.ON else 0

    # Get the correct service call
    service = "restart_firewall"

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )
