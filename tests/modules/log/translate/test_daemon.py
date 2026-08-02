"""Tests for the shared daemon lifecycle event translation."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.daemon import PATTERNS, AREventDaemon
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw daemon lifecycle message."""

    return PATTERNS.translate(content)


class TestTranslateDaemon:
    """The pattern set shared by the service daemons."""

    @pytest.mark.parametrize(
        ("content", "event"),
        [
            ("daemon is started", AREventDaemon.STARTED),
            ("daemon is stopped", AREventDaemon.STOPPED),
            ("smb daemon is stopped", AREventDaemon.STOPPED),
            # The firmware misspells it on some daemons
            ("daemon is stoped", AREventDaemon.STOPPED),
        ],
    )
    def test_lifecycle(self, content: str, event: str) -> None:
        """Every observed wording maps to the state it reports."""

        assert _translate(content) == {
            _KEY.EVENT_TYPE: event,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future daemon message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
