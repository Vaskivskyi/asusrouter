"""Data transform module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wan import ARWANCapability


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
