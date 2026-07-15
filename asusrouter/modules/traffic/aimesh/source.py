"""AiMesh traffic data source for AsusRouter."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.aimesh.topology import ARAiMeshMedium
from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_request_type
from asusrouter.modules.traffic.base import ARTrafficLink, ARTrafficSource
from asusrouter.modules.traffic.enums import ARTrafficType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.readers import read_units_data_rate
from asusrouter.tools.types import ARCallableType, ARCallbackType
from asusrouter.tools.units import UnitOfDataRate
from asusrouter.tools.writers import dict_to_request

_LOGGER = logging.getLogger(__name__)

_read_kibps = read_units_data_rate(UnitOfDataRate.KIBIBIT_PER_SECOND)
_read_Mibps = read_units_data_rate(UnitOfDataRate.MEBIBIT_PER_SECOND)  # noqa: N816

_OK_STATUS = 200

# Wireless backhaul mediums (use the station endpoint)
_WIRELESS_BACKHAUL = (ARAiMeshMedium.WIRELESS, ARAiMeshMedium.MLO)

# Raw (flattened) key -> (output metric, value reader)
_TRANSLATION_TABLE: dict[str, tuple[ARMetricType, ARCallableType]] = {
    "data_rx": (ARMetricType.RX_SPEED, _read_kibps),
    "data_tx": (ARMetricType.TX_SPEED, _read_kibps),
    "data_avg_rx": (ARMetricType.RX_SPEED_AVG, _read_kibps),
    "data_avg_tx": (ARMetricType.TX_SPEED_AVG, _read_kibps),
    "phy_rx": (ARMetricType.PHY_RX_SPEED, _read_Mibps),
    "phy_tx": (ARMetricType.PHY_TX_SPEED, _read_Mibps),
}


class ARTrafficAiMeshSource(ARTrafficSource):
    """AiMesh traffic source."""


def _resolve_band(
    link: ARWiFiBand,
    node_mac: MacAddress,
    identity: ARDeviceIdentity,
) -> tuple[AREndpoint | None, dict[str, Any]]:
    """Resolve the wifi fronthaul endpoint for a band."""

    node = identity.aimesh.get(node_mac)
    radio = node.radios.get(link) if node else None
    band_mac = (radio.mac_fh or radio.mac_ap) if radio else None
    if band_mac is None:
        return None, {}
    return AREndpoint.FETCH_TRAFFIC_WIFI, {
        "node_mac": node_mac,
        "band_mac": band_mac,
    }


def _resolve_backhaul(
    node_mac: MacAddress,
    identity: ARDeviceIdentity,
) -> tuple[AREndpoint | None, dict[str, Any]]:
    """Resolve the backhaul endpoint from the node's uplink medium."""

    node = identity.aimesh.get(node_mac)
    backhaul = node.backhaul if node else None
    if backhaul is None:
        return None, {}
    if backhaul.medium in _WIRELESS_BACKHAUL:
        if backhaul.mac_parent is None or backhaul.mac_sta is None:
            return None, {}
        return AREndpoint.FETCH_TRAFFIC_BACKHAUL, {
            "node_mac": backhaul.mac_parent,
            "sta_mac": backhaul.mac_sta,
        }
    return AREndpoint.FETCH_TRAFFIC_ETHERNET, {
        "node_mac": node_mac,
        "is_bh": True,
    }


def _resolve(
    link: ARTrafficLink,
    node_mac: MacAddress,
    identity: ARDeviceIdentity,
) -> tuple[AREndpoint | None, dict[str, Any]]:
    """Resolve the endpoint and request args for a link via topology."""

    if isinstance(link, ARWiFiBand):
        return _resolve_band(link, node_mac, identity)
    if link is ARTrafficType.WIRED:
        return AREndpoint.FETCH_TRAFFIC_ETHERNET, {
            "node_mac": node_mac,
            "is_bh": False,
        }
    if link is ARTrafficType.BACKHAUL:
        return _resolve_backhaul(node_mac, identity)
    # WAN / USB / LACP / UNKNOWN - not served by AiMesh
    return None, {}


async def _get_one(
    callback: ARCallbackType,
    link: ARTrafficLink,
    node_mac: MacAddress,
    identity: ARDeviceIdentity,
) -> dict[ARTrafficLink, Any]:
    """Fetch the raw traffic of a single link, keyed by it."""

    endpoint, args = _resolve(link, node_mac, identity)
    if endpoint is None:
        return {}

    request = dict_to_request(
        args, request_type=get_endpoint_request_type(endpoint)
    )
    return {link: await callback(endpoint=endpoint, request=request)}


async def _get_all(
    node_mac: MacAddress,
    identity: ARDeviceIdentity,
    get_data_callback: ARCallbackType | None,
) -> dict[ARTrafficLink, Any]:
    """Fetch all of a node's links via the cached pipeline, merged."""

    if get_data_callback is None:
        return {}

    node = identity.aimesh.get(node_mac)
    links: list[ARTrafficLink] = list(node.radios) if node else []
    links.append(ARTrafficType.WIRED)
    if node is not None and node.backhaul is not None:
        links.append(ARTrafficType.BACKHAUL)

    sources = [ARTrafficAiMeshSource(link, node_mac) for link in links]
    results = await get_data_callback(sources)

    merged: dict[ARTrafficLink, Any] = {}
    if isinstance(results, dict):
        for content in results.values():
            if isinstance(content, dict):
                merged.update(content)
    return merged


async def get_state(
    callback: ARCallbackType,
    source: ARTrafficAiMeshSource,
    *,
    identity: ARDeviceIdentity,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Fetch AiMesh traffic for the source's link (or all links)."""

    node_mac = source.target or identity.mac
    if node_mac is None:
        return {}

    if source.link is None:
        return await _get_all(node_mac, identity, get_data_callback)
    return await _get_one(callback, source.link, node_mac, identity)


def _is_metrics(value: Any) -> bool:
    """Whether a value is already a decoded metrics dict."""

    return isinstance(value, dict) and all(
        isinstance(key, ARMetricType) for key in value
    )


def _flatten_dict(d: Any, parent_key: str = "") -> dict[str, Any]:
    """Flatten a nested dict, joining nested keys with `_`."""

    if not isinstance(d, dict):
        return {}

    flat: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}_{key}" if parent_key else str(key)
        if isinstance(value, dict):
            flat.update(_flatten_dict(value, new_key))
        else:
            flat[new_key] = value

    return flat


def _to_metrics(raw: Any) -> dict[ARMetricType, Any]:
    """Translate a raw traffic response into metrics."""

    flat = _flatten_dict(raw)
    if not flat:
        return {}

    status = raw_to_int(flat.get("error_status"))
    if status is not None and status != _OK_STATUS:
        _LOGGER.warning("AiMesh traffic returned status `%s`", status)

    return {
        metric: reader(flat[key])
        for key, (metric, reader) in _TRANSLATION_TABLE.items()
        if key in flat
    }


def translate_state(
    data: Any,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Translate raw (atomic) or pass through merged (aggregate) traffic."""

    if not isinstance(data, dict):
        return {}

    return {
        link: value if _is_metrics(value) else _to_metrics(value)
        for link, value in data.items()
    }


ARCallReg.register_module(
    ARTrafficAiMeshSource,
    get_state=get_state,
    translate_state=translate_state,
)
