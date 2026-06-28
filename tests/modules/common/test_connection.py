"""Tests for the common connection enum."""

from __future__ import annotations

from asusrouter.modules.common.connection import ARConnectionType


def test_values() -> None:
    """Members map to their string values."""

    assert ARConnectionType.WIRED.value == "wired"
    assert ARConnectionType.WIRELESS.value == "wireless"


def test_from_value_unknown() -> None:
    """Unknown input resolves to UNKNOWN."""

    assert ARConnectionType.from_value("nope") is ARConnectionType.UNKNOWN
