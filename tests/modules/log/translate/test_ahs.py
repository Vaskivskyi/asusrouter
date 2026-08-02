"""Tests for the ahs daemon event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.ahs import PATTERNS, AREventAhs
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw ahs message."""

    return PATTERNS.translate(content)


class TestTranslateAhs:
    """The per-program dispatcher."""

    def test_json_update(self) -> None:
        """The periodic JSON write is recognized."""

        content = "[read_json]Update ahs JSON file."

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAhs.JSON_UPDATE,
            _KEY.RAW: content,
        }

    def test_terminate(self) -> None:
        """The shutdown line is recognized."""

        content = "===Terminate ahs daemon==="

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAhs.TERMINATE,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future ahs message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAhs.UNKNOWN,
            _KEY.RAW: unread(content),
        }
