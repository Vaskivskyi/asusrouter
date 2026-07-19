"""Tests for the LED enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.led.enums import ARLedField


@pytest.mark.parametrize("member", list(ARLedField), ids=lambda m: m.name)
def test_value_round_trips(member: ARLedField) -> None:
    """Every member resolves from its own stored value."""

    assert ARLedField.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARLedField.from_value("zzz-not-a-real-enum-value") is (
        ARLedField.UNKNOWN
    )
