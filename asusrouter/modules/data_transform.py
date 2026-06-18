"""Data transform module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.client import process_client
from asusrouter.modules.data import AsusDataState
from asusrouter.modules.ports import ARPortType
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import support_available_in
from asusrouter.modules.wan import ARWANCapability
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.readers import readable_mac

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# List of models with 6Ghz support
# and no 5Ghz2 support
MODEL_WITH_6GHZ = [
    "RT-AXE95Q",
]


def transform_network(
    data: dict[str, Any],
    description: ARDeviceIdentity,
    history: AsusDataState | None,
) -> dict[str, Any]:
    """Transform network data."""

    if not support_available_in(
        description.support,
        ARSupportType.WAN_CAPABILITIES,
        ARWANCapability.DUALWAN,
    ):
        return data

    network = data.copy()
    for interface in network:
        for speed in ("rx_speed", "tx_speed"):
            if speed not in network[interface]:
                network[interface][speed] = 0.0

    if "usb" not in network:
        usb_history = (
            history.data.get("usb") if history and history.data else None
        )
        if usb_history:
            network["usb"] = usb_history
            network["usb"]["rx_speed"] = 0.0
            network["usb"]["tx_speed"] = 0.0
        else:
            network["usb"] = {
                "rx": 0,
                "tx": 0,
                "rx_speed": 0.0,
                "tx_speed": 0.0,
            }

    if "5ghz2" in network:
        wifi = description.wifi
        support_5g2 = ARWiFiBand.BAND_5G2 in wifi
        support_6g = ARWiFiBand.BAND_6G1 in wifi
        if (
            not support_5g2 and support_6g
        ) or description.model in MODEL_WITH_6GHZ:
            network["6ghz"] = network.pop("5ghz2")

    return network


def transform_clients(
    data: dict[str, Any], history: AsusDataState | None, **kwargs: Any
) -> dict[str, Any]:
    """Transform clients data."""

    clients = {}
    for mac, client in data.items():
        if readable_mac(mac):
            # Check client history
            client_history = (
                history.data.get(mac) if history and history.data else None
            )
            # Process the client
            clients[mac] = process_client(client, client_history, **kwargs)

    return clients


def transform_cpu(
    data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Transform cpu data."""

    for info in data.values():
        info.setdefault("usage", None)

    return data


def transform_ethernet_ports(
    data: dict[str, Any],
    mac: str | None,
) -> dict[str, dict[str, Any]]:
    """Transform the legacy ethernet ports data to the new format."""

    # Check if the first level of the dict is ARPortType enum
    # If any other key is found, return the data as is
    for data_key in data:
        if not isinstance(data_key, ARPortType):
            return data

    # If mac is not available, return the data as is
    if not mac:
        return data

    # Transform the data
    return {mac: data}


def transform_wan(
    data: dict[str, Any],
    support: dict[ARSupportType, Any] | None,
) -> dict[str, Any]:
    """Transform WAN data."""

    wan = data.copy()

    if not support:
        return wan

    wan_caps = support.get(ARSupportType.WAN_CAPABILITIES)
    if (
        not isinstance(wan_caps, list)
        or ARWANCapability.DUALWAN not in wan_caps
    ):
        wan.pop("dualwan", None)
    if (
        not isinstance(wan_caps, list)
        or ARWANCapability.AGGREGATION not in wan_caps
    ):
        wan.pop("aggregation", None)

    return wan
