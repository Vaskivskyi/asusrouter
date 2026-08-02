"""System init log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress, Serial


class AREventInit(FromStrMixin, StrEnum):
    """System init event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    FIRMWARE_BANNER = "firmware_banner"


PATTERNS = ARLogPatternSet(
    AREventInit.UNKNOWN,
    (
        ARLogPattern(
            AREventInit.FIRMWARE_BANNER,
            r"fwver: (?P<version>\S+)"
            r"(?: \(sn:(?P<device_serial>\S+)"
            r" /ha:(?P<device_mac>[0-9A-Fa-f:]+)\s*\))?",
            convert={
                AREventKey.DEVICE_MAC: MacAddress.from_value_safe,
                AREventKey.DEVICE_SERIAL: Serial.from_value_safe,
            },
            marker="fwver:",
        ),
    ),
)
