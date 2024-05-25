"""Network tools endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.tools.readers import read_json_content


def read(content: str) -> dict[str, Any]:
    """Read port status data"""

    # Read the page content
    port_status: dict[str, Any] = read_json_content(content)

    return port_status


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process network tools data."""

    return {
        AsusData.PING: data,
    }
