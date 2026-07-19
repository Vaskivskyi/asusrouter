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
    """Connected clients count data source for the connected router."""


# Universal instance - preferred
ARClientsCountSourceUniversal: ARClientsCountSource = ARClientsCountSource()


def _build_request(mac: MacAddress) -> str:
    """Build the active-client diagnostics request for the router MAC."""

    return dict_to_request(
        {
            "ts": int(time.time()),
            "duration": _DIAG_DURATION,
            "point": _DIAG_POINT,
            "node_mac": mac.as_asus(),
        },
        request_type=_DIAG_REQUEST_TYPE,
    )


async def _fetch_modern(
    callback: ARCallbackType, mac: MacAddress
) -> int | None:
    """Fetch the newest connected-client count from diagnostics."""

    data = await callback(
        endpoint=AREndpoint.FETCH_DIAGNOSTICS_ACTIVE_CLIENT,
        request=_build_request(mac),
    )
    counts = data.get("count") if isinstance(data, dict) else None
    if not isinstance(counts, list) or not counts:
        return None

    return raw_to_int(counts[-1])


def _is_aiboard(client: ARClient) -> bool:
    """Whether the client is the device's own AI board."""

    name = client.name
    return name is not None and name.lower().startswith(_AIBOARD_NAME_PREFIX)


def _has_ai(identity: ARDeviceIdentity | None) -> bool:
    """Whether the device reports AI support (has an AI board)."""

    if identity is None:
        return False
    return bool(identity.support.get(ARSupportType.AI))


async def _fetch_legacy(
    callback: ARCallbackType, identity: ARDeviceIdentity | None
) -> int:
    """Count the online clients, excluding the AI board on AI devices."""

    raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.CLIENTLIST, ARHook.CLIENTLIST_DATABASE),
    )
    clients = build_clients(raw, identity)
    online = [client for client in clients.values() if client.online is True]

    total = len(online)
    if _has_ai(identity):
        total -= sum(1 for client in online if _is_aiboard(client))

    return total


async def fetch_state(
    callback: ARCallbackType,
    source: ARClientsCountSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> int:
    """Fetch the connected clients count, preferring the modern endpoint."""

    mac = identity.mac if identity is not None else None
    if mac is not None:
        modern = await _fetch_modern(callback, mac)
        if modern is not None:
            return modern

    return await _fetch_legacy(callback, identity)


ARCallReg.register_source(ARClientsCountSource, fetch_state=fetch_state)


__all__ = [
    "ARClientsCountSource",
    "ARClientsCountSourceUniversal",
    "fetch_state",
]
