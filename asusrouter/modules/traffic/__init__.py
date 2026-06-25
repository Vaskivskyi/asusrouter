"""Traffic supermodule.

Umbrella over the traffic submodules. `ARTrafficSource` is the public,
backend-agnostic source: it dispatches to the right submodule
(`aimesh` for now; `interface` and per-client traffic join later as
sibling submodules). Importing this package registers all callables.
"""

from __future__ import annotations

from typing import Any

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.traffic.aimesh import ARTrafficAiMeshSource
from asusrouter.modules.traffic.base import (
    ARTrafficLink,
    ARTrafficSource,
    ARTrafficType,
)
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.types import ARCallbackType

__all__ = [
    "ARTrafficAiMeshSource",
    "ARTrafficLink",
    "ARTrafficSource",
    "ARTrafficType",
]


async def get_state(
    callback: ARCallbackType,
    source: ARTrafficSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[ARTrafficLink, Any]:
    """Dispatch the traffic request to the backend submodules."""

    if get_data_callback is None:
        return {}

    # Only AiMesh exists today; interface joins here later
    delegate = ARTrafficAiMeshSource(source.link, source.target)
    results = await get_data_callback(delegate)
    if isinstance(results, dict):
        content: Any = next(iter(results.values()), {})
        return content if isinstance(content, dict) else {}
    return {}


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
