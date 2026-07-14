"""Parental control enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARParentalControlCommand(FromStrMixin, StrEnum):
    """The mutation an action performs on parental control."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ADD = "add"
    REMOVE = "remove"
    SET = "set"
    STATE = "state"


class ARParentalControlType(FromIntMixin, IntEnum):
    """Per-rule type. Values are the device `MULTIFILTER_ENABLE` codes."""

    UNKNOWN = UNKNOWN_MEMBER

    DISABLE = 0
    TIME = 1  # follow the timemap schedule (offline/online per mode)
    BLOCK = 2  # block at all times


class ARWeekday(FromIntMixin, IntEnum):
    """Day of week. Values are the timemap weekday bitmap positions."""

    UNKNOWN = UNKNOWN_MEMBER

    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class ARParentalControlScheduleMode(FromStrMixin, StrEnum):
    """Per-rule schedule mode. Values are the timemap entry prefix char.

    Only relevant for a `TIME` rule; the router's `PC_SCHED_V3` support
    must be at least 3 for a device to accept the online mode.
    """

    UNKNOWN = UNKNOWN_MEMBER_STR

    OFFLINE = "W"  # block internet during the scheduled windows
    ONLINE = "M"  # allow internet only during the scheduled windows


class ARParentalControlField(FromStrMixin, StrEnum):
    """Keys of the parental control data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    MAC = "mac"
    MODE = "mode"  # schedule mode of a TIME rule (offline/online)
    NAME = "name"
    RULES = "rules"
    SCHEDULE = "schedule"  # parsed timemap windows (list of entries)
    STATE = "state"  # rules-engine (time-scheduling) master on/off
    TIMEMAP = "timemap"  # raw weekly schedule string
    TYPE = "type"


__all__ = [
    "ARParentalControlCommand",
    "ARParentalControlField",
    "ARParentalControlScheduleMode",
    "ARParentalControlType",
    "ARWeekday",
]
