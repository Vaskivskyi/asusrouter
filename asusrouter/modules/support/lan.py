"""Supported LAN."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.lan import ARLANCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict


def translate_lan_capabilities(data: dict[str, Any]) -> list[ARLANCapability]:
    """Translate LAN capabilities support data."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    result: list[ARLANCapability] = []

    if is_true_in_dict(ARSupportValue.LAN_AGGREGATION.value, data):
        result.append(ARLANCapability.AGGREGATION)

    return result
