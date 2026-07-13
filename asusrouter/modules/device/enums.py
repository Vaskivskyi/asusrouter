"""Device enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


# TODO: Redo this legacy class
class DeviceOperationMode(FromIntMixin, IntEnum):
    """Types of device operation modes."""

    UNKNOWN = UNKNOWN_MEMBER

    ROUTER = 1
    REPEATER = 2
    ACCESS_POINT = 3
    MEDIA_BRIDGE = 4
    AIMESH_NODE = 5


__all__ = [
    "DeviceOperationMode",
]
