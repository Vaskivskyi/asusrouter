"""Wireless client event daemon log event translation."""

from __future__ import annotations

from enum import StrEnum
from functools import partial
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


class AREventWirelessClientDaemon(FromStrMixin, StrEnum):
    """Wireless client event daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ASSOC = "assoc"
    AUTH = "auth"
    DEAUTH = "deauth"
    DISASSOC = "disassoc"
    REASSOC = "reassoc"
    START = "start"


# Shared by both station messages
_STATION: dict[AREventKey, Callable[[str], Any]] = {
    AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
    AREventKey.RSSI: int,
    AREventKey.WL_ID: WiFiInterface.from_value_safe,
}

PATTERNS = ARLogPatternSet(
    AREventWirelessClientDaemon.UNKNOWN,
    (
        ARLogPattern(
            {
                "Assoc": AREventWirelessClientDaemon.ASSOC,
                "Auth": AREventWirelessClientDaemon.AUTH,
                "ReAssoc": AREventWirelessClientDaemon.REASSOC,
            },
            rf"{WL_PATTERN}:\s*(?P<event_type>Assoc|Auth|ReAssoc)\s+"
            rf"(?P<client_mac>{MAC_PATTERN}),"
            r"\s*status:\s*(?P<status_text>.+?)\s*\((?P<status>-?\d+)\),"
            r"\s*rssi:\s*(?P<rssi>-?\d+)",
            convert={**_STATION, AREventKey.STATUS: int},
            marker="status:",
        ),
        ARLogPattern(
            {
                "Deauth_ind": AREventWirelessClientDaemon.DEAUTH,
                "Disassoc": AREventWirelessClientDaemon.DISASSOC,
            },
            rf"{WL_PATTERN}:\s*(?P<event_type>Deauth_ind|Disassoc)\s+"
            rf"(?P<client_mac>{MAC_PATTERN}),"
            r"\s*status:\s*(?P<status>-?\d+),"
            r"\s*reason:\s*(?P<reason_text>.+?)\s*\((?P<reason>[0-9A-Fa-f]+)\),"
            r"\s*rssi:\s*(?P<rssi>-?\d+)",
            # The driver prints the reason code in hex
            convert={
                **_STATION,
                AREventKey.REASON: partial(int, base=16),
                AREventKey.STATUS: int,
            },
            marker="reason:",
        ),
        ARLogPattern(
            AREventWirelessClientDaemon.START,
            r"wlceventd Start",
            marker="wlceventd Start",
        ),
    ),
)
