"""Supported Aura features."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.converters import safe_bool_nn, safe_int_nn


def translate_aura(data: dict[str, bool]) -> bool:
    """Translate Aura presence."""

    if isinstance(data, dict):
        return safe_bool_nn(data.get(ARSupportValue.AURA.value))

    return False  # type: ignore[unreachable]


def translate_aura_night_mode(data: dict[str, bool]) -> bool:
    """Translate Aura night mode presence."""

    if isinstance(data, dict):
        return safe_bool_nn(data.get(ARSupportValue.AURA_NIGHT_MODE.value))

    return False  # type: ignore[unreachable]


def translate_aura_zone(data: dict[str, bool]) -> int:
    """Translate Aura zone count."""

    if isinstance(data, dict):
        return safe_int_nn(data.get(ARSupportValue.AURA_ZONE.value))

    return 0  # type: ignore[unreachable]
