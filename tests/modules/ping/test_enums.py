"""Tests for the ping enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.ping.enums import ARPingStatus


@pytest.mark.parametrize("member", list(ARPingStatus), ids=lambda m: m.name)
def test_value_round_trips(member: ARPingStatus) -> None:
    """Every member resolves from its own stored value."""

    assert ARPingStatus.from_value(member.value) is member


def test_finished_code() -> None:
    """`3` maps to FINISHED."""

    assert ARPingStatus.from_value("3") is ARPingStatus.FINISHED


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARPingStatus.from_value("1") is ARPingStatus.UNKNOWN
