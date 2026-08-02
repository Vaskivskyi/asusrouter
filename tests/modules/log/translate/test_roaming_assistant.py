"""Tests for the roaming assistant event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.roaming_assistant import (
    PATTERNS,
    AREventRoamingAssistant,
)
from asusrouter.tools.identifiers import MacAddress, WiFiInterface
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_NODE = "AA:BB:CC:00:00:01"
_CLIENT = "AA:BB:CC:00:00:02"
_CANDIDATE = (
    f"determine candidate node [{_NODE}](rssi: -46dbm) "
    f"for client [{_CLIENT}](rssi: -57dbm from client)"
    "(rssi: -71dbm from ap) to roam"
)
_ROAM = f"Roam a client [{_CLIENT}], status [0]"
_WEAK = f"wl0.2: disconnect weak signal strength station [{_CLIENT}]"
_REMOVE = f"wl0.2: remove client [{_CLIENT}] from monitor list"
_ALREADY = (
    f"[EXAP]Deauth old sta in wl0.2: {_CLIENT}, "
    f"because sta is already connected to {_NODE}."
)


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw roaming assistant message."""

    return PATTERNS.translate(content)


class TestCandidateSearch:
    """Candidate-search message translation."""

    def test_parses_fields(self) -> None:
        """Both MACs, all rssi values and the type are extracted."""

        assert _translate(_CANDIDATE) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.CANDIDATE_SEARCH,
            _KEY.RAW: classified(_CANDIDATE, IDENTIFIER),
            _KEY.NODE_MAC: MacAddress.from_value(_NODE),
            _KEY.NODE_RSSI: -46,
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.CLIENT_RSSI: -57,
            _KEY.AP_RSSI: -71,
        }

    def test_short_variant(self) -> None:
        """The single-rssi variant parses without an ap_rssi key."""

        short = (
            f"determine candidate node [{_NODE}](rssi: -10dbm) "
            f"for client [{_CLIENT}](rssi: -32dbm) to roam"
        )

        assert _translate(short) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.CANDIDATE_SEARCH,
            _KEY.RAW: classified(short, IDENTIFIER),
            _KEY.NODE_MAC: MacAddress.from_value(_NODE),
            _KEY.NODE_RSSI: -10,
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.CLIENT_RSSI: -32,
        }


class TestClientRoaming:
    """Client-roaming message translation."""

    def test_parses_fields(self) -> None:
        """The client MAC and status are extracted, no empty keys."""

        assert _translate(_ROAM) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.CLIENT_ROAMING,
            _KEY.RAW: classified(_ROAM, IDENTIFIER),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.STATUS: 0,
        }


class TestDeauthOldSta:
    """Deauth-old-sta translation (reason and node optional)."""

    def test_router_with_reason(self) -> None:
        """Router `wlX.Y` form with the reason keeps the connected-node MAC."""

        assert _translate(_ALREADY) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.DEAUTH_OLD_STA,
            _KEY.RAW: classified(_ALREADY, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 2),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.NODE_MAC: MacAddress.from_value(_NODE),
        }

    def test_node_without_reason(self) -> None:
        """Node `N N` form has no reason, so no node MAC key."""

        content = f"[EXAP]Deauth old sta in 0 2: {_CLIENT}"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.DEAUTH_OLD_STA,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 2),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }


class TestMonitoredClient:
    """Messages about a client on a monitored radio."""

    def test_disconnect_weak_signal(self) -> None:
        """The weak-signal disconnect keeps the wl id and client MAC."""

        assert _translate(_WEAK) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.DISCONNECT_WEAK_SIGNAL,
            _KEY.RAW: classified(_WEAK, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 2),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }

    def test_remove_client(self) -> None:
        """The monitor-list removal keeps the wl id and client MAC."""

        assert _translate(_REMOVE) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.REMOVE_CLIENT,
            _KEY.RAW: classified(_REMOVE, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 2),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }

    def test_sta_ap_band_bind_deauth(self) -> None:
        """The band-bind deauth keeps the wl id and client MAC."""

        content = f"wl0.2: sta-ap-band-bind deauth [{_CLIENT}]"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.STA_AP_BAND_BIND_DEAUTH,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 2),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }


class TestTranslateRoamingAssistant:
    """The per-program dispatcher."""

    def test_roaming_start(self) -> None:
        """The marker maps to ROAMING_START, no data keys."""

        content = "ROAMING Start"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.ROAMING_START,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future roamast message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRoamingAssistant.UNKNOWN,
            _KEY.RAW: unread(content),
        }
