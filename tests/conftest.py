"""Fixtures for AsusRouter."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from asusrouter.connection import Connection
from tests.helpers import (
    TCONST_HOST,
    TCONST_PASS,
    TCONST_USER,
    AsyncPatch,
    ConnectionFactory,
    SyncPatch,
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


@pytest.fixture
def universal_mock() -> Generator[UniversalMockPatcher, None, None]:
    """Fixture for a universal mock patcher."""

    patcher = UniversalMockPatcher()
    yield patcher
    patcher.stop()


@pytest.fixture(name="async_connect")
def mock_async_connect(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> AsyncPatch:
    """Fixture to patch the `async_connect` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "async_connect", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="async_connect_with_lock")
def mock_async_connect_with_lock(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> AsyncPatch:
    """Fixture to patch the `_async_connect_with_lock` method with a lock."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_async_connect_with_lock", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="fallback")
def mock_fallback(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> AsyncPatch:
    """Fixture to patch the `_fallback` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_fallback", side_effect, return_value
        )

    return _patch


@pytest.fixture(name="log_request")
def mock_log_request(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> SyncPatch:
    """Fixture to patch the `_log_request` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "_log_request", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="make_request")
def mock_make_request(
    universal_mock: UniversalMockPatcher,  # noqa: F811
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
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> SyncPatch:
    """Fixture to patch the `_new_session` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "_new_session", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="payload_for_logging")
def mock_payload_for_logging(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> SyncPatch:
    """Fixture to patch the `_payload_for_logging` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "_payload_for_logging", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="reset_connection")
def mock_reset_connection(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> SyncPatch:
    """Fixture to patch the `reset_connection` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> Mock:
        return universal_mock.patch(
            connection, "reset_connection", side_effect, return_value, Mock
        )

    return _patch


@pytest.fixture(name="send_request")
def mock_send_request(
    universal_mock: UniversalMockPatcher,  # noqa: F811
) -> AsyncPatch:
    """Fixture to patch the `_send_request` method."""

    def _patch(
        connection: Any, side_effect: Any = None, return_value: Any = None
    ) -> AsyncMock:
        return universal_mock.patch(
            connection, "_send_request", side_effect, return_value
        )

    return _patch
