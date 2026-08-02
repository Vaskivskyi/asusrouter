"""Tests for the host AP daemon (hostapd) event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.hostapd import PATTERNS, AREventHostapd
from asusrouter.tools.identifiers import MacAddress, WiFiInterface
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_MAC = "aa:bb:cc:3f:8d:15"
_ADD_FAILED = (
    f"wl0.1: STA {_MAC} IEEE 802.11: Could not add STA to kernel driver"
)


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw host AP daemon message."""

    return PATTERNS.translate(content)


class TestTranslateHostapd:
    """The per-program dispatcher."""

    def test_sta_add_failed(self) -> None:
        """The interface and client MAC are extracted."""

        assert _translate(_ADD_FAILED) == {
            _KEY.EVENT_TYPE: AREventHostapd.STA_ADD_FAILED,
            _KEY.RAW: classified(_ADD_FAILED, IDENTIFIER),
            _KEY.WL_ID: WiFiInterface.from_value("0.1"),
            _KEY.CLIENT_MAC: MacAddress.from_value(_MAC),
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "wl0.1: STA aa:bb:cc:3f:8d:15 IEEE 802.11: authenticated"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHostapd.UNKNOWN,
            _KEY.RAW: unread(content),
        }
