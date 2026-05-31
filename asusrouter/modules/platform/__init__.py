"""Platform module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARPlatform(FromStrMixin, StrEnum):
    """Platform types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BROADCOM = "broadcom"
    LANTIQ = "lantiq"
    MEDIATEK = "mediatek"
    QUALCOMM = "qualcomm"
