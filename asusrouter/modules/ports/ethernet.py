"""Ethernet ports module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class ARPortEthernetSpeed(FromIntMixin, IntEnum):
    """Ethernet port speed."""

    UNKNOWN = UNKNOWN_MEMBER

    DOWN = 0
    MBPS_10 = 10
    MBPS_100 = 100
    MBPS_1000 = 1000
    MBPS_2500 = 2500
    MBPS_5000 = 5000
    MBPS_10000 = 10000


_PORT_SPEED_MAP: dict[str, ARPortEthernetSpeed] = {
    "t": ARPortEthernetSpeed.MBPS_10,
    "X": ARPortEthernetSpeed.DOWN,
    "M": ARPortEthernetSpeed.MBPS_100,
    "G": ARPortEthernetSpeed.MBPS_1000,
    "Q": ARPortEthernetSpeed.MBPS_2500,
    "F": ARPortEthernetSpeed.MBPS_5000,
    "T": ARPortEthernetSpeed.MBPS_10000,
}


def read_ethernet_port_speed(code: str) -> ARPortEthernetSpeed:
    """Read port speed from router code."""

    return _PORT_SPEED_MAP.get(code, ARPortEthernetSpeed.UNKNOWN)
