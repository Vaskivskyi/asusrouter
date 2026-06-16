"""AI module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARAICapability(FromStrMixin, StrEnum):
    """AI capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    RESET_BETA = "reset_beta"
    SLM = "slm"
    UPGRADE_BETA = "upgrade_beta"
