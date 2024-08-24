"""Network tools endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.tools.readers import read_json_content as read  # noqa: F401


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process network tools data."""

    return {
        AsusData.PING: data,
    }
