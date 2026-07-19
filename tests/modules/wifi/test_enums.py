"""Tests for the WiFi enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.wifi.enums import (
    ARWiFiAuth,
    ARWiFiAuthMode,
    ARWiFiBand,
    ARWiFiBandwidth,
    ARWiFiField,
    ARWiFiFrequency,
    ARWiFiGeneration,
    ARWiFiMacFilterMode,
    ARWiFiMultiBand,
)

_ENUMS = [
    ARWiFiAuth,
    ARWiFiAuthMode,
    ARWiFiBand,
    ARWiFiBandwidth,
    ARWiFiField,
    ARWiFiFrequency,
    ARWiFiGeneration,
    ARWiFiMacFilterMode,
    ARWiFiMultiBand,
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


class TestARWiFiBandFromNband:
    """Tests for ARWiFiBand.from_nband."""

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("1", ARWiFiBand.BAND_5G1),
            ("2", ARWiFiBand.BAND_2G1),
            ("4", ARWiFiBand.BAND_6G1),
            ("9", ARWiFiBand.UNKNOWN),
            ("", ARWiFiBand.UNKNOWN),
            (None, ARWiFiBand.UNKNOWN),
        ],
    )
    def test_from_nband(self, code: str | None, expected: ARWiFiBand) -> None:
        """A Broadcom nband radio code maps to its band."""

        assert ARWiFiBand.from_nband(code) is expected
