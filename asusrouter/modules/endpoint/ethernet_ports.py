"""Ethernet ports endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ports import (
    ARPortEthernetSpeed,
    ARPortType,
    read_ethernet_port_speed,
)
from asusrouter.tools.converters import safe_int
from asusrouter.tools.readers import read_json_content

_LOGGER = logging.getLogger(__name__)


def read(content: str, **kwargs: Any) -> dict[str, Any]:
    """Read ethernet ports data."""

    # Read the json content
    ethernet_ports: dict[str, Any] = read_json_content(
        content.replace("get_wan_lan_status = ", "").replace(";", "")
    )

    return ethernet_ports


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process ethernet ports data."""

    # Ports info
    ports: dict[ARPortType, dict[Any, Any]] = {
        ARPortType.LAN: {},
        ARPortType.WAN: {},
    }

    port_speed = data.get("portSpeed")

    if port_speed is None:
        return {
            AsusData.PORTS: ports,
        }

    for port, value in port_speed.items():
        # Get the port code
        port_code = port[0:3].lower()
        # Check whether the port code is in ARPortType enum
        try:
            port_type = ARPortType(port_code)
        except ValueError:
            # This should be some other kind of port and not LAN or WAN
            # Based on https://github.com/Vaskivskyi/ha-asusrouter/issues/774
            # it is probably the SFPP port, since 10G WAN/LAN should be
            # detected properly.
            if port_code == "10g":
                port_type = ARPortType.SFPP
            else:
                continue

            # If the port type is not in the ports dict, add it
            if port_type not in ports:
                ports[port_type] = {}

        # Get the port id and link rate
        port_id = safe_int(port[3:])
        link_rate = read_ethernet_port_speed(value)
        # Save the port info
        ports[port_type][port_id] = {
            "state": link_rate
            not in (
                ARPortEthernetSpeed.DOWN,
                ARPortEthernetSpeed.UNKNOWN,
            ),
            "link_rate": link_rate,
        }

    return {
        AsusData.PORTS: ports,
    }
