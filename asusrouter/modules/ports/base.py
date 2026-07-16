"""Base definitions for the ports module.

Port models and the readers shared by the port_status and ethernet
parsers. Kept separate from the package __init__ so the parsing
submodules can import them without a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from asusrouter.modules.ports.enums import (
    ARPortCapability,
    ARPortProperty,
    ARPortsInfo,
    ARPortSpeed,
    ARPortType,
)
from asusrouter.modules.usb import ARUSBSpeed
from asusrouter.tools.converters.int import int_to_bits
from asusrouter.tools.converters.raw import raw_to_int


@dataclass(frozen=True)
class ARPortCableState:
    """Diagnostic state of a single ethernet cable pair."""

    status: int
    length: int


@dataclass(frozen=True)
class ARPortsData:
    """Ports and node-level info reported by a single device.

    Each entry in `ports` is a property mapping that always carries
    `ARPortProperty.NATIVE_NAME`.
    """

    info: dict[ARPortsInfo, Any]
    ports: list[dict[ARPortProperty, Any]]


_CAPABILITIES: list[ARPortCapability] = [
    cap for cap in ARPortCapability if cap.value >= 0
]

# The order is important: first matching capability wins
_PORT_CAPABILITY_TO_TYPE: dict[ARPortCapability, ARPortType] = {
    ARPortCapability.WAN: ARPortType.WAN,
    ARPortCapability.LAN: ARPortType.LAN,
    ARPortCapability.USB: ARPortType.USB,
    ARPortCapability.MOCA: ARPortType.MOCA,
}


def read_port_type(capabilities: dict[ARPortCapability, bool]) -> ARPortType:
    """Read port type from capability bits."""

    return next(
        (
            port_type
            for cap, port_type in _PORT_CAPABILITY_TO_TYPE.items()
            if capabilities.get(cap) is True
        ),
        ARPortType.UNKNOWN,
    )


def read_port_speed(
    port_type: ARPortType,
    raw: int,
) -> ARPortSpeed | ARUSBSpeed:
    """Read port link rate for the given port type."""

    if port_type == ARPortType.USB:
        return ARUSBSpeed.from_value(raw)
    return ARPortSpeed.from_value(raw)


def read_port_capabilities(raw: Any) -> dict[ARPortCapability, bool]:
    """Read port capabilities from raw integer."""

    value = raw_to_int(raw)
    if not isinstance(value, int) or value < 0:
        return {}
    bits = int_to_bits(value)
    return {cap: cap.value in bits for cap in _CAPABILITIES}


__all__ = [
    "ARPortCableState",
    "ARPortsData",
    "read_port_capabilities",
    "read_port_speed",
    "read_port_type",
]
