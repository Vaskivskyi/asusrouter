"""Roaming assistant (roamast) log event translation for AsusRouter."""

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


class AREventRoamingAssistant(FromStrMixin, StrEnum):
    """Roaming assistant event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CANDIDATE_SEARCH = "candidate_search"
    CLIENT_ROAMING = "client_roaming"
    DEAUTH_OLD_STA = "deauth_old_sta"
    DISCONNECT_WEAK_SIGNAL = "disconnect_weak_signal"
    REMOVE_CLIENT = "remove_client"
    ROAMING_START = "roaming_start"
    STA_AP_BAND_BIND_DEAUTH = "sta_ap_band_bind_deauth"


# A client seen on a monitored radio
_CLIENT = {
    AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
    AREventKey.WL_ID: WiFiInterface.from_value_safe,
}

PATTERNS = ARLogPatternSet(
    AREventRoamingAssistant.UNKNOWN,
    (
        ARLogPattern(
            AREventRoamingAssistant.CANDIDATE_SEARCH,
            rf"determine candidate node \[(?P<node_mac>{MAC_PATTERN})\]"
            r"\s*\(rssi:\s*(?P<node_rssi>-?\d+)\s*dbm\)"
            rf"\s*for client \[(?P<client_mac>{MAC_PATTERN})\]"
            r"\s*\(rssi:\s*(?P<client_rssi>-?\d+)\s*dbm"
            r"(?:\s*from client\)\s*\(rssi:\s*(?P<ap_rssi>-?\d+)\s*dbm"
            r"\s*from ap)?\)",
            convert={
                AREventKey.AP_RSSI: int,
                AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
                AREventKey.CLIENT_RSSI: int,
                AREventKey.NODE_MAC: MacAddress.from_value_safe,
                AREventKey.NODE_RSSI: int,
            },
            marker="determine candidate node",
        ),
        ARLogPattern(
            AREventRoamingAssistant.CLIENT_ROAMING,
            rf"Roam a client \[(?P<client_mac>{MAC_PATTERN})\],"
            r"\s*status \[(?P<status>-?\d+)\]",
            convert={
                AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
                AREventKey.STATUS: int,
            },
            marker="Roam a client",
        ),
        # Older builds print the radio as a bare `<unit> <subunit>` pair
        ARLogPattern(
            AREventRoamingAssistant.DEAUTH_OLD_STA,
            r"Deauth old sta in (?P<wl_id>wl[\d.]+|\d+ \d+):"
            rf"\s*(?P<client_mac>{MAC_PATTERN})"
            r"(?:,\s*because sta is already connected to "
            rf"(?P<node_mac>{MAC_PATTERN}))?",
            convert={
                **_CLIENT,
                AREventKey.NODE_MAC: MacAddress.from_value_safe,
            },
            marker="Deauth old sta in",
        ),
        ARLogPattern(
            AREventRoamingAssistant.DISCONNECT_WEAK_SIGNAL,
            rf"{WL_PATTERN}:\s*disconnect weak signal strength station "
            rf"\[(?P<client_mac>{MAC_PATTERN})\]",
            convert=_CLIENT,
            marker="disconnect weak signal strength station",
        ),
        ARLogPattern(
            AREventRoamingAssistant.REMOVE_CLIENT,
            rf"{WL_PATTERN}:\s*remove client "
            rf"\[(?P<client_mac>{MAC_PATTERN})\] from monitor list",
            convert=_CLIENT,
            marker="from monitor list",
        ),
        ARLogPattern(
            AREventRoamingAssistant.ROAMING_START,
            r"ROAMING Start",
            marker="ROAMING Start",
        ),
        ARLogPattern(
            AREventRoamingAssistant.STA_AP_BAND_BIND_DEAUTH,
            rf"{WL_PATTERN}:\s*sta-ap-band-bind deauth "
            rf"\[(?P<client_mac>{MAC_PATTERN})\]",
            convert=_CLIENT,
            marker="sta-ap-band-bind deauth",
        ),
    ),
)
