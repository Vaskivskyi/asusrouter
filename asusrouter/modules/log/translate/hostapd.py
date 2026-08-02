"""Host AP daemon (hostapd) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import MAC_PATTERN, WL_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress, WiFiInterface


class AREventHostapd(FromStrMixin, StrEnum):
    """Host AP daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    STA_ADD_FAILED = "sta_add_failed"


PATTERNS = ARLogPatternSet(
    AREventHostapd.UNKNOWN,
    (
        ARLogPattern(
            AREventHostapd.STA_ADD_FAILED,
            rf"{WL_PATTERN}: STA (?P<client_mac>{MAC_PATTERN}) "
            r"IEEE 802\.11: Could not add STA to kernel driver",
            convert={
                AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
                AREventKey.WL_ID: WiFiInterface.from_value_safe,
            },
            marker="Could not add STA to kernel driver",
        ),
    ),
)
