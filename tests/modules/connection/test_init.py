"""Tests for the connection module."""

from __future__ import annotations

import pytest

from asusrouter.modules.connection import ARConnection


@pytest.mark.parametrize("member", list(ARConnection), ids=lambda m: m.name)
def test_value_round_trips(member: ARConnection) -> None:
    """Every member resolves from its own stored value."""

    assert ARConnection.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARConnection.from_value("zzz-not-a-real-enum-value") is (
        ARConnection.UNKNOWN
    )
