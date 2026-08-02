"""Tests for the wireless client event daemon event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.wireless_client_daemon import (
    PATTERNS,
    AREventWirelessClientDaemon,
)
from asusrouter.tools.identifiers import MacAddress, WiFiInterface
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_CLIENT = "AA:BB:CC:00:00:01"
_PREFIX = "wlceventd_proc_event(722):"
_AUTH = f"{_PREFIX} wl0.1: Auth {_CLIENT}, status: Successful (0), rssi:0"
_DEAUTH = (
    f"{_PREFIX} wl0.1: Deauth_ind {_CLIENT}, status: 0, "
    "reason: Deauthenticated because sending station is leaving "
    "(or has left) IBSS or ESS (3), rssi:-55"
)


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw wireless client daemon message."""

    return PATTERNS.translate(content)


class TestConnect:
    """Auth/assoc/reassoc message translation."""

    def test_assoc(self) -> None:
        """Assoc parses wl id, MAC, status and rssi."""

        content = (
            f"{_PREFIX} wl2.1: Assoc {_CLIENT}, "
            "status: Successful (0), rssi:-42"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.ASSOC,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(2, 1),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.STATUS: 0,
            _KEY.STATUS_TEXT: "Successful",
            _KEY.RSSI: -42,
        }

    def test_auth(self) -> None:
        """Auth maps to the AUTH event type."""

        assert _translate(_AUTH) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.AUTH,
            _KEY.RAW: classified(_AUTH, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 1),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.STATUS: 0,
            _KEY.STATUS_TEXT: "Successful",
            _KEY.RSSI: 0,
        }

    def test_reassoc(self) -> None:
        """ReAssoc maps to the REASSOC event type."""

        content = (
            f"{_PREFIX} wl0.1: ReAssoc {_CLIENT}, "
            "status: Successful (0), rssi:-47"
        )

        assert (
            _translate(content)[_KEY.EVENT_TYPE]
            is AREventWirelessClientDaemon.REASSOC
        )


class TestDisconnect:
    """Deauth/disassoc message translation."""

    def test_deauth(self) -> None:
        """Deauth_ind keeps the reason text and its parenthesised code."""

        assert _translate(_DEAUTH) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.DEAUTH,
            _KEY.RAW: classified(_DEAUTH, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 1),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.STATUS: 0,
            _KEY.REASON: 3,
            _KEY.REASON_TEXT: (
                "Deauthenticated because sending station is leaving "
                "(or has left) IBSS or ESS"
            ),
            _KEY.RSSI: -55,
        }

    def test_disassoc(self) -> None:
        """Disassoc maps to the DISASSOC event type."""

        content = (
            f"{_PREFIX} wl2.1: Disassoc {_CLIENT}, status: 0, "
            "reason: Unspecified reason (1), rssi:0"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.DISASSOC,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(2, 1),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.STATUS: 0,
            _KEY.REASON: 1,
            _KEY.REASON_TEXT: "Unspecified reason",
            _KEY.RSSI: 0,
        }

    def test_reason_hex_code(self) -> None:
        """The parenthesised reason code is hexadecimal (`f` -> 15)."""

        content = (
            f"{_PREFIX} wl0.1: Deauth_ind {_CLIENT}, status: 0, "
            "reason: 4-way handshake timeout (f), rssi:-46"
        )

        event = _translate(content)

        assert event[_KEY.REASON] == 15
        assert event[_KEY.REASON_TEXT] == "4-way handshake timeout"

    def test_reason_unmapped(self) -> None:
        """An unmapped reason keeps the UNKNOWN text and its hex code."""

        content = (
            f"{_PREFIX} wl0.1: Deauth_ind {_CLIENT}, status: 0, "
            "reason: UNKNOWN (7b7c), rssi:-68"
        )

        event = _translate(content)

        assert event[_KEY.REASON] == 0x7B7C
        assert event[_KEY.REASON_TEXT] == "UNKNOWN"


class TestTranslateWirelessClientDaemon:
    """The per-program dispatcher."""

    def test_start(self) -> None:
        """The marker maps to START, no data keys (line prefix ignored)."""

        content = "main(1239): wlceventd Start..."

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.START,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future wlceventd message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWirelessClientDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
