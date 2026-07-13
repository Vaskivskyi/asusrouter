"""System status enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARSystemType(FromStrMixin, StrEnum):
    """A system component reported in the status."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CORE_1 = "core_1"
    CORE_2 = "core_2"
    CORE_3 = "core_3"
    CORE_4 = "core_4"
    CORE_5 = "core_5"
    CORE_6 = "core_6"
    CORE_7 = "core_7"
    CORE_8 = "core_8"
    CPU = "cpu"
    RAM = "ram"


__all__ = [
    "ARSystemType",
]
