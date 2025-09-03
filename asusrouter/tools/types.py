"""Types tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

# Universal sync callback
ARCallableType = Callable[..., Any]
# Universal async callback
ARCallbackType = Callable[..., Awaitable[Any]]
