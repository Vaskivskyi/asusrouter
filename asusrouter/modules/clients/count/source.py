"""Connected clients count data source for AsusRouter."""

from __future__ import annotations

import time
from typing import Any

from asusrouter.modules.clients.model import ARClient
from asusrouter.modules.clients.translate import build_clients
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_request_type
from asusrouter.modules.endpoint.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import dict_to_request

# Diagnostics window: newest of several points; 60/30 matches the device
_DIAG_DURATION = 60
_DIAG_POINT = 30
_DIAG_REQUEST_TYPE = get_endpoint_request_type(
    AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT
)

# Don't count AI board (starts with prefix) when counting online clients
_AIBOARD_NAME_PREFIX = "aiboard"


class ARClientsCountSource(ARDataSource):
    """Connected clients count data source."""

    def __init__(self, target: Any = None) -> None:
        """Initialize the source with an optional target MAC."""

        super().__init__()

        self._target: MacAddress | None = None
        self.target = target

    @property
    def target(self) -> MacAddress | None:
        """Get the target MAC address."""

        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        """Set the target MAC address."""

        self._target = MacAddress.from_value_safe(value)

    def _key(self) -> tuple[Any, ...]:
        """Key by the target MAC."""

        return (self._target,)


# Universal instance - preferred (targets all nodes)
ARClientsCountSourceUniversal: ARClientsCountSource = ARClientsCountSource()


def _build_request(mac: MacAddress) -> str:
    """Build the active-client diagnostics request for one node MAC."""

    return dict_to_request(
        {
            "ts": int(time.time()),
            "duration": _DIAG_DURATION,
            "point": _DIAG_POINT,
            "node_mac": mac.as_asus(),
        },
        request_type=_DIAG_REQUEST_TYPE,
    )


async def _fetch_modern_one(
    callback: ARCallbackType, mac: MacAddress
) -> int | None:
    """Fetch the newest connected-client count for one node."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT,
        request=_build_request(mac),
    )
    counts = data.get("count") if isinstance(data, dict) else None
    if not isinstance(counts, list) or not counts:
        return None

    # A refresh can momentarily report 0; fall back one point only
    last = raw_to_int(counts[-1])
    if last == 0:
        prev_point = counts[-2:-1]
        prev = raw_to_int(prev_point[0]) if prev_point else None
        if prev:
            return prev

    return last


def _is_aiboard(client: ARClient) -> bool:
    """Whether the client is the device's own AI board."""

    name = client.name
    return name is not None and name.lower().startswith(_AIBOARD_NAME_PREFIX)


def _target_macs(
    source: ARClientsCountSource, identity: ARDeviceIdentity
) -> list[MacAddress]:
    """Resolve the nodes to report: the target, else all known nodes."""

    if source.target is not None:
        return [source.target]
    nodes = identity.aimesh.macs()
    if nodes:
        return nodes
    return [identity.mac] if identity.mac is not None else []


async def _fetch_modern(
    callback: ARCallbackType, macs: list[MacAddress]
) -> dict[MacAddress, int]:
    """Fetch the per-node counts from the active-client diagnostics."""

    result: dict[MacAddress, int] = {}
    for mac in macs:
        count = await _fetch_modern_one(callback, mac)
        if count is not None:
            result[mac] = count
    return result


async def _fetch_legacy(
    callback: ARCallbackType,
    identity: ARDeviceIdentity,
    macs: list[MacAddress],
) -> dict[MacAddress, int]:
    """Count the online clients per node, excluding the AI board."""

    raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.CLIENTLIST, ARHook.CLIENTLIST_DATABASE),
    )
    clients = build_clients(raw, identity)
    skip_aiboard = bool(identity.support.get(ARSupportType.AI))

    per_node: dict[MacAddress, int] = {}
    for client in clients.values():
        if client.online is not True or client.connection is None:
            continue
        if skip_aiboard and _is_aiboard(client):
            continue
        node = client.connection.node
        if node is not None:
            per_node[node] = per_node.get(node, 0) + 1

    # Report every requested node, filling absent ones with zero
    return {mac: per_node.get(mac, 0) for mac in macs}


async def fetch_state(
    callback: ARCallbackType,
    source: ARClientsCountSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[MacAddress, int]:
    """Fetch per-node connected clients counts, preferring diagnostics."""

    macs = _target_macs(source, identity)
    if not macs:
        return {}

    modern = await _fetch_modern(callback, macs)
    if modern:
        return modern

    return await _fetch_legacy(callback, identity, macs)


ARCallReg.register_source(ARClientsCountSource, fetch_state=fetch_state)


__all__ = [
    "ARClientsCountSource",
    "ARClientsCountSourceUniversal",
    "fetch_state",
]
