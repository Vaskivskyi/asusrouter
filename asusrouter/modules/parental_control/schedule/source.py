"""Parental control data source for AsusRouter."""

from __future__ import annotations

from itertools import zip_longest
from typing import TYPE_CHECKING, Any

from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.parental_control.enums import (
    ARParentalControlField,
    ARParentalControlScheduleMode,
    ARParentalControlType,
)
from asusrouter.modules.parental_control.schedule.timemap import (
    DEFAULT_TIMEMAP,
    apply_mode,
    parse_timemap,
    serialize_timemap,
    timemap_mode,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_bool, raw_to_str
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.readers.nvram_list import decode
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Rules-engine master toggle
KEY_STATE = ARNvramType.PARENTAL_CONTROL_STATE
# Parallel per-rule lists, aligned by position and `>`-joined
KEY_MAC = ARNvramType.PARENTAL_CONTROL_MAC
KEY_NAME = ARNvramType.PARENTAL_CONTROL_NAME
KEY_TYPE = ARNvramType.PARENTAL_CONTROL_TYPE
KEY_TIMEMAP = ARNvramType.PARENTAL_CONTROL_TIMEMAP

# Full NVRAM request for the parental control state, built once
PC_REQUEST: tuple[ARNvramType, ...] = (
    KEY_STATE,
    KEY_MAC,
    KEY_NAME,
    KEY_TYPE,
    KEY_TIMEMAP,
)


class ARParentalControlSource(ARDataSource):
    """AsusRouter parental control data source."""


# Universal instance - preferred
ARParentalControlSourceUniversal: ARParentalControlSource = (
    ARParentalControlSource()
)


async def get_state(
    callback: ARCallbackType,
    source: ARParentalControlSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the parental control configuration through the NVRAM module."""

    return await async_fetch_values(get_data_callback, PC_REQUEST)


def _split_list(raw: Any) -> list[str]:
    """Decode a `>`-joined parallel list into its positional fields."""

    text = decode(raw)
    return text.split(">") if text else []


def rule_schedule_mode(
    rule: dict[ARParentalControlField, Any],
) -> ARParentalControlScheduleMode:
    """Resolve a rule's schedule mode: explicit MODE field else timemap."""

    mode = rule.get(ARParentalControlField.MODE)
    if mode is not None:
        return ARParentalControlScheduleMode.from_value(mode)
    return timemap_mode(str(rule.get(ARParentalControlField.TIMEMAP) or ""))


def rule_entry_count(rule: dict[ARParentalControlField, Any]) -> int:
    """Count the schedule windows a rule serializes to.

    Mirrors `_rule_timemap`: a parsed `SCHEDULE` wins, else the raw
    `TIMEMAP`, else the seeded default.
    """

    schedule = rule.get(ARParentalControlField.SCHEDULE)
    if schedule is not None:
        return len(schedule)
    raw = rule.get(ARParentalControlField.TIMEMAP)
    return len(parse_timemap(raw if raw else DEFAULT_TIMEMAP))


def _parse_rule(
    mac: str, name: str, type_: str, timemap: str
) -> dict[ARParentalControlField, Any]:
    """Build a single rule dict from its aligned list fields."""

    parsed_mac = MacAddress.from_value_safe(mac)
    timemap_str = raw_to_str(timemap) or ""

    return {
        ARParentalControlField.MAC: parsed_mac if parsed_mac else mac,
        ARParentalControlField.NAME: raw_to_str(name) or "",
        ARParentalControlField.TYPE: ARParentalControlType.from_value(type_),
        ARParentalControlField.MODE: timemap_mode(timemap_str),
        ARParentalControlField.SCHEDULE: parse_timemap(timemap_str),
        ARParentalControlField.TIMEMAP: timemap_str,
    }


def _parse_rules(
    data: dict[Any, Any],
) -> list[dict[ARParentalControlField, Any]]:
    """Parse the parallel per-rule lists into rule dicts."""

    # The four lists are positional; pad short ones so rows stay aligned
    rows = zip_longest(
        _split_list(data.get(KEY_MAC)),
        _split_list(data.get(KEY_NAME)),
        _split_list(data.get(KEY_TYPE)),
        _split_list(data.get(KEY_TIMEMAP)),
        fillvalue="",
    )

    return [
        _parse_rule(mac, name, type_, timemap)
        for mac, name, type_, timemap in rows
        if mac != ""
    ]


def _rule_timemap(rule: dict[ARParentalControlField, Any]) -> str:
    """Serialize a rule's timemap from its schedule entries, else the raw one.

    A parsed `SCHEDULE` is authoritative when present; otherwise the raw
    `TIMEMAP` string passes through. Either way the rule's mode is applied.
    """

    mode = rule_schedule_mode(rule)

    schedule = rule.get(ARParentalControlField.SCHEDULE)
    if schedule is not None:
        return serialize_timemap(schedule, mode)

    raw = str(rule.get(ARParentalControlField.TIMEMAP) or DEFAULT_TIMEMAP)
    return apply_mode(raw, mode)


def _rule_field(rule: dict[ARParentalControlField, Any]) -> tuple[str, ...]:
    """Serialize a rule dict into its (mac, name, type, timemap) fields."""

    mac = rule.get(ARParentalControlField.MAC)
    mac_str = mac.as_asus() if isinstance(mac, MacAddress) else str(mac or "")

    type_ = ARParentalControlType.from_value(
        rule.get(ARParentalControlField.TYPE)
    )

    return (
        mac_str,
        str(rule.get(ARParentalControlField.NAME) or ""),
        str(type_.value),
        _rule_timemap(rule),
    )


def serialize_rules(
    rules: list[dict[ARParentalControlField, Any]],
) -> dict[str, str]:
    """Serialize rule dicts into the parallel `>`-joined nvram lists."""

    columns = [_rule_field(rule) for rule in rules]
    return {
        KEY_MAC.value: ">".join(column[0] for column in columns),
        KEY_NAME.value: ">".join(column[1] for column in columns),
        KEY_TYPE.value: ">".join(column[2] for column in columns),
        KEY_TIMEMAP.value: ">".join(column[3] for column in columns),
    }


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARParentalControlField, Any]:
    """Translate raw parental control nvram into a structured dict."""

    if not isinstance(data, dict) or not data:
        return {}

    return {
        ARParentalControlField.STATE: raw_to_bool(data.get(KEY_STATE))
        or False,
        ARParentalControlField.RULES: _parse_rules(data),
    }


ARCallReg.register_module(
    ARParentalControlSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARParentalControlSource",
    "ARParentalControlSourceUniversal",
    "DEFAULT_TIMEMAP",
    "get_state",
    "rule_entry_count",
    "rule_schedule_mode",
    "serialize_rules",
    "translate_state",
]
