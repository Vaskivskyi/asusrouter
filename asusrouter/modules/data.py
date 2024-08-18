"""Data module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from asusrouter.tools.converters import safe_bool


class AsusData(str, Enum):
    """AsusRouter data class."""

    AIMESH = "aimesh"
    AURA = "aura"
    BOOTTIME = "boottime"
    CLIENTS = "clients"
    CPU = "cpu"
    DEVICEMAP = "devicemap"
    FIRMWARE = "firmware"
    FIRMWARE_NOTE = "firmware_note"
    FLAGS = "flags"
    GWLAN = "gwlan"
    LED = "led"
    NETWORK = "network"
    NODE_INFO = "node_info"
    OPENVPN = "openvpn"
    OPENVPN_CLIENT = "openvpn_client"
    OPENVPN_SERVER = "openvpn_server"
    PARENTAL_CONTROL = "parental_control"
    PING = "ping"
    PORT_FORWARDING = "port_forwarding"
    PORTS = "ports"
    RAM = "ram"
    SPEEDTEST = "speedtest"
    # SPEEDTEST_HISTORY = "speedtest_history"
    SPEEDTEST_RESULT = "speedtest_result"
    # SPEEDTEST_SERVERS = "speedtest_servers"
    SYSINFO = "sysinfo"
    SYSTEM = "system"
    TEMPERATURE = "temperature"
    VPNC = "vpnc"
    VPNC_CLIENTLIST = "vpnc_clientlist"
    WAN = "wan"
    WIREGUARD = "wireguard"
    WIREGUARD_CLIENT = "wireguard_client"
    WIREGUARD_SERVER = "wireguard_server"
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

    def update_state(self, state: Any, last_id: Optional[int] = None) -> None:
        """Update a state variable in the data dict."""

        # Convert the state if needed
        state = convert_state(state)

        if last_id is not None:
            if not isinstance(self.data, dict):
                self.data = {}
            self.data.setdefault(last_id, {})["state"] = state
            return

        if isinstance(self.data, dict):
            self.data["state"] = state
            return

        self.data = {"state": state}

    def offset_time(self, offset: Optional[int]) -> None:
        """Offset the timestamp."""

        if offset is None:
            self.timestamp = datetime.now(timezone.utc)
            return

        self.timestamp = datetime.now(timezone.utc) + timedelta(seconds=offset)


def convert_state(state: Any):
    """Convert the state to a correct one."""

    # If the state is not boolean, convert it to boolean
    if not isinstance(state, bool):
        state = safe_bool(state)

    return state
