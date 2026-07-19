"""Tests for the temperature enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.temperature.enums import ARTemperatureType


@pytest.mark.parametrize(
    "member", list(ARTemperatureType), ids=lambda m: m.name
)
def test_value_round_trips(member: ARTemperatureType) -> None:
    """Every member resolves from its own stored value."""

    assert ARTemperatureType.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARTemperatureType.from_value("zzz-not-a-real-enum-value") is (
        ARTemperatureType.UNKNOWN
    )
