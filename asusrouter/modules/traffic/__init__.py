"""Traffic module for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import (
    ARTrafficLink,
    ARTrafficSource,
    ARTrafficType,
)
from asusrouter.modules.traffic.interface import ARTrafficInterfaceSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
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


def _content(results: Any) -> dict[ARTrafficLink, Any]:
    """Unwrap a single source's content from a fetch result."""

    if not isinstance(results, dict):
        return {}
    content: Any = next(iter(results.values()), {})
    return content if isinstance(content, dict) else {}


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
    # Skip AiMesh entirely for interface-only links to save a fetch
    aimesh: dict[ARTrafficLink, Any] = {}
    if link not in _INTERFACE_ONLY:
        aimesh = _content(
            await get_data_callback(ARTrafficAiMeshSource(link, target))
        )

    # Interface (counters + speeds) only for the connected router, and not
    # for the backhaul link which it cannot report
    interface: dict[ARTrafficLink, Any] = {}
    if is_self and link is not ARTrafficType.BACKHAUL:
        interface = _content(
            await get_data_callback(ARTrafficInterfaceSource(target))
        )
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


def translate_state(
    data: Any,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Pass through the already-merged traffic state."""

    return data if isinstance(data, dict) else {}


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}
ARCallReg.register(ARTrafficSource, **calls)
