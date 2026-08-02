"""Tests for the disk monitor event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.disk_monitor import (
    PATTERNS,
    AREventDiskMonitor,
)
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw disk monitor message."""

    return PATTERNS.translate(content)


class TestTranslateDiskMonitor:
    """The per-program dispatcher."""

    def test_finish(self) -> None:
        """The marker maps to FINISH, no data keys."""

        assert _translate("Finish") == {
            _KEY.EVENT_TYPE: AREventDiskMonitor.FINISH,
            _KEY.RAW: "Finish",
        }

    def test_sigalrm(self) -> None:
        """The marker maps to SIGALRM, no data keys."""

        assert _translate("Got SIGALRM...") == {
            _KEY.EVENT_TYPE: AREventDiskMonitor.SIGALRM,
            _KEY.RAW: "Got SIGALRM...",
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future disk_monitor message"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventDiskMonitor.UNKNOWN,
            _KEY.RAW: unread(content),
        }
