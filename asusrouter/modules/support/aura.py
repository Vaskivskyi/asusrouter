"""Supported Aura features."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.converters import safe_int_nn

translate_aura = make_bool_translator(ARSupportValue.AURA.value)
translate_aura_night_mode = make_bool_translator(
    ARSupportValue.AURA_NIGHT_MODE.value
)


def translate_aura_zone(data: dict[str, bool]) -> int:
    """Translate Aura zone count."""

    if isinstance(data, dict):
        return safe_int_nn(data.get(ARSupportValue.AURA_ZONE.value))

    return 0  # type: ignore[unreachable]
