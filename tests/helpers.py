"""Helpers for unit test modules."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock, Mock

from asusrouter.connection import Connection

AsyncPatch = Callable[..., AsyncMock]
SyncPatch = Callable[..., Mock]
ConnectionFactory = Callable[..., Connection]


TCONST_HOST = "localhost"
TCONST_USER = "user"
TCONST_PASS = "pass"  # noqa: S105
