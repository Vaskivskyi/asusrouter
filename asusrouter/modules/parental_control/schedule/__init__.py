"""Time-scheduling sub-feature of parental control."""

from __future__ import annotations

from asusrouter.modules.parental_control.schedule.action import (
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_RULES,
    SCHEDULE_MODE_MIN_VERSION,
    ARParentalControlAction,
    ARParentalControlRule,
    run_action,
)
from asusrouter.modules.parental_control.schedule.source import (
    ARParentalControlSource,
    ARParentalControlSourceUniversal,
    fetch_state,
    rule_entry_count,
    rule_schedule_mode,
    serialize_rules,
    translate_state,
)
from asusrouter.modules.parental_control.schedule.timemap import (
    DAILY,
    DEFAULT_TIMEMAP,
    WEEKDAYS,
    WEEKEND,
    ARScheduleEntry,
    parse_timemap,
    serialize_timemap,
    timemap_mode,
)

__all__ = [
    "DAILY",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_RULES",
    "DEFAULT_TIMEMAP",
    "SCHEDULE_MODE_MIN_VERSION",
    "WEEKDAYS",
    "WEEKEND",
    "ARParentalControlAction",
    "ARParentalControlRule",
    "ARParentalControlSource",
    "ARParentalControlSourceUniversal",
    "ARScheduleEntry",
    "fetch_state",
    "parse_timemap",
    "rule_entry_count",
    "rule_schedule_mode",
    "run_action",
    "serialize_rules",
    "serialize_timemap",
    "timemap_mode",
    "translate_state",
]
