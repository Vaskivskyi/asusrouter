"""Tests for the credentials enums."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.credentials.enums import ARCredentialsStatus

_ENUMS = [ARCredentialsStatus]
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


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("200", ARCredentialsStatus.SUCCESS),
        ("401", ARCredentialsStatus.WRONG_PASSWORD),
        ("402", ARCredentialsStatus.LOCKED_OUT),
    ],
)
def test_status_from_device_code(
    code: Any, expected: ARCredentialsStatus
) -> None:
    """The device statusCode maps to the matching status."""

    assert ARCredentialsStatus.from_value(code) is expected
