"""Access Point module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AccessPoint:
    """Access point class."""

    # Basic information
    mac: str | None = None
    ssid: str | None = None

    # Fronthaul information
    hidden: bool | None = None
    mac_fh: str | None = None
    ssid_fh: str | None = None
