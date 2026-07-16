"""Writers tools for AsusRouter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final
from urllib.parse import quote_plus

from asusrouter.const import RequestType
from asusrouter.tools.identifiers import MacAddress

REQUEST_DELIMITER: Final[dict[RequestType, str]] = {
    RequestType.GET: "&",
    RequestType.POST: ";",
}


def _value_to_str(value: Any) -> str:
    """Render a request value as a device-friendly string."""

    if isinstance(value, MacAddress):
        return value.as_asus()
    if isinstance(value, bool):
        return "1" if value else "0"
    return "" if value is None else str(value)


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

    is_get = request_type == RequestType.GET
    parts: list[str] = []

    for key, value in data.items():
        val_str = _value_to_str(value)
        if is_get:
            parts.append(f"{quote_plus(str(key))}={quote_plus(val_str)}")
        else:
            # Escape single quotes to avoid breaking the 'key':'value' syntax
            esc_k = str(key).replace("'", "\\'")
            esc_v = val_str.replace("'", "\\'")
            parts.append(f"'{esc_k}':'{esc_v}'")

    return REQUEST_DELIMITER[request_type].join(parts)


__all__ = [
    "REQUEST_DELIMITER",
    "dict_to_request",
]
