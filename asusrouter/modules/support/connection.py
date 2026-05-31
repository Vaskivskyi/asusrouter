"""Supported connections."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.connection_v2 import ARConnection
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.readers import is_true_in_dict

TRANSLATION_TABLE_CONNECTION: dict[ARSupportValue, ARConnection] = {
    ARSupportValue.CONNECTION_HTTPS: ARConnection.HTTPS,
    ARSupportValue.CONNECTION_SSH: ARConnection.SSH,
}


def translate_connection(data: dict[str, Any]) -> list[ARConnection]:
    """Translate connection data to ARConnection."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    return [
        connection_type
        for (
            support_value,
            connection_type,
        ) in TRANSLATION_TABLE_CONNECTION.items()
        if is_true_in_dict(support_value.value, data)
    ]
