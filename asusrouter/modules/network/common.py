"""Shared helpers for the network module."""

from __future__ import annotations

import re
from typing import Any

from asusrouter.modules.network.enums import ARNetworkField
from asusrouter.modules.wifi import ARWiFiMacFilterMode
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.identifiers.mac import MacAddress
from asusrouter.tools.units import DataRateUnitConverter, UnitOfDataRate

# Matches a colon-separated MAC address anywhere in a string
_MAC_RE = re.compile(r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}")

# Raw filter mode value -> mode (both numeric and text are seen)
_MAC_FILTER_MODES: dict[str, ARWiFiMacFilterMode] = {
    "0": ARWiFiMacFilterMode.DISABLED,
    "1": ARWiFiMacFilterMode.ALLOW,
    "2": ARWiFiMacFilterMode.DENY,
    "disabled": ARWiFiMacFilterMode.DISABLED,
    "allow": ARWiFiMacFilterMode.ALLOW,
    "deny": ARWiFiMacFilterMode.DENY,
}


def decode(raw: Any) -> str:
    """Decode the char-encoded nvram separators to `<`/`>`."""

    if not isinstance(raw, str):
        return ""
    return raw.replace("&#60", "<").replace("&#62", ">")


def read_mac_list(raw: Any) -> list[MacAddress]:
    """Read a MAC filter list into MAC addresses."""

    return [
        mac
        for token in _MAC_RE.findall(decode(raw))
        if (mac := MacAddress.from_value_safe(token)) is not None
    ]


def mac_filter_mode(raw: Any) -> ARWiFiMacFilterMode | None:
    """Map a raw filter mode value to a mode, or None if unknown."""

    return _MAC_FILTER_MODES.get(str(raw))


def _to_bits(raw: Any) -> int | None:
    """Convert a Kib/s rate to bits/s, or None if unparsable."""

    value = raw_to_int(raw)
    if value is None:
        return None
    return int(
        DataRateUnitConverter.convert_to_base(
            value, UnitOfDataRate.KIBIBIT_PER_SECOND
        )
    )


def bandwidth_limit(
    enabled: Any, download: Any, upload: Any
) -> dict[ARNetworkField, Any]:
    """Build the bandwidth-limiter fields, empty when the limiter is off.

    Both backends store the per-direction rate in Kib/s; it is exposed in
    bits/s.
    """

    if not (raw_to_bool(enabled) or False):
        return {}

    fields: dict[ARNetworkField, Any] = {}
    down = _to_bits(download)
    if down is not None:
        fields[ARNetworkField.BANDWIDTH_LIMIT_DOWNLOAD] = down
    up = _to_bits(upload)
    if up is not None:
        fields[ARNetworkField.BANDWIDTH_LIMIT_UPLOAD] = up
    return fields
