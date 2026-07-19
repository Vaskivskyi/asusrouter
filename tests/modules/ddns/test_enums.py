"""Tests for the DDNS enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.ddns.enums import (
    ARDdnsCommand,
    ARDdnsField,
    ARDdnsServer,
    ARDdnsStatus,
)

_ENUMS = [ARDdnsCommand, ARDdnsField, ARDdnsServer, ARDdnsStatus]
# An empty-string value (e.g. ARDdnsStatus.NONE) is a sentinel: it cannot be
# resolved back through from_value, which treats blank input as UNKNOWN
_MEMBERS = [member for enum in _ENUMS for member in enum if member.value != ""]


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


def test_blank_status_is_unknown() -> None:
    """The blank NONE status value resolves to UNKNOWN."""

    assert ARDdnsStatus.NONE.value == ""
    assert ARDdnsStatus.from_value("") is ARDdnsStatus.UNKNOWN
