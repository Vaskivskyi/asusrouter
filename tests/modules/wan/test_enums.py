"""Tests for the WAN enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.wan.enums import ARDualWanMode, ARWANCapability

_ENUMS = [ARDualWanMode, ARWANCapability]
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


class TestARDualWanMode:
    """Explicit code mappings for ARDualWanMode."""

    def test_values(self) -> None:
        """Members map to their router codes."""

        assert ARDualWanMode.FAILOVER.value == "fo"
        assert ARDualWanMode.FALLBACK.value == "fb"
        assert ARDualWanMode.LOAD_BALANCE.value == "lb"
