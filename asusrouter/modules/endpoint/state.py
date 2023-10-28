"""State endpoint module."""

from __future__ import annotations

from typing import Any


def read(content: str) -> dict[str, Any]:  # pylint: disable=unused-argument
    """Read state data"""

    # Read the json content
    state: dict[str, Any] = {}

    return state
