"""Tests for the LAN module."""

from __future__ import annotations

import pytest

from asusrouter.modules.lan import ARLANCapability


@pytest.mark.parametrize("member", list(ARLANCapability), ids=lambda m: m.name)
def test_value_round_trips(member: ARLANCapability) -> None:
    """Every member resolves from its own stored value."""

    assert ARLANCapability.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARLANCapability.from_value("zzz-not-a-real-enum-value") is (
        ARLANCapability.UNKNOWN
    )
