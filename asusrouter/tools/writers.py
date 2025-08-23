"""Writers module.

This module contains the writers for AsusRouter,
which prepare data to be sent to the router.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final
from urllib.parse import quote_plus

from asusrouter.config import (
    CONFIG_DEFAULT_ALREADY_NOTIFIED,
    ARConfigBase,
    ARConfigKeyBase,
)
from asusrouter.const import RequestType
from asusrouter.tools.converters import clean_input
from asusrouter.tools.identifiers import MacAddress

REQUEST_DELIMITER: Final[dict[RequestType, str]] = {
    RequestType.GET: "&",
    RequestType.POST: ";",
}


@clean_input
def nvram(content: str | list[str] | None = None) -> str | None:
    """NVRAM writer.

    This function converts a list of strings (or a single string)
    into a string request to the NVRAM read endpoint.
    """

    if isinstance(content, str):
        return f"nvram_get({content});"

    if isinstance(content, list):
        return "".join([f"nvram_get({item});" for item in content])

    return None


@clean_input
def dict_to_request(
    data: Mapping[str, Any], request_type: RequestType = RequestType.POST
) -> str:
    """Convert a mapping to a request string.

    - For RequestType.GET keys and values are URL-quoted (quote_plus) and
      pairs are joined with '&'.
    - For RequestType.POST keys and values are escaped for single-quotes and
      pairs are joined with ';'.
    """
    if not data:
        return ""

    delimiter = REQUEST_DELIMITER.get(
        request_type, REQUEST_DELIMITER[RequestType.GET]
    )
    parts: list[str] = []

    for key, value in data.items():
        # Normalize value (handle MacAddress specially)
        if isinstance(value, MacAddress):
            val_str = value.as_asus()
        elif isinstance(value, bool):
            # Device-friendly boolean representation
            val_str = "1" if value else "0"
        else:
            val_str = "" if value is None else str(value)

        if request_type == RequestType.GET:
            k = quote_plus(str(key))
            v = quote_plus(val_str)
            parts.append(f"{k}={v}")
        else:  # POST
            # Escape single quotes to avoid breaking the 'key':'value' syntax
            esc_k = str(key).replace("'", "\\'")
            esc_v = val_str.replace("'", "\\'")
            parts.append(f"'{esc_k}':'{esc_v}'")

    return delimiter.join(parts) if parts else ""


def ensure_notification_flag(
    config: ARConfigBase,
    key: ARConfigKeyBase,
) -> None:
    """Ensure notification flag exists in the configs."""

    if key not in config:
        config.register(key)
        config.set(
            key,
            CONFIG_DEFAULT_ALREADY_NOTIFIED,
        )
