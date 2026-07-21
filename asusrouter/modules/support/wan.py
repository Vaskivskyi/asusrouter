"""Supported WAN."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.modules.wan import ARWANCapability
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

translate_wan = make_bool_translator(
    ARSupportValue.WAN_NOWAN.value, negate=True
)

_CAPABILITY_FLAGS = {
    ARSupportValue.WAN_AGGREGATION.value: ARWANCapability.AGGREGATION,
    ARSupportValue.WAN_DUALWAN.value: ARWANCapability.DUALWAN,
}


def translate_wan_capabilities(
    data: dict[str, Any],
) -> dict[ARWANCapability, bool | int]:
    """Map advertised WAN capabilities; LIMIT carries the port count."""

    capabilities: dict[ARWANCapability, bool | int] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }

    limit = raw_to_int(data.get(ARSupportValue.WAN_LIMIT.value))
    if limit:
        capabilities[ARWANCapability.LIMIT] = limit

    return capabilities
