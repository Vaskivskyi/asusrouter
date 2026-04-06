"""Supported connections."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.readers import is_true_in_dict


class ARSupportConnection(FromStrMixin, StrEnum):
    """Connection types."""

    UNKNOWN = "unknown"

    HTTPS = "https"
    SSH = "ssh"


TRANSLATION_TABLE_CONNECTION: dict[ARSupportValue, ARSupportConnection] = {
    ARSupportValue.CONNECTION_HTTPS: ARSupportConnection.HTTPS,
    ARSupportValue.CONNECTION_SSH: ARSupportConnection.SSH,
}


def translate_connection(data: dict[str, Any]) -> list[ARSupportConnection]:
    """Translate connection data to ARSupportConnection."""

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
