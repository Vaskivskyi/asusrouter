"""Tests for the NTP event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.ntp import PATTERNS, AREventNtp
from tests.modules.log.translate import unread

_KEY = AREventKey
_START = "start NTP update"


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw NTP message."""

    return PATTERNS.translate(content)


class TestTranslateNtp:
    """The per-program dispatcher."""

    def test_start_update(self) -> None:
        """The known message maps to START_UPDATE, no data keys."""

        assert _translate(_START) == {
            _KEY.EVENT_TYPE: AREventNtp.START_UPDATE,
            _KEY.RAW: _START,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future ntp message"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventNtp.UNKNOWN,
            _KEY.RAW: unread(content),
        }
