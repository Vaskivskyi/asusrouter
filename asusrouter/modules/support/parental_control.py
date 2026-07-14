"""Supported parental control."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_int_translator

# Max number of per-client rules the router accepts (0 when unreported)
translate_parental_control_max_rules = make_int_translator(
    ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value
)

# Max total schedule windows across all rules (0 when unreported)
translate_parental_control_max_entries = make_int_translator(
    ARSupportValue.PARENTAL_CONTROL_MAX_ENTRIES.value
)

# Time-scheduling generation; >= 3 accepts the online (allow-only) mode
translate_parental_control_sched_version = make_int_translator(
    ARSupportValue.PARENTAL_CONTROL_SCHED_VERSION.value
)
