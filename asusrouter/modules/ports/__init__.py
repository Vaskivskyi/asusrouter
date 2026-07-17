"""Ports module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.ports.base import (
    ARPortCableState,
    ARPortsData,
    read_port_capabilities,
    read_port_speed,
    read_port_type,
)
from asusrouter.modules.ports.enums import (
    ARPortCablePair,
    ARPortCapability,
    ARPortProperty,
    ARPortsInfo,
    ARPortSpeed,
    ARPortType,
)
from asusrouter.modules.ports.source import (
    ARPortsSource,
    ARPortsSourceUniversal,
    fetch_state,
    translate_state,
)
from asusrouter.modules.usb import ARUSBDevice, ARUSBDeviceType, ARUSBSpeed

__all__ = [
    "ARPortCablePair",
    "ARPortCableState",
    "ARPortCapability",
    "ARPortSpeed",
    "ARPortProperty",
    "ARPortType",
    "ARUSBSpeed",
    "ARPortsInfo",
    "ARPortsData",
    "ARPortsSource",
    "ARPortsSourceUniversal",
    "ARUSBDevice",
    "ARUSBDeviceType",
    "fetch_state",
    "read_port_capabilities",
    "read_port_speed",
    "read_port_type",
    "translate_state",
]
