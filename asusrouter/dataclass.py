"""Dataclass module for AsusRouter"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from asusrouter.util.converters import none_or_str


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

    # WLAN only values
    online: bool | None = None
    rssi: int | None = None
    connected_since: int | None = None
    rx_speed: float | None = None
    tx_speed: float | None = None


@dataclass
class AsusDevice:
    """Asus device class"""

    serial: str | None = None
    mac: str | None = None
    model: str | None = None
    brand: str = "ASUSTek"
    fw_major: str | None = None
    fw_minor: str | None = None
    fw_build: str | None = None
    services: str | None = None
    sysinfo: bool = False
    led: bool = False
    ledg: bool = False
    aura: bool = False
    vpn_status: bool = False

    def firmware(self) -> str:
        return "{}.{}_{}".format(self.fw_major, self.fw_minor, self.fw_build)


@dataclass
class Key:
    """Key class"""

    value: str | int
    value_to_use: str = ""
    method: function = none_or_str

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
class Monitor(dict):
    """
    Monitor class

    In general this is dict with additions

    Properties
    -----
    `active`: bool flag of monitor being active

    `time`: datetime object showing the last time monitor was updated

    `ready`: bool flag if monitor was ever loaded

    Methods
    -----
    `start`: set `active` to True

    `stop`: set `active` to False

    `reset`: set `time` to utcnow()

    `finish`: set `ready` to True
    """

    active: bool = False
    time: datetime | None = None
    ready: bool = False

    def start(self) -> None:
        """Set to active"""

        self.active = True

    def stop(self) -> None:
        """Set to not-active"""

        self.active = False

    def reset(self) -> None:
        """Reset time to utcnow"""

        self.time = datetime.utcnow()

    def finish(self) -> None:
        """Set ready status to True"""

        self.ready = True
