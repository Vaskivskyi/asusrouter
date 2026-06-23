"""Parser for the get_port_status.cgi endpoint."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.ports.base import (
    ARPortCablePair,
    ARPortCableState,
    ARPortCapability,
    ARPortProperty,
    ARPortsData,
    ARPortsInfo,
    ARPortSpeed,
    ARPortType,
    ARUSBSpeed,
    read_port_capabilities,
    read_port_speed,
    read_port_type,
)
from asusrouter.modules.ports.common import warn_unknown_port
from asusrouter.modules.usb import ARUSBDevice
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import MacAddress

# Native-name prefixes used by the modern endpoint
_NATIVE_PREFIXES = ("L", "W", "U")


# Raw field -> (property, converter) for the simple per-port fields
_PORT_FIELD_CONVERTERS: dict[
    str, tuple[ARPortProperty, Callable[[Any], Any]]
] = {
    "ifname": (ARPortProperty.IFNAME, raw_to_str),
    "ui_display": (ARPortProperty.UI_DISPLAY, raw_to_str),
    "seq_no": (ARPortProperty.SEQ_NO, raw_to_int),
    "flag": (ARPortProperty.FLAG, raw_to_bool),
    "phy_port_id": (ARPortProperty.PHY_PORT_ID, raw_to_int),
    "ext_port_id": (ARPortProperty.EXT_PORT_ID, raw_to_int),
    "timeout": (ARPortProperty.TIMEOUT, raw_to_int),
    "linkrecover": (ARPortProperty.LINK_RECOVER, raw_to_bool),
}


def native_name(label: str) -> str | None:
    """Normalize a modern port label, or None if it is unknown.

    Modern labels are already in the target form (`L1`, `W0`, `U1`,
    `AI`); this only validates them and warns once on anything else.
    """

    if label == "AI":
        return "AI"
    if label[:1] in _NATIVE_PREFIXES and label[1:].isdigit():
        return label

    warn_unknown_port(label)
    return None


def read_role(
    name: str,
    base_role: ARPortType,
    capabilities: dict[ARPortCapability, bool],
    max_rate: ARPortSpeed | ARUSBSpeed,
) -> ARPortType:
    """Resolve the port role from its label and capabilities.

    `base_role` is the capability-derived type, reused here to avoid
    recomputing it.
    """

    # The AI board is a dedicated internal port identified by its label
    if name == "AI":
        return ARPortType.AI

    # A 10G-capable port advertising SFP+ is an SFP+ port
    if (
        max_rate == ARPortSpeed.MBPS_10000
        and capabilities.get(ARPortCapability.SFPP) is True
    ):
        return ARPortType.SFPP

    return base_role


def read_cable(
    values: dict[str, Any],
) -> dict[ARPortCablePair, ARPortCableState]:
    """Collapse the per-pair cable diagnostics into a single mapping."""

    cable: dict[ARPortCablePair, ARPortCableState] = {}
    for pair in ARPortCablePair:
        if pair.value not in values:
            continue
        cable[pair] = ARPortCableState(
            status=raw_to_int(values.get(pair.value)) or 0,
            length=raw_to_int(values.get(f"{pair.value}_len")) or 0,
        )

    return cable


def read_devices(values: dict[str, Any]) -> list[ARUSBDevice]:
    """Parse the USB devices connected to a port, if any."""

    raw_devices = values.get("devices")
    if not isinstance(raw_devices, dict):
        return []

    return [
        ARUSBDevice.from_raw(position, raw)
        for position, raw in raw_devices.items()
        if isinstance(raw, dict)
    ]


def read_node_info(raw: dict[str, Any]) -> dict[ARPortsInfo, Any]:
    """Parse the node-level info reported alongside the ports."""

    info: dict[ARPortsInfo, Any] = {}
    for member in ARPortsInfo:
        if member.value not in raw:
            continue
        if member is ARPortsInfo.CD_GOOD_TO_GO:
            info[member] = raw_to_bool(raw.get(member.value))
        else:
            info[member] = raw_to_int(raw.get(member.value))

    return info


def read_port(name: str, values: dict[str, Any]) -> dict[ARPortProperty, Any]:
    """Parse a single modern port entry into a property mapping."""

    capabilities = read_port_capabilities(values.get("cap"))
    base_role = read_port_type(capabilities)

    link_rate = read_port_speed(
        base_role, raw_to_int(values.get("link_rate")) or 0
    )
    max_rate = read_port_speed(
        base_role, raw_to_int(values.get("max_rate")) or 0
    )

    port: dict[ARPortProperty, Any] = {
        ARPortProperty.NATIVE_NAME: name,
        ARPortProperty.STATE: raw_to_bool(values.get("is_on")),
        ARPortProperty.LINK_RATE: link_rate,
        ARPortProperty.MAX_RATE: max_rate,
        ARPortProperty.ROLE: read_role(
            name, base_role, capabilities, max_rate
        ),
        ARPortProperty.CAPABILITIES: [
            cap for cap, present in capabilities.items() if present
        ],
        ARPortProperty.EXTENDED: True,
    }

    for raw_key, (prop, converter) in _PORT_FIELD_CONVERTERS.items():
        if raw_key in values:
            port[prop] = converter(values[raw_key])

    cable = read_cable(values)
    if cable:
        port[ARPortProperty.CABLE] = cable

    devices = read_devices(values)
    if devices:
        port[ARPortProperty.DEVICES] = devices

    return port


def translate_port_status(
    data: dict[str, Any], identity: ARDeviceIdentity
) -> dict[MacAddress, ARPortsData]:
    """Translate a get_port_status.cgi payload to the unified format."""

    node_info = data.get("node_info") or {}
    port_info = data.get("port_info") or {}

    # Preserve order: ports first, then any node-info-only MACs
    macs = list(port_info) + [m for m in node_info if m not in port_info]

    result: dict[MacAddress, ARPortsData] = {}
    for mac_raw in macs:
        mac = MacAddress.from_value_safe(mac_raw)
        if mac is None:
            continue

        ports: list[dict[ARPortProperty, Any]] = []
        for label, values in (port_info.get(mac_raw) or {}).items():
            name = native_name(label)
            if name is None:
                continue
            ports.append(read_port(name, values))

        result[mac] = ARPortsData(
            info=read_node_info(node_info.get(mac_raw) or {}),
            ports=ports,
        )

    return result
