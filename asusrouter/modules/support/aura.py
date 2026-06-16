"""Supported Aura features."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
)

translate_aura = make_bool_translator(ARSupportValue.AURA.value)
translate_aura_night_mode = make_bool_translator(
    ARSupportValue.AURA_NIGHT_MODE.value
)
translate_aura_zone = make_int_translator(ARSupportValue.AURA_ZONE.value)
