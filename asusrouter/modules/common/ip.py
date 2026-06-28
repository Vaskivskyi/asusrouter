"""Common IP module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARIPMethod(FromStrMixin, StrEnum):
    """Method of obtaining IP address."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DHCP = "dhcp"
    MANUAL = "manual"
