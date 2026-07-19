"""Tests for the system status enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.system_status.enums import ARSystemType


@pytest.mark.parametrize("member", list(ARSystemType), ids=lambda m: m.name)
def test_value_round_trips(member: ARSystemType) -> None:
    """Every member resolves from its own stored value."""

    assert ARSystemType.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARSystemType.from_value("zzz-not-a-real-enum-value") is (
        ARSystemType.UNKNOWN
    )
