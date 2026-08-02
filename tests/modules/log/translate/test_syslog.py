"""Tests for the syslog daemon event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.syslog import PATTERNS, AREventSyslog
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw syslog daemon message."""

    return PATTERNS.translate(content)


class TestTranslateSyslog:
    """The per-program dispatcher."""

    def test_started(self) -> None:
        """The BusyBox version is extracted."""

        content = "syslogd started: BusyBox v1.25.1"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventSyslog.STARTED,
            _KEY.RAW: content,
            _KEY.VERSION: "1.25.1",
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future syslogd message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventSyslog.UNKNOWN,
            _KEY.RAW: unread(content),
        }
