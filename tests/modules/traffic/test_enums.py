"""Tests for the traffic enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.traffic.enums import ARTrafficType


@pytest.mark.parametrize("member", list(ARTrafficType), ids=lambda m: m.name)
def test_value_round_trips(member: ARTrafficType) -> None:
    """Every member resolves from its own stored value."""

    assert ARTrafficType.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARTrafficType.from_value("zzz-not-a-real-enum-value") is (
        ARTrafficType.UNKNOWN
    )
