"""Supported DSL."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator

translate_dsl = make_bool_translator(ARSupportValue.DSL.value)
