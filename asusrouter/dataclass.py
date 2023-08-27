"""Dataclass module for AsusRouter"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from asusrouter.util.converters import none_or_any, none_or_str

DEFAULT_PARENTAL_CONTROL_TIMEMAP = "W03E21000700<W04122000800"


@dataclass
class ConnectedDevice:
    """Connected device class"""

    name: str | None = None
    mac: str | None = None

    ip: str | None = None
    ip_method: str | None = None

    internet_state: bool | None = None
    internet_mode: bool | None = None

    connection_type: str | None = None
    node: str | None = None

    # WLAN only values
    online: bool = False
    rssi: int | None = None
    connected_since: int | None = None
    rx_speed: float | None = None
    tx_speed: float | None = None

    guest: int = 0


@dataclass
class AsusDevice:
    """Asus device class"""

    serial: str | None = None
    mac: str | None = None
    model: str | None = None
    brand: str = "ASUSTek"
    firmware: Firmware | None = None
    services: str | None = None
    led: bool = False
    ledg: bool = False
    aura: bool = False
    vpn_status: bool = False
    endpoints: dict[str, bool] | None = None


@dataclass
class AiMeshDevice:
    """AiMesh device class"""

    # Status
    status: bool = False

    alias: str | None = None
    model: str | None = None
    product_id: str | None = None
    ip: str | None = None

    fw: str | None = None
    fw_new: str | None = None

    mac: str | None = None

    # Access point: ap2g, ap5g, ap5g1, ap6g, apdwb
    ap: dict[str, Any] | None = None
    # Parent AiMesh: pap2g, rssi2g, pap2g_ssid, pap5g, rssi5g, pap5g_ssid, pap6g, rssi6g, pap6g_ssid
    parent: dict[str, Any] | None = None
    # Node state
    state: int | None = None
    level: int | None = None
    config: dict[str, Any] | None = None


@dataclass
class Key:
    """Key class"""

    value: str | int
    value_to_use: str = ""
    method: Callable = none_or_str

    def __str__(self) -> str:
        """Return only `value` as default"""

        return str(self.value)

    def get(self) -> str:
        """
        Get the proper value

        Returns
        -----
        `value_to_use` if exists, `value` otherwise
        """

        if self.value_to_use != "":
            return self.value_to_use

        return self.value


@dataclass
class SearchKey:
    """SearchKey class"""

    value: str
    method: Callable = none_or_any

    def __str__(self) -> str:
        """Return only `value` as default"""

        return str(self.value)


@dataclass
class Monitor(dict):
    """
    Monitor class

    In general this is dict with additions

    Properties
    -----
    `active`: bool flag of monitor being active

    `time`: datetime object showing the last time monitor was updated

    `ready`: bool flag if monitor is compiled

    Methods
    -----
    `start`: set `active` to True

    `stop`: set `active` to False

    `reset`: set `time` to utcnow()

    `finish`: set `ready` to True
    """

    active: bool = False
    time: datetime | None = None
    ready: bool = True
    enabled: bool = True
    inactive_event: asyncio.Event = asyncio.Event()

    def start(self) -> None:
        """Set to active"""

        self.active = True
        self.inactive_event.clear()

    def stop(self) -> None:
        """Set to not-active"""

        self.active = False
        self.inactive_event.set()

    def reset(self) -> None:
        """Reset time to utcnow"""

        self.time = datetime.utcnow()

    def finish(self) -> None:
        """Set ready status to True"""

        self.ready = True

    def drop(self) -> None:
        """Drop on errors"""

        self.stop()
        self.ready = False


@dataclass
class Firmware:
    """Firmware class"""

    major: str = "3.0.0.4"
    minor: int | None = None
    build: int | None = None
    build_more: int | str | None = None

    def __lt__(self, other: Firmware | None) -> bool:
        """Define less-than"""

        result = False

        if other:
            if self.major and other.major:
                # Check if the first character of either major version is the same
                if self.major[0] == other.major[0]:
                    # Split the major versions into lists of integers
                    major1 = [int(x) for x in self.major.split(".")]
                    major2 = [int(x) for x in other.major.split(".")]
                    # Compare the major versions
                    if major1 < major2:
                        result = True
                    # Proceed only if major is the same for both
                    elif major1 == major2:
                        if (
                            (self.minor and other.minor and self.minor < other.minor)
                            or (self.build and other.build and self.build < other.build)
                            or (
                                isinstance(self.build_more, int)
                                and isinstance(self.build_more, type(other.build_more))
                                and self.build_more < other.build_more
                            )
                        ):
                            result = True

        return result

    def __str__(self) -> str:
        """Define string"""

        return f"{self.major}.{self.minor}.{self.build}_{self.build_more}"


@dataclass(frozen=True)
class FilterDevice:
    """Device filter class"""

    mac: str | None = None
    name: str | None = None
    type: str | None = None
    timemap: str = DEFAULT_PARENTAL_CONTROL_TIMEMAP


@dataclass(frozen=True)
class PortForwarding:
    """Port forwarding class"""

    name: str = str()
    ip: str = str()
    port: str = str()
    protocol: str = str()
    ip_external: str = str()
    port_external: str = str()
