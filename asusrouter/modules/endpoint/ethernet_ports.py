"""Ethernet ports endpoint module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ports import PORT_SPEED, PortSpeed, PortType
from asusrouter.tools.converters import safe_int
from asusrouter.tools.readers import read_json_content


def read(content: str) -> dict[str, Any]:
    """Read ethernet ports data."""

    # Read the json content
    ethernet_ports: dict[str, Any] = read_json_content(
        content.replace("get_wan_lan_status = ", "").replace(";", "")
    )

    return ethernet_ports


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process ethernet ports data."""

    # Ports info
    ports = {
        PortType.LAN: {},
        PortType.WAN: {},
    }
    if "portSpeed" in data:
        data = data["portSpeed"]
        for port, value in data.items():
            port_type = PortType(port[0:3].lower())
            port_id = safe_int(port[3:])
            link_rate = PORT_SPEED.get(value)
            ports[port_type][port_id] = {
                "state": link_rate != PortSpeed.LINK_DOWN,
                "link_rate": link_rate,
            }

    return {
        AsusData.PORTS: ports,
    }
