"""Tests for the kernel module loader event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.modprobe import PATTERNS, AREventModprobe
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw modprobe message."""

    return PATTERNS.translate(content)


class TestTranslateModprobe:
    """The per-program dispatcher."""

    def test_module_not_found(self) -> None:
        """The module the loader could not find is extracted."""

        content = "module scsi_wait_scan not found in modules.dep"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventModprobe.MODULE_NOT_FOUND,
            _KEY.RAW: content,
            _KEY.MODULE: "scsi_wait_scan",
        }

    def test_dashed_module(self) -> None:
        """A module name holding a dash is read whole."""

        content = "module ledtrig-usbdev not found in modules.dep"

        assert _translate(content)[_KEY.MODULE] == "ledtrig-usbdev"

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future modprobe message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventModprobe.UNKNOWN,
            _KEY.RAW: unread(content),
        }
