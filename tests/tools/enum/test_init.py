"""Tests for the enum tools."""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum, IntEnum, StrEnum
import importlib
import inspect
import pkgutil
from typing import Any

import pytest

from asusrouter.tools import enum as enum_tools
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


def _iter_enum_classes() -> Iterator[type[Enum]]:
    """Yield all enum classes in the asusrouter package.

    Check the ones inheriting our mixins.
    """

    # Clear any previous failed imports
    if hasattr(_iter_enum_classes, "_failed_imports"):
        delattr(_iter_enum_classes, "_failed_imports")

    failed_imports: list[tuple[str, str]] = []

    # Import package modules under asusrouter
    package = importlib.import_module("asusrouter")
    for finder, name, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        # Import module
        try:
            mod = importlib.import_module(name)
        except ImportError as ex:
            # Record failed imports
            failed_imports.append((name, repr(ex)))
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            try:
                if issubclass(obj, Enum) and (
                    issubclass(obj, enum_tools.FromIntMixin)
                    or issubclass(obj, enum_tools.FromStrMixin)
                ):
                    yield obj
            except TypeError:
                # Not compatible with issubclass; skip
                continue

    # If any imports failed, attach them to the generator function
    if failed_imports:
        # attach a list for later inspection
        setattr(_iter_enum_classes, "_failed_imports", failed_imports)


def test_enums_define_unknown() -> None:
    """Test to ensure all enums define an UNKNOWN member."""

    enums = list(_iter_enum_classes())
    total = len(enums)

    # If any imports failed, report them
    failed = getattr(_iter_enum_classes, "_failed_imports", None)
    if failed:
        details = "; ".join(f"{mod} -> {err}" for mod, err in failed)
        pytest.fail(
            f"Some modules failed to import during discovery: {details}"
        )

    # Explicit report if nothing was found (likely a discovery/import issue)
    assert total > 0, (
        "No enums inheriting FromIntMixin/FromStrMixin "
        "were discovered in the package"
    )

    missing = [
        f"{enum_cls.__module__}.{enum_cls.__name__}"
        for enum_cls in enums
        if not hasattr(enum_cls, "UNKNOWN")
    ]

    if missing:
        # Skip  generic base classes (`ARDataType`)
        missing = [m for m in missing if not m.endswith("ARDataType")]

        if len(missing) == 0:
            return

        pytest.fail(
            f"Found {total} enums inheriting mixins;"
            f"{len(missing)} missing UNKNOWN: " + ", ".join(missing)
        )

    # If nothing is missing, the test passes
