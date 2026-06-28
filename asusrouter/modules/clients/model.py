"""Clients model for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from asusrouter.modules.common.connection import ARConnectionType
from asusrouter.modules.common.device import ARDeviceType
from asusrouter.modules.common.internet import ARInternetMode
from asusrouter.modules.common.ip import ARIPMethod
from asusrouter.modules.wifi import ARWiFiAuth, ARWiFiBand, ARWiFiFrequency
from asusrouter.tools.identifiers import IpAddress, MacAddress


@dataclass
class ARClientLink:
    """One radio link of a client's wireless connection."""

    frequency: ARWiFiFrequency = ARWiFiFrequency.UNKNOWN
    band: ARWiFiBand | None = None
    mac: MacAddress | None = None
    rssi: int | None = None
    rx_speed: float | None = None
    tx_speed: float | None = None
    connected_since: datetime | None = None


@dataclass
class ARClientConnection:
    """The current connection of an online client."""

    type: ARConnectionType = ARConnectionType.UNKNOWN
    ip: IpAddress | None = None
    ip_method: ARIPMethod = ARIPMethod.UNKNOWN
    internet_access: bool | None = None
    node: MacAddress | None = None
    ssid: str | None = None
    security: ARWiFiAuth | None = None
    guest: bool = False
    sdn: str | None = None
    mlo: bool = False
    connected_since: datetime | None = None
    links: list[ARClientLink] = field(default_factory=list)


@dataclass
class ARClient:
    """A network client (identity and preferences)."""

    mac: MacAddress
    online: bool = False
    name: str | None = None
    vendor: str | None = None
    vendor_class: str | None = None
    device_type: ARDeviceType = ARDeviceType.UNKNOWN
    os_type: int | None = None
    bound_node: MacAddress | None = None
    internet_mode: ARInternetMode = ARInternetMode.UNKNOWN
    connection: ARClientConnection | None = None
