"""Tests for the common internet-mode enum."""

from __future__ import annotations

from asusrouter.modules.common.internet import ARInternetMode


def test_values() -> None:
    """Members map to their string values."""

    assert ARInternetMode.ALLOW.value == "allow"
    assert ARInternetMode.BLOCK.value == "block"
    assert ARInternetMode.TIME.value == "time"


def test_from_value_unknown() -> None:
    """Unknown input resolves to UNKNOWN."""

    assert ARInternetMode.from_value("nope") is ARInternetMode.UNKNOWN
