"""Tests for the action base module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.action import ARAction, ARActionType


class _AltAction(ARAction):
    """A distinct action type (actions are equal by exact type)."""


class TestARActionType:
    """Tests for ARActionType."""

    def test_add_value(self) -> None:
        """ADD maps to its string value."""

        assert ARActionType.ADD.value == "add"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("add", ARActionType.ADD),
            ("clean", ARActionType.CLEAN),
            ("remove", ARActionType.REMOVE),
            ("other", ARActionType.UNKNOWN),
            (None, ARActionType.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARActionType) -> None:
        """from_value maps known strings, falls back to UNKNOWN."""

        assert ARActionType.from_value(value) == expected


def test_equal_by_type() -> None:
    """Actions are equal and hash alike when of the same exact type."""

    assert ARAction() == ARAction()
    assert hash(ARAction()) == hash(ARAction())


def test_not_equal_across_types() -> None:
    """Actions of different types are not equal."""

    assert ARAction() != _AltAction()
    assert ARAction().__eq__(object()) is NotImplemented


def test_repr() -> None:
    """The repr names the action type."""

    assert repr(_AltAction()) == "<_AltAction>"
