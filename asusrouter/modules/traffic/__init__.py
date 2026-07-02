"""Traffic module for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import (
    ARTrafficLink,
    ARTrafficSource,
    ARTrafficType,
)
from asusrouter.modules.traffic.interface import ARTrafficInterfaceSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.types import ARCallbackType

__all__ = [
    "ARTrafficAiMeshSource",
    "ARTrafficInterfaceSource",
    "ARTrafficLink",
    "ARTrafficSource",
    "ARTrafficType",
]

# Links served only by the interface submodule (no AiMesh fetch for them)
_INTERFACE_ONLY: frozenset[ARTrafficType] = frozenset(
    {
        ARTrafficType.WAN,
        ARTrafficType.USB,
        ARTrafficType.BRIDGE,
        ARTrafficType.LACP,
        ARTrafficType.LACP1,
        ARTrafficType.LACP2,
    }
)


def _content(value: Any) -> dict[ARTrafficLink, Any]:
    """Coerce a fetched source content to a dict."""

    return value if isinstance(value, dict) else {}


async def get_state(
    callback: ARCallbackType,
    source: ARTrafficSource,
    *,
    identity: ARDeviceIdentity | None = None,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Dispatch and merge AiMesh and interface traffic for the source."""

    if get_data_callback is None:
        return {}

    target = source.target
    link = source.link
    is_self = target is None or (
        identity is not None and target == identity.mac
    )

    # AiMesh serves bands / WIRED / BACKHAUL; interface serves the rest.
    # Both go into one pipeline request, so they are fetched concurrently
    aimesh_source: ARTrafficAiMeshSource | None = None
    interface_source: ARTrafficInterfaceSource | None = None
    request: list[ARDataSource] = []
    if link not in _INTERFACE_ONLY:
        aimesh_source = ARTrafficAiMeshSource(link, target)
        request.append(aimesh_source)
    # Interface (counters + speeds) only for the connected router, and not
    # for the backhaul link which it cannot report
    if is_self and link is not ARTrafficType.BACKHAUL:
        interface_source = ARTrafficInterfaceSource(target)
        request.append(interface_source)

    if not request:
        return {}

    results = await get_data_callback(request)
    if not isinstance(results, dict):
        results = {}

    aimesh = _content(results.get(aimesh_source))
    interface = _content(results.get(interface_source))
    if link is not None:
        interface = {link: interface[link]} if link in interface else {}

    # Interface is the base (byte counters); AiMesh overlays it and wins on
    # shared keys (its measured speeds are more precise than netdev deltas)
    merged: dict[ARTrafficLink, Any] = {
        key: dict(value) for key, value in interface.items()
    }
    for key, value in aimesh.items():
        merged[key] = {**merged.get(key, {}), **value}
    return merged


ARCallReg.register_module(ARTrafficSource, get_state=get_state)
