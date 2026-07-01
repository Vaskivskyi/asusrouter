"""Common vendor module for AsusRouter."""

from __future__ import annotations

# Coded prefixes mapped to a display-name template
_VENDOR_PREFIXES: dict[str, str] = {
    "android-dhcp-": "Android {}",
}

# Exact coded values mapped to their proper name
_VENDOR_ALIASES: dict[str, str] = {
    "MSFT 5.0": "Microsoft Corporation",
}


def format_vendor(vendor: str | None) -> str | None:
    """Format a coded vendor value into a readable name."""

    if not vendor:
        return vendor

    for prefix, template in _VENDOR_PREFIXES.items():
        if vendor.startswith(prefix):
            return template.format(vendor[len(prefix) :])

    return _VENDOR_ALIASES.get(vendor, vendor)
