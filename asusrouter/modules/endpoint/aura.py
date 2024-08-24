"""Aura endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.readers import read_json_content


def read(content: str) -> dict[str, Any]:
    """Read aura data"""

    # Read the json content
    aura: dict[str, Any] = read_json_content(content)

    return aura
