"""Tests for the firmware release note reader."""

from __future__ import annotations

import pytest

from asusrouter.modules.firmware.note import read_firmware_note
from asusrouter.tools.converters.raw import _BOM


class TestReadFirmwareNote:
    """Tests for read_firmware_note."""

    def test_strips_headers_and_bom(self) -> None:
        """The BOM and header lines are stripped, change lines kept."""

        content = (
            f"{_BOM}Firmware version 3.0.0.4\nRelease Note\n- Fix A\n- Fix B\n"
        )
        assert read_firmware_note(content) == "- Fix A\n- Fix B"

    @pytest.mark.parametrize(
        "content",
        [
            "",
            "\n\n",
            "   \n  \n",
            "Firmware version 1\nRelease Note\n",
        ],
    )
    def test_empty_returns_none(self, content: str) -> None:
        """Empty or header-only notes return None."""

        assert read_firmware_note(content) is None
