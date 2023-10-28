"""Port Status endpoint module."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.data import AsusData
from asusrouter.modules.ports import PORT_TYPE, PORT_VALUE_MAP, PortType
from asusrouter.tools.converters import safe_int
from asusrouter.tools.readers import read_json_content

_LOGGER = logging.getLogger(__name__)


def read(content: str) -> dict[str, Any]:  # pylint: disable=unused-argument
    """Read port status data"""

    # Read the page content
    port_status: dict[str, Any] = read_json_content(content)

    return port_status


def process(data: dict[str, Any]) -> dict[AsusData, Any]:
    """Process port status data"""

    ports = {
        PortType.LAN: {},
        PortType.USB: {},
        PortType.WAN: {},
    }

    if not data:
        return {
            AsusData.PORTS: ports,
            AsusData.NODE_INFO: {},
        }

    state: dict[AsusData, Any] = {}

    # Node info
    node_info = data.get("node_info", {})
    if node_info:
        # This is just a dict with a single pair mac: info
        mac = list(node_info.keys())[0]
        node = node_info[mac]
        state[AsusData.NODE_INFO] = node

    # Port info
    port_info = data.get("port_info", {})
    if port_info:
        # This is a dict with a single pair mac: info
        mac = list(port_info.keys())[0]
        info = port_info[mac]

        for port in info:
            if not port[0] in PORT_TYPE:
                _LOGGER.debug("Unknown port type `%s`. Please, report this", port[0])
                continue

            port_type = PORT_TYPE[port[0]]
            port_id = safe_int(port[1:])
            # Replace needed key/value pairs
            for key, key_to_use, method in PORT_VALUE_MAP:
                if key in info[port]:
                    info[port][key_to_use] = method(info[port][key])
                    if key_to_use != key:
                        info[port].pop(key)
            # Temporary solution for USB
            if port_type == PortType.USB and "devices" in info[port]:
                info[port]["state"] = True
            ports[port_type][port_id] = info[port]

    state[AsusData.PORTS] = ports

    return state
