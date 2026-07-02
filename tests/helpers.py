"""Helpers for unit test modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast
from unittest.mock import AsyncMock, Mock, patch

from asusrouter.connection import Connection
from asusrouter.modules.source import ARDataSource, ARDataStateDynamic

AsyncPatch = Callable[..., AsyncMock]
SyncPatch = Callable[..., Mock]
ConnectionFactory = Callable[..., Connection]


class MakeStateFactory(Protocol):
    """Callable that creates a state object with mocked update behavior."""

    def __call__(
        self,
        source: ARDataSource,
        callback: Any = None,
        caller: Any = None,
        translator: Any = None,
        caller_multi: bool = False,
        translator_multi: bool = False,
    ) -> ARDataStateDynamic:
        """Create a state object with mocked update behavior."""
        ...


class BindStateFactory(Protocol):
    """Callable that creates a state and binds it to the router."""

    def __call__(
        self,
        source: ARDataSource,
        callback: Any = None,
        caller: Any = None,
        translator: Any = None,
        caller_multi: bool = False,
        translator_multi: bool = False,
    ) -> ARDataStateDynamic:
        """Create a state and bind it to the router."""
        ...


class UniversalMockPatcher:
    """Universal mock patcher for async methods."""

    def __init__(self) -> None:
        """Initialize the UniversalMockPatcher."""

        self.patches: list[Any] = []

    def patch(
        self,
        obj: Any,
        method_name: str,
        side_effect: Any = None,
        return_value: Any = None,
        mock_type: type = AsyncMock,
    ) -> AsyncMock | Mock:
        """Patch a method on the provided object."""

        patcher = patch.object(obj, method_name, new_callable=mock_type)
        mock_method = patcher.start()
        self.patches.append(patcher)
        if side_effect is not None:
            mock_method.side_effect = side_effect
        elif return_value is not None:
            mock_method.return_value = return_value
        return mock_method

    def stop(self) -> None:
        """Stop all patches."""

        for patcher in self.patches:
            patcher.stop()


def assert_state_updated(
    state: ARDataStateDynamic, expected_update: Any
) -> None:
    """Assert the state update method was called with the expected payload."""

    cast(Mock, state.update).assert_called_once_with(expected_update)


def assert_state_not_updated(state: ARDataStateDynamic) -> None:
    """Assert the state update method was not called."""

    cast(Mock, state.update).assert_not_called()


TCONST_HOST = "localhost"
TCONST_USER = "user"
TCONST_PASS = "pass"
