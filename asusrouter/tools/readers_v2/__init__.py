"""Reading tools V2 for AsusRouter."""

from __future__ import annotations

import re
from typing import Any

from asusrouter.tools.readers_v2.raw import (
    is_true_in_dict,
    read_js_variables,
    read_json_content,
)

# Nested `'IFACE':{rx:0x..,tx:0x..}` from `update.cgi?output=netdev`
_NETDEV_NESTED_RE = re.compile(
    r"'(\w+)'\s*:\s*\{\s*rx\s*:\s*(0x[0-9a-fA-F]+)\s*,"
    r"\s*tx\s*:\s*(0x[0-9a-fA-F]+)\s*\}"
)
# Flat `"IFACE_rx":"0x.."` from the legacy appGet `netdev` hook
_NETDEV_FLAT_RE = re.compile(r'"(\w+)_(rx|tx)"\s*:\s*"(0x[0-9a-fA-F]+)"')


def read_netdev(content: str, **kwargs: Any) -> dict[str, dict[str, int]]:
    """Parse a netdev payload into per-interface byte counters.

    Handles both the `update.cgi` JS literal (nested, bare keys, single
    quotes) and the legacy appGet hook (flat `IFACE_rx` keys). Neither is
    parsed as JSON on purpose: both repeat `INTERNET` once per WAN unit on
    dual-WAN devices, so duplicates are summed per interface instead of
    being collapsed.
    """

    result: dict[str, dict[str, int]] = {}
    for iface, rx, tx in _NETDEV_NESTED_RE.findall(content):
        bucket = result.setdefault(iface, {})
        bucket["rx"] = bucket.get("rx", 0) + int(rx, 16)
        bucket["tx"] = bucket.get("tx", 0) + int(tx, 16)
    for iface, kind, value in _NETDEV_FLAT_RE.findall(content):
        bucket = result.setdefault(iface, {})
        bucket[kind] = bucket.get(kind, 0) + int(value, 16)
    return result


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


__all__ = [
    "is_true_in_dict",
    "read_js_section",
    "read_js_variables",
    "read_json_content",
    "read_netdev",
]
