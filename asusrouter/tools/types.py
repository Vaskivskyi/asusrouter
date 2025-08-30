"""Types tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ARCallbackType = Callable[..., Awaitable[Any]]
ARConverterType = Callable[..., Any]
