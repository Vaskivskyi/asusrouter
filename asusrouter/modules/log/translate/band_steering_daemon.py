"""Band steering daemon (bsd) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.common import MAC_PATTERN, WL_PATTERN
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress, WiFiInterface

if TYPE_CHECKING:
    from collections.abc import Callable


class AREventBandSteeringDaemon(FromStrMixin, StrEnum):
    """Band steering daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ACT_FRAME_SENT = "act_frame_sent"
    STA_NO_RESPONSE = "sta_no_response"
    STA_SKIPPED = "sta_skipped"
    TRANSIT_RESPONSE = "transit_response"


_CLIENT: dict[AREventKey, Callable[[str], Any]] = {
    AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
}
_RADIO: dict[AREventKey, Callable[[str], Any]] = {
    AREventKey.WL_ID: WiFiInterface.from_value_safe,
}

PATTERNS = ARLogPatternSet(
    AREventBandSteeringDaemon.UNKNOWN,
    (
        # The steering request itself; the trailing `ssid <mac>` is left
        # in the raw, the firmware label does not match its value
        ARLogPattern(
            AREventBandSteeringDaemon.ACT_FRAME_SENT,
            rf"(?:{WL_PATTERN}\s+)?Sending act Frame to "
            rf"(?P<client_mac>{MAC_PATTERN}) "
            r"with transition target (?P<target>wl[\d.]+)",
            convert={
                **_CLIENT,
                **_RADIO,
                AREventKey.TARGET: WiFiInterface.from_value_safe,
            },
            marker="Sending act Frame",
        ),
        ARLogPattern(
            AREventBandSteeringDaemon.STA_NO_RESPONSE,
            rf"STA:(?P<client_mac>{MAC_PATTERN}) no response",
            convert=_CLIENT,
            marker="no response",
        ),
        ARLogPattern(
            AREventBandSteeringDaemon.STA_SKIPPED,
            rf"Skip STA:(?P<client_mac>{MAC_PATTERN})",
            convert=_CLIENT,
            marker="Skip STA:",
        ),
        # `event` and `token` carry no confirmed meaning, so the detailed
        # form keeps only the fields that do
        ARLogPattern(
            AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            rf"BSS Transit Response: ifname={WL_PATTERN}.*?"
            r"status=(?P<status>\d+), "
            rf"mac=(?P<client_mac>{MAC_PATTERN})",
            convert={**_CLIENT, **_RADIO, AREventKey.STATUS: int},
            marker="BSS Transit Response",
        ),
        ARLogPattern(
            AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            r"BSS Transit Response: STA (?P<status_text>\w+)",
            marker="BSS Transit Response",
        ),
        # The token carries no confirmed meaning, so it stays in the raw
        ARLogPattern(
            AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            r"BSS Transit Response: not for token",
            marker="BSS Transit Response",
        ),
        ARLogPattern(
            AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            rf"BSS Transit Response: not for interface {WL_PATTERN}",
            convert=_RADIO,
            marker="BSS Transit Response",
        ),
    ),
)
