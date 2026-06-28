"""Tests for the common IP enum."""

from __future__ import annotations

from asusrouter.modules.common.ip import ARIPMethod


def test_values() -> None:
    """Members map to their string values."""

    assert ARIPMethod.DHCP.value == "dhcp"
    assert ARIPMethod.MANUAL.value == "manual"


def test_from_value_unknown() -> None:
    """Unknown input resolves to UNKNOWN."""

    assert ARIPMethod.from_value("nope") is ARIPMethod.UNKNOWN
