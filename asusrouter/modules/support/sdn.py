"""Supported SDN."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.network.enums import ARSDNCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.converters.raw import raw_to_int

translate_sdn = make_bool_translator(ARSupportValue.SDN.value)

_CAPABILITY_INTS = {
    ARSupportValue.SDN_AWV.value: ARSDNCapability.AWV,
    ARSupportValue.SDN_MAINFH.value: ARSDNCapability.MAIN_FRONTHAUL,
    ARSupportValue.SDN_MAX_RULES.value: ARSDNCapability.MAX_RULES,
    ARSupportValue.SDN_MWL.value: ARSDNCapability.MWL,
    ARSupportValue.SDN_PRIORITY.value: ARSDNCapability.PRIORITY,
}


def translate_sdn_capabilities(
    data: dict[str, Any],
) -> dict[ARSDNCapability, int]:
    """Map SDN capabilities, each present only when reported."""

    capabilities: dict[ARSDNCapability, int] = {}
    for key, capability in _CAPABILITY_INTS.items():
        value = raw_to_int(data.get(key))
        if value:
            capabilities[capability] = value
    return capabilities
