"""Identifier tools."""

from __future__ import annotations

from asusrouter.tools.identifiers.hostname import Hostname
from asusrouter.tools.identifiers.ip import IpAddress, IpInterface
from asusrouter.tools.identifiers.mac import MacAddress
from asusrouter.tools.identifiers.password import Password
from asusrouter.tools.identifiers.serial import Serial
from asusrouter.tools.identifiers.ssid import Ssid
from asusrouter.tools.identifiers.username import Username
from asusrouter.tools.identifiers.wifi import WiFiInterface

__all__ = [
    "Hostname",
    "IpAddress",
    "IpInterface",
    "MacAddress",
    "Password",
    "Serial",
    "Ssid",
    "Username",
    "WiFiInterface",
]
