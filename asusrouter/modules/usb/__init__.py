"""USB module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class ARUSBGeneration(FromIntMixin, IntEnum):
    """USB generation types."""

    UNKNOWN = UNKNOWN_MEMBER

    USB = 1
    USB_2 = 2
    USB_3 = 3
