"""Tests for the platform module."""

from __future__ import annotations

import pytest

from asusrouter.modules.platform import ARPlatform


@pytest.mark.parametrize("member", list(ARPlatform), ids=lambda m: m.name)
def test_value_round_trips(member: ARPlatform) -> None:
    """Every member resolves from its own stored value."""

    assert ARPlatform.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARPlatform.from_value("zzz-not-a-real-enum-value") is (
        ARPlatform.UNKNOWN
    )
