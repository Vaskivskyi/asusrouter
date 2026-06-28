"""Clients module for AsusRouter."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.clients.model import (
    ARClient,
    ARClientConnection,
    ARClientLink,
)
from asusrouter.modules.clients.translate import build_clients
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType

__all__ = [
    "ARClient",
    "ARClientConnection",
    "ARClientLink",
    "ARClientsSource",
    "ARClientsSourceUniversal",
]


class ARClientsSource(ARDataSource):
    """Clients data source for the connected router."""

    def __init__(self) -> None:
        """Initialize the clients source."""

        super().__init__()

        self._prev: dict[MacAddress, ARClient] = {}

    def __eq__(self, other: object) -> bool:
        """All clients sources are equal (router-global)."""

        if not isinstance(other, ARClientsSource):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        """Hash by type."""

        return hash(type(self))

    def __repr__(self) -> str:
        """Representation of the clients source."""

        return "<ARClientsSource>"

    def merge_history(
        self, current: dict[MacAddress, ARClient]
    ) -> dict[MacAddress, ARClient]:
        """Keep previously seen clients that vanished, marked offline."""

        result = dict(current)
        for mac, client in self._prev.items():
            if mac not in result:
                result[mac] = replace(client, online=False, connection=None)
        self._prev = result
        return result


# Universal instance - preferred
ARClientsSourceUniversal: ARClientsSource = ARClientsSource()


async def get_state(
    callback: ARCallbackType,
    source: ARClientsSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[MacAddress, ARClient]:
    """Fetch and build the client list, retaining vanished clients."""

    raw = await callback(
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(ARHook.CLIENTLIST, ARHook.CLIENTLIST_DATABASE),
    )
    return source.merge_history(build_clients(raw, identity))


def translate_state(
    data: Any,
    **kwargs: Any,
) -> dict[MacAddress, ARClient]:
    """Pass the built clients through."""

    return data if isinstance(data, dict) else {}


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}
ARCallReg.register(ARClientsSource, **calls)
