"""Tests for the action base module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.action import ARAction, ARActionType, async_start_run


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


class TestAsyncStartRun:
    """Tests for async_start_run."""

    @pytest.mark.asyncio
    async def test_no_callback(self) -> None:
        """Without a run callback the trigger fails."""

        assert await async_start_run(None, ARAction()) is False

    @pytest.mark.asyncio
    async def test_run_does_not_start(self) -> None:
        """A falsy run result drops the trigger."""

        callback = AsyncMock(return_value=False)
        assert await async_start_run(callback, ARAction(), delay=0) is False
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_starts(self) -> None:
        """A truthy run result starts the action after the delay."""

        action = ARAction()
        callback = AsyncMock(return_value=True)
        assert await async_start_run(callback, action, delay=0) is True
        callback.assert_awaited_once_with(action)
