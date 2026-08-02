"""Supported parental control."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.parental_control.enums import (
    ARParentalControlCapability,
)
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.converters.raw import raw_to_int

translate_parental_control = make_bool_translator(
    ARSupportValue.PARENTAL_CONTROL.value
)

_CAPABILITY_INTS = {
    ARSupportValue.PARENTAL_CONTROL_MAX_ENTRIES.value: (
        ARParentalControlCapability.MAX_ENTRIES
    ),
    ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: (
        ARParentalControlCapability.MAX_RULES
    ),
    ARSupportValue.PARENTAL_CONTROL_SCHED_VERSION.value: (
        ARParentalControlCapability.SCHED_VERSION
    ),
}


def translate_parental_control_capabilities(
    data: dict[str, Any],
) -> dict[ARParentalControlCapability, int]:
    """Map parental control limits and version, present only when reported."""

    capabilities: dict[ARParentalControlCapability, int] = {}

    for key, capability in _CAPABILITY_INTS.items():
        value = raw_to_int(data.get(key))
        if value:
            capabilities[capability] = value

    return capabilities
