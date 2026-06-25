"""Reading tools V2 for AsusRouter."""

from __future__ import annotations

from typing import Any


def read_js_section(data: Any, key: str) -> Any:
    """Read a section from JS-variable data.

    ASUS JS variables wrap their payload in a single-element list cover
    (`name = [VALUE][0];`); after parsing, the value is `[VALUE]`. Return
    its first element, or None when absent.
    """

    if not isinstance(data, dict):
        return None
    value = data.get(key)
    return value[0] if isinstance(value, list) and value else None
