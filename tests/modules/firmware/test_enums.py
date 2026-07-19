"""Tests for the firmware enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.firmware.enums import (
    ARFirmwareType,
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
)

_ENUMS = [
    ARFirmwareType,
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
]
_MEMBERS = [member for enum in _ENUMS for member in enum]


@pytest.mark.parametrize(
    "member", _MEMBERS, ids=lambda m: f"{type(m).__name__}.{m.name}"
)
def test_value_round_trips(member: Any) -> None:
    """Every member resolves from its own stored value."""

    assert type(member).from_value(member.value) is member


@pytest.mark.parametrize("enum", _ENUMS, ids=lambda e: e.__name__)
def test_unknown_fallback(enum: Any) -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert enum.from_value("zzz-not-a-real-enum-value") is enum.UNKNOWN


class TestWebEnumCodes:
    """Explicit code mappings for the web-state enums."""

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
