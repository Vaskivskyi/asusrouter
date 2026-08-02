"""WiFi scheduler log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import WiFiInterface

# The scheduler names a radio by its two indices instead of its `wl`
# token, and they are the same pair
_SEPARATOR = ", subunit="


class AREventWifiScheduler(FromStrMixin, StrEnum):
    """WiFi scheduler event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    RADIO_OFF = "radio_off"
    RADIO_ON = "radio_on"


def _radio(value: str) -> WiFiInterface | None:
    """Read `0, subunit=2` as the interface those indices name."""

    unit, _, subunit = value.partition(_SEPARATOR)

    return WiFiInterface.from_value_safe(f"{unit}.{subunit}")


PATTERNS = ARLogPatternSet(
    AREventWifiScheduler.UNKNOWN,
    (
        ARLogPattern(
            {
                "off": AREventWifiScheduler.RADIO_OFF,
                "on": AREventWifiScheduler.RADIO_ON,
            },
            rf"Turn radio \[band_index=(?P<wl_id>\d+{_SEPARATOR}\d+)\] "
            r"(?P<event_type>on|off)",
            convert={AREventKey.WL_ID: _radio},
            marker="Turn radio",
        ),
    ),
)
