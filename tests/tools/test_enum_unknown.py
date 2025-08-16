"""Tests to ensure inherited enums define `UNKNOWN` members."""

from collections.abc import Iterator
from enum import Enum
import importlib
import inspect
import pkgutil

import pytest

from asusrouter.tools import enum as enum_tools


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
        pytest.fail(
            f"Found {total} enums inheriting mixins;"
            f"{len(missing)} missing UNKNOWN: " + ", ".join(missing)
        )

    # If nothing is missing, the test passes
