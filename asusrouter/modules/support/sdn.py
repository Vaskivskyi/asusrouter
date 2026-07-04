"""Supported SDN."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_int_translator

# All SDN support flags are reported as integers (counts or 0/1 toggles)
translate_sdn_awv = make_int_translator(ARSupportValue.SDN_AWV.value)
translate_sdn_mainfh = make_int_translator(ARSupportValue.SDN_MAINFH.value)
translate_sdn_max_rules = make_int_translator(
    ARSupportValue.SDN_MAX_RULES.value
)
translate_sdn_mwl = make_int_translator(ARSupportValue.SDN_MWL.value)
translate_sdn_priority = make_int_translator(ARSupportValue.SDN_PRIORITY.value)
