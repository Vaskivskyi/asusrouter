"""Tests for the firmware module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.firmware import (
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
)


class TestWebEnums:
    """Tests for the web-state enums."""

    @pytest.mark.parametrize(
        ("enum", "raw", "expected"),
        [
            (ARFirmwareWebError, "0", ARFirmwareWebError.NONE),
            (ARFirmwareWebError, "3", ARFirmwareWebError.FW_ERROR),
            (ARFirmwareWebError, "42", ARFirmwareWebError.UNKNOWN),
            (ARFirmwareWebFetch, "0", ARFirmwareWebFetch.ACTIVE),
            (ARFirmwareWebFetch, "1", ARFirmwareWebFetch.INACTIVE),
            (ARFirmwareWebNotify, "2", ARFirmwareWebNotify.FORCE),
            (ARFirmwareWebNotify, "", ARFirmwareWebNotify.UNKNOWN),
            (ARFirmwareWebUpgrade, "-1", ARFirmwareWebUpgrade.INACTIVE),
            (ARFirmwareWebUpgrade, "2", ARFirmwareWebUpgrade.ACTIVE),
        ],
    )
    def test_from_value(self, enum: Any, raw: str, expected: Any) -> None:
        """`from_value` maps known codes and falls back to UNKNOWN."""

        assert enum.from_value(raw) == expected
