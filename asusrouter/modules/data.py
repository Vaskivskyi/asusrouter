"""Data module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AsusData(str, Enum):
    """AsusRouter data class."""

    AIMESH = "aimesh"
    BOOTTIME = "boottime"
    CLIENTS = "clients"
    CPU = "cpu"
    DEVICEMAP = "devicemap"
    FIRMWARE = "firmware"
    FLAGS = "flags"
    GWLAN = "gwlan"
    LED = "led"
    NETWORK = "network"
    NODE_INFO = "node_info"
    OPENVPN = "openvpn"
    PARENTAL_CONTROL = "parental_control"
    PORT_FORWARDING = "port_forwarding"
    PORTS = "ports"
    RAM = "ram"
    SYSINFO = "sysinfo"
    SYSTEM = "system"
    TEMPERATURE = "temperature"
    WAN = "wan"
    WLAN = "wlan"


@dataclass
class AsusDataState:
    """State of data."""

    data: Optional[Any] = None
    timestamp: datetime = datetime.now(timezone.utc)
    active: bool = False
    inactive_event: asyncio.Event = asyncio.Event()

    def start(self) -> None:
        """Set to active."""

        self.active = True
        self.inactive_event.clear()

    def stop(self) -> None:
        """Set to not-active."""

        self.active = False
        self.inactive_event.set()

    def update(self, data: Any) -> None:
        """Update the state."""

        self.data = data
        # Set timestamp to the current utc time
        self.timestamp = datetime.now(timezone.utc)
        # Set to inactive
        self.stop()

    def update_state(self, state: Any) -> None:
        """Update a state variable in the data dict."""

        if isinstance(self.data, dict):
            self.data.update({"state": state})
            return

        self.data = {"state": state}
