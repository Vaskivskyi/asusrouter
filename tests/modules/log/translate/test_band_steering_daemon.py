"""Tests for the band steering daemon (bsd) event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.band_steering_daemon import (
    PATTERNS,
    AREventBandSteeringDaemon,
)
from asusrouter.tools.identifiers import MacAddress, WiFiInterface
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_CLIENT = "aa:bb:cc:00:00:01"
_BSSID = "aa:bb:cc:00:00:02"


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw band steering daemon message."""

    return PATTERNS.translate(content)


class TestActFrameSent:
    """The steering request."""

    def test_parses_radios_and_client(self) -> None:
        """Source radio, client and transition target are extracted."""

        content = (
            f"bsd: wl0.1 Sending act Frame to {_CLIENT} "
            f"with transition target wl1.1 ssid {_BSSID}"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.ACT_FRAME_SENT,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(0, 1),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
            _KEY.TARGET: WiFiInterface(1, 1),
        }

    def test_source_radio_optional(self) -> None:
        """Some builds omit the source radio, so no wl id is carried."""

        content = (
            f"bsd: Sending act Frame to {_CLIENT} "
            f"with transition target wl1.1 ssid {_BSSID}"
        )

        event = _translate(content)

        assert _KEY.WL_ID not in event
        assert event[_KEY.TARGET] == WiFiInterface(1, 1)


class TestTransitResponse:
    """Every shape of the transition response line."""

    def test_status_word(self) -> None:
        """The bare accept/reject form keeps the word."""

        content = "bsd: BSS Transit Response: STA reject"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            _KEY.RAW: content,
            _KEY.STATUS_TEXT: "reject",
        }

    def test_other_interface(self) -> None:
        """The not-for-interface form keeps the radio it was not for."""

        content = "bsd: BSS Transit Response: not for interface wl0.1"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            _KEY.RAW: content,
            _KEY.WL_ID: WiFiInterface(0, 1),
        }

    def test_detailed_form(self) -> None:
        """The detailed form keeps radio, status and client, not the flags."""

        content = (
            "bsd: BSS Transit Response: ifname=wl1.1, event=156, "
            f"token=e0, status=7, mac={_CLIENT}"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface(1, 1),
            _KEY.STATUS: 7,
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }

    def test_token_only_form(self) -> None:
        """The not-for-token form carries no field of known meaning."""

        content = "bsd: BSS Transit Response: not for token e4"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.TRANSIT_RESPONSE,
            _KEY.RAW: content,
        }


class TestStation:
    """Per-station outcomes."""

    def test_no_response(self) -> None:
        """A silent station is reported with its MAC."""

        content = f"bsd: STA:{_CLIENT} no response"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.STA_NO_RESPONSE,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }

    def test_skipped(self) -> None:
        """A skipped station is reported with its MAC."""

        content = f"bsd: Skip STA:{_CLIENT} reject BSSID"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.STA_SKIPPED,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.CLIENT_MAC: MacAddress.from_value(_CLIENT),
        }


class TestTranslateBandSteeringDaemon:
    """The per-program dispatcher."""

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "bsd: some future bsd message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventBandSteeringDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
