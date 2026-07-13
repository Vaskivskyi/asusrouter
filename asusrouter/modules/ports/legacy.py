"""Parser for the ajax_ethernet_ports.asp endpoint.

The legacy endpoint only reports the current link rate per port and has
no MAC, so the ports are attributed to the main device via its identity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.ports.base import ARPortsData
from asusrouter.modules.ports.common import warn_unknown_port
from asusrouter.modules.ports.enums import ARPortProperty, ARPortSpeed
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.identifiers import MacAddress

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Legacy label prefix -> native-name letter
_LEGACY_PREFIXES: dict[str, str] = {
    "WAN": "W",
    "LAN": "L",
    "USB": "U",
}

_DOWN_SPEEDS = (ARPortSpeed.DOWN, ARPortSpeed.UNKNOWN)

# Single-letter speed codes used by the ajax_ethernet_ports endpoint
_PORT_SPEED_MAP: dict[str, ARPortSpeed] = {
    "t": ARPortSpeed.MBPS_10,
    "X": ARPortSpeed.DOWN,
    "M": ARPortSpeed.MBPS_100,
    "G": ARPortSpeed.MBPS_1000,
    "Q": ARPortSpeed.MBPS_2500,
    "F": ARPortSpeed.MBPS_5000,
    "T": ARPortSpeed.MBPS_10000,
}


def read_ethernet_port_speed(code: str) -> ARPortSpeed:
    """Read port speed from the legacy single-letter router code."""

    return _PORT_SPEED_MAP.get(code, ARPortSpeed.UNKNOWN)


def native_name(label: str) -> str | None:
    """Normalize a legacy port label to the modern native name.

    `LAN 1` -> `L1`, `WAN 0` -> `W0`, a 10G port -> `SFP`. Unknown
    labels are skipped with a one-time warning.
    """

    prefix = label[:3].upper()

    if prefix == "10G":
        return "SFP"

    letter = _LEGACY_PREFIXES.get(prefix)
    index = raw_to_int(label[3:])
    if letter is None or index is None:
        warn_unknown_port(label)
        return None

    return f"{letter}{index}"


def translate_ethernet_ports(
    data: dict[str, Any], identity: ARDeviceIdentity
) -> dict[MacAddress, ARPortsData]:
    """Translate an ajax_ethernet_ports.asp payload to the unified format."""

    port_speed = data.get("portSpeed")
    if not port_speed:
        return {}

    mac = identity.mac
    if mac is None:
        return {}

    ports: list[dict[ARPortProperty, Any]] = []
    for label, code in port_speed.items():
        name = native_name(label)
        if name is None:
            continue
        link_rate = read_ethernet_port_speed(code)
        ports.append(
            {
                ARPortProperty.NATIVE_NAME: name,
                ARPortProperty.STATE: link_rate not in _DOWN_SPEEDS,
                ARPortProperty.LINK_RATE: link_rate,
                ARPortProperty.EXTENDED: False,
            }
        )

    return {mac: ARPortsData(info={}, ports=ports)}
