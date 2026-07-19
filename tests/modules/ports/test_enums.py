"""Tests for the ports enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.ports.enums import (
    ARPortCablePair,
    ARPortCapability,
    ARPortProperty,
    ARPortsInfo,
    ARPortSpeed,
    ARPortType,
)

_ENUMS = [
    ARPortCablePair,
    ARPortCapability,
    ARPortProperty,
    ARPortSpeed,
    ARPortsInfo,
    ARPortType,
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


class TestARPortSpeed:
    """Explicit Mbps-to-grade mappings for ARPortSpeed."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, ARPortSpeed.DOWN),
            (10, ARPortSpeed.MBPS_10),
            (100, ARPortSpeed.MBPS_100),
            (1000, ARPortSpeed.MBPS_1000),
            (2500, ARPortSpeed.MBPS_2500),
            (5000, ARPortSpeed.MBPS_5000),
            (10000, ARPortSpeed.MBPS_10000),
            (999, ARPortSpeed.UNKNOWN),
            (-1, ARPortSpeed.UNKNOWN),
        ],
    )
    def test_from_value(self, value: int, expected: ARPortSpeed) -> None:
        """ARPortSpeed.from_value maps Mbps to the speed grade."""

        assert ARPortSpeed.from_value(value) == expected
