"""Networkmapd endpoint module."""

from __future__ import annotations

from typing import Any


def read(content: str) -> dict[str, Any]:  # pylint: disable=unused-argument
    """Read networkmapd data"""

    # Read the json content
    networkmapd: dict[str, Any] = {}

    return networkmapd
