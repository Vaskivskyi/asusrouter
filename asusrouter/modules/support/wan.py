"""Supported WAN."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.modules.wan import ARWANCapability
from asusrouter.tools.converters import safe_int_nn
from asusrouter.tools.readers import is_true_in_dict

translate_wan = make_bool_translator(
    ARSupportValue.WAN_NOWAN.value, negate=True
)


def translate_wan_capabilities(data: dict[str, Any]) -> list[ARWANCapability]:
    """Translate WAN capabilities support data."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    result: list[ARWANCapability] = []

    if is_true_in_dict(ARSupportValue.WAN_AGGREGATION.value, data):
        result.append(ARWANCapability.AGGREGATION)

    if is_true_in_dict(ARSupportValue.WAN_DUALWAN.value, data):
        result.append(ARWANCapability.DUALWAN)

    return result


def translate_wan_limit(data: dict[str, Any]) -> int:
    """Translate WAN limit support data."""

    if not isinstance(data, dict):
        return 0  # type: ignore[unreachable]

    return safe_int_nn(data.get(ARSupportValue.WAN_LIMIT.value))
