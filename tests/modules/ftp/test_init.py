"""Tests for the FTP module."""

from __future__ import annotations

import pytest

from asusrouter.modules.ftp import ARFTPCapability


@pytest.mark.parametrize("member", list(ARFTPCapability), ids=lambda m: m.name)
def test_value_round_trips(member: ARFTPCapability) -> None:
    """Every member resolves from its own stored value."""

    assert ARFTPCapability.from_value(member.value) is member


def test_unknown_fallback() -> None:
    """An unrecognised value falls back to UNKNOWN."""

    assert ARFTPCapability.from_value("zzz-not-a-real-enum-value") is (
        ARFTPCapability.UNKNOWN
    )
