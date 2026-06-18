"""USB ports module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class ARPortUSBSpeed(FromIntMixin, IntEnum):
    """USB port speed."""

    UNKNOWN = UNKNOWN_MEMBER

    DOWN = 0
    USB2 = 480
    USB3 = 5000
    USB3_1 = 10000
    USB3_2 = 20000
