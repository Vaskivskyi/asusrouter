"""Tests for the cron event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.cron import PATTERNS, AREventCron
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw cron message."""

    return PATTERNS.translate(content)


class TestTranslateCron:
    """The per-program dispatcher."""

    def test_time_disparity(self) -> None:
        """The disparity in minutes is extracted."""

        content = "time disparity of 1191748 minutes detected"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventCron.TIME_DISPARITY,
            _KEY.RAW: content,
            _KEY.MINUTES: 1191748,
        }

    def test_negative_disparity(self) -> None:
        """A backwards clock jump keeps the sign."""

        content = "time disparity of -42 minutes detected"

        assert _translate(content)[_KEY.MINUTES] == -42

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future crond message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventCron.UNKNOWN,
            _KEY.RAW: unread(content),
        }
