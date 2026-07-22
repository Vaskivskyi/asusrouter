"""Supported Aura features."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.aura.enums import ARAuraCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

translate_aura = make_bool_translator(ARSupportValue.AURA.value)


def translate_aura_capabilities(
    data: dict[str, Any],
) -> dict[ARAuraCapability, bool | int]:
    """Map advertised Aura capabilities; ZONE carries the zone count."""

    capabilities: dict[ARAuraCapability, bool | int] = {}

    if is_true_in_dict(ARSupportValue.AURA_NIGHT_MODE.value, data):
        capabilities[ARAuraCapability.NIGHT_MODE] = True

    zones = raw_to_int(data.get(ARSupportValue.AURA_ZONE.value))
    if zones:
        capabilities[ARAuraCapability.ZONE] = zones

    return capabilities
