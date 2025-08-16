"""Tests for the enum tools."""

from enum import IntEnum, StrEnum
from typing import Any

import pytest

from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class FakeStrEnum(FromStrMixin, StrEnum):
    """String-based enum for testing."""

    UNKNOWN = "unknown_value"
    FOO = "foo_value"
    BAR = "bar_value"


class FakeStrEnumNoUnknown(FromStrMixin, StrEnum):
    """String-based enum for testing without unknown."""

    FOO = "foo_value"
    BAR = "bar_value"


class FakeIntEnum(FromIntMixin, IntEnum):
    """Integer-based enum for testing."""

    UNKNOWN = -999
    ONE = 1
    TWO = 2


class FakeIntEnumNoUnknown(FromIntMixin, IntEnum):
    """Integer-based enum for testing without unknown."""

    ONE = 1
    TWO = 2


@pytest.mark.parametrize(
    ("value", "member"),
    [
        (FakeStrEnum.FOO, FakeStrEnum.FOO),
        ("unknown_value", FakeStrEnum.UNKNOWN),
        ("  foo_value  ", FakeStrEnum.FOO),
        ("foo", FakeStrEnum.FOO),
        ("  bar  ", FakeStrEnum.BAR),
        ("none", FakeStrEnum.UNKNOWN),
        (None, FakeStrEnum.UNKNOWN),
        (123, FakeStrEnum.UNKNOWN),
        (object(), FakeStrEnum.UNKNOWN),
    ],
    ids=[
        "actual_enum",
        "from_correct_value",
        "from_parsed_value",
        "from_correct_key",
        "from_parsed_key",
        "not_value_not_key",
        "not_a_string",
        "wrong_type",
        "object",
    ],
)
def test_fromstr(value: Any, member: FakeStrEnum) -> None:
    """Test string-based enum resolution."""

    assert FakeStrEnum.from_value(value) is member


def test_fromstr_no_unknown() -> None:
    """Test string-based enum resolution without unknowns."""

    with pytest.raises(ValueError, match="no `UNKNOWN` member is defined"):
        FakeStrEnumNoUnknown.from_value("unknown_value")


@pytest.mark.parametrize(
    ("value", "member"),
    [
        (FakeIntEnum.ONE, FakeIntEnum.ONE),
        (1, FakeIntEnum.ONE),
        ("2", FakeIntEnum.TWO),
        ("one", FakeIntEnum.ONE),
        ("  two  ", FakeIntEnum.TWO),
        ("three", FakeIntEnum.UNKNOWN),
        (4, FakeIntEnum.UNKNOWN),
        (None, FakeIntEnum.UNKNOWN),
        ((1,), FakeIntEnum.UNKNOWN),
        (object(), FakeIntEnum.UNKNOWN),
    ],
    ids=[
        "actual_enum",
        "from_correct_value",
        "from_parsed_value",
        "from_correct_key",
        "from_parsed_key",
        "value_does_not_exist",
        "not_value_not_key",
        "not_compatible",
        "wrong_type",
        "object",
    ],
)
def test_fromint(value: Any, member: FakeIntEnum) -> None:
    """Test integer-based enum resolution."""

    assert FakeIntEnum.from_value(value) is member


def test_fromint_no_unknown() -> None:
    """Test integer-based enum resolution without unknowns."""

    with pytest.raises(ValueError, match="no `UNKNOWN` member is defined"):
        FakeIntEnumNoUnknown.from_value("unknown_value")
