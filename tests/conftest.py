"""Fixtures for AsusRouter."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.connection import Connection
from asusrouter.modules.source import ARDataSource, ARDataStateDynamic
from tests.helpers import (
    TCONST_HOST,
    TCONST_PASS,
    TCONST_USER,
    AsyncPatch,
    BindStateFactory,
    ConnectionFactory,
    MakeStateFactory,
    SyncPatch,
    UniversalMockPatcher,
)


@pytest.fixture(name="connection_factory")
def connection_factory() -> ConnectionFactory:
    """Fixture to create a Connection object."""

    def _factory(**kwargs: Any) -> Connection:
        """Create a Connection object."""

        return Connection(
            hostname=TCONST_HOST,
            username=TCONST_USER,
            password=TCONST_PASS,
            **kwargs,
        )

    return _factory


@pytest.fixture
def universal_mock() -> Generator[UniversalMockPatcher, None, None]:
    """Fixture for a universal mock patcher."""

    patcher = UniversalMockPatcher()
    yield patcher
    patcher.stop()


@pytest.fixture(name="async_connect")
def mock_async_connect(
    universal_mock: UniversalMockPatcher,
) -> AsyncPatch:
    """Fixture to patch the `async_connect` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "async_connect", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="login")
def mock_login(
    universal_mock: UniversalMockPatcher,
) -> AsyncPatch:
    """Fixture to patch the `_login` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_login", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="fallback")
def mock_fallback(
    universal_mock: UniversalMockPatcher,
) -> AsyncPatch:
    """Fixture to patch the `_apply_fallback` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_apply_fallback", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="log_request")
def mock_log_request(
    universal_mock: UniversalMockPatcher,
) -> SyncPatch:
    """Fixture to patch the module-level `_log_request` function."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        patcher = patch("asusrouter.connection._log_request")
        mock = patcher.start()
        universal_mock.patches.append(patcher)
        if side_effect is not None:
            mock.side_effect = side_effect
        elif return_value is not None:
            mock.return_value = return_value
        return mock

    return _patch


@pytest.fixture(name="make_request")
def mock_make_request(
    universal_mock: UniversalMockPatcher,
) -> AsyncPatch:
    """Fixture to patch the `_make_request` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_make_request", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="new_session")
def mock_new_session(
    universal_mock: UniversalMockPatcher,
) -> SyncPatch:
    """Fixture to patch the `_new_session` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "_create_session", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="payload_for_logging")
def mock_payload_for_logging(
    universal_mock: UniversalMockPatcher,
) -> SyncPatch:
    """Fixture to patch the module-level `_payload_for_logging` function."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        patcher = patch("asusrouter.connection._payload_for_logging")
        mock = patcher.start()
        universal_mock.patches.append(patcher)
        if side_effect is not None:
            mock.side_effect = side_effect
        elif return_value is not None:
            mock.return_value = return_value
        return mock

    return _patch


@pytest.fixture(name="reset_auth")
def mock_reset_auth(
    universal_mock: UniversalMockPatcher,
) -> SyncPatch:
    """Fixture to patch the `reset_auth` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "reset_auth", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="send_request")
def mock_send_request(
    universal_mock: UniversalMockPatcher,
) -> AsyncPatch:
    """Fixture to patch the `_send_request` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_send_request", side_effect, return_value
        )

    return _patch


@pytest.fixture
def router() -> AsusRouter:
    """Provide a fresh AsusRouter instance for each test."""

    return AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
    )


@pytest.fixture
def source() -> ARDataSource:
    """Provide a fresh data source for each test."""

    return ARDataSource()


@pytest.fixture
def make_state() -> MakeStateFactory:
    """Create a state object with mocked update behavior."""

    def _make_state(
        source: ARDataSource,
        callback: Any = None,
        caller: Any = None,
        translator: Any = None,
        caller_multi: bool = False,
        translator_multi: bool = False,
    ) -> ARDataStateDynamic:
        state = ARDataStateDynamic(source)
        cast(Any, state).update = Mock()
        state.callback = callback
        state.state_caller = caller
        state.state_caller_multi = caller_multi
        state.translate_caller = translator
        state.translate_caller_multi = translator_multi
        return state

    return _make_state


@pytest.fixture
def bind_state(
    router: AsusRouter,
    make_state: MakeStateFactory,
) -> BindStateFactory:
    """Create a state and bind it to the router."""

    def _bind_state(
        source: ARDataSource,
        callback: Any = None,
        caller: Any = None,
        translator: Any = None,
        caller_multi: bool = False,
        translator_multi: bool = False,
    ) -> ARDataStateDynamic:
        state = make_state(
            source,
            callback=callback,
            caller=caller,
            translator=translator,
            caller_multi=caller_multi,
            translator_multi=translator_multi,
        )
        router._data_states[source] = state
        return state

    return _bind_state
