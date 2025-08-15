"""Tests for the security tools."""

from typing import Any

import pytest

from asusrouter.tools.security import ARSecurityLevel


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("UNKNOWN", -999),
        ("STRICT", 0),
        ("DEFAULT", 1),
        ("SANITIZED", 5),
        ("UNSAFE", 9),
    ],
)
def test_enum_members_and_values(name: str, value: int) -> None:
    """Enum members exist and have the expected integer values."""

    member = getattr(ARSecurityLevel, name)
    assert member.name == name
    assert member.value == value


def test_ordering_comparisons() -> None:
    """Numeric ordering between levels behaves as expected."""

    assert ARSecurityLevel.STRICT < ARSecurityLevel.DEFAULT
    assert ARSecurityLevel.DEFAULT < ARSecurityLevel.SANITIZED
    assert ARSecurityLevel.SANITIZED < ARSecurityLevel.UNSAFE


def test_int_cast_and_lookup() -> None:
    """Casting from int and name lookup return the correct members."""

    assert ARSecurityLevel(1) is ARSecurityLevel.DEFAULT
    assert ARSecurityLevel["SANITIZED"] is ARSecurityLevel.SANITIZED


def test_unique_values() -> None:
    """Ensure all enum values are unique (mirrors @unique contract)."""

    values = [member.value for member in ARSecurityLevel]
    assert len(values) == len(set(values))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Real level already
        (ARSecurityLevel.DEFAULT, ARSecurityLevel.DEFAULT),
        # Int-compatible
        (1, ARSecurityLevel.DEFAULT),
        ("1", ARSecurityLevel.DEFAULT),
        ("5.0", ARSecurityLevel.SANITIZED),
        # Level which does not exist
        (861, ARSecurityLevel.UNKNOWN),
        # Name-compatible
        ("sanitized", ARSecurityLevel.SANITIZED),
        ("SANITIZED", ARSecurityLevel.SANITIZED),
        # Other
        (None, ARSecurityLevel.UNKNOWN),
        ("unknown-name", ARSecurityLevel.UNKNOWN),
        (object(), ARSecurityLevel.UNKNOWN),
    ],
)
def test_from_value(value: Any, expected: ARSecurityLevel) -> None:
    """Test ARSecurityLevel.from_value() with default behavior."""

    assert ARSecurityLevel.from_value(value) is expected
