"""Tests for the action base module."""

from __future__ import annotations

from asusrouter.modules.action import ARAction


class _AltAction(ARAction):
    """A distinct action type (actions are equal by exact type)."""


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
