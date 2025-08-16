"""Device module.

This module defines all device-related types, classes and functions.
"""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class DeviceOperationMode(FromIntMixin, IntEnum):
    """Types of device operation modes.

    Known modes
    ---
    - **ROUTER**
    - **REPEATER**
    - **ACCESS_POINT**
    - **MEDIA_BRIDGE**
    - **AIMESH_NODE**
    """

    UNKNOWN = UNKNOWN_MEMBER

    ROUTER = 1
    REPEATER = 2
    ACCESS_POINT = 3
    MEDIA_BRIDGE = 4
    AIMESH_NODE = 5
