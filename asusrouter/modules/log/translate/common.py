"""Shared regex fragments for log event translation."""

from __future__ import annotations

# A MAC address as the firmware prints it (colon-separated, unpadded)
MAC_PATTERN = r"[0-9A-Fa-f:]+"

# A `wl<unit>[.<subunit>]` interface token, read as the `wl_id` field
WL_PATTERN = r"(?P<wl_id>wl[\d.]+)"

# A radio named either way
RADIO_PATTERN = rf"(?:{WL_PATTERN}|(?P<interface>eth\d+))"
