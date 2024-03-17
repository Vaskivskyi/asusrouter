"""Parental control module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.tools.converters import safe_int, safe_return

KEY_PC_BLOCK_ALL = "MULTIFILTER_BLOCK_ALL"
KEY_PC_MAC = "MULTIFILTER_MAC"
KEY_PC_NAME = "MULTIFILTER_DEVICENAME"
KEY_PC_STATE = "MULTIFILTER_ALL"
KEY_PC_TIMEMAP = "MULTIFILTER_MACFILTER_DAYTIME_V2"
KEY_PC_TYPE = "MULTIFILTER_ENABLE"

PC_RULE_MAP = {
    KEY_PC_MAC: "mac",
    KEY_PC_NAME: "name",
    KEY_PC_TIMEMAP: "timemap",
    KEY_PC_TYPE: "type",
}

HOOK_PC = [
    KEY_PC_BLOCK_ALL,
    KEY_PC_MAC,
    KEY_PC_NAME,
    KEY_PC_STATE,
    KEY_PC_TIMEMAP,
    KEY_PC_TYPE,
]


DEFAULT_PC_TIMEMAP = "W03E21000700<W04122000800"


class PCRuleType(IntEnum):
    """Parental control rule type."""

    UNKNOWN = -999
    REMOVE = -1  # pseudo type to remove a rule
    DISABLE = 0
    TIME = 1
    BLOCK = 2


@dataclass
class ParentalControlRule:
    """Parental control rule class."""

    mac: Optional[str] = None
    name: str = ""
    timemap: str = DEFAULT_PC_TIMEMAP
    type: PCRuleType = PCRuleType.UNKNOWN


class AsusParentalControl(IntEnum):
    """Asus parental control state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


class AsusBlockAll(IntEnum):
    """Asus block all state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusParentalControl | AsusBlockAll | ParentalControlRule,
    **kwargs: Any,
) -> bool:
    """Set the parental control state."""

    # Check if we need to set a rule
    if isinstance(state, ParentalControlRule):
        return await set_rule(callback, state, **kwargs)

    # Check if state is available and valid
    if not isinstance(
        state, (AsusParentalControl, AsusBlockAll)
    ) or not state.value in (0, 1):
        return False

    service_arguments = {}

    match state:
        case a if isinstance(a, AsusParentalControl):
            service_arguments = {
                KEY_PC_STATE: 1 if state == AsusParentalControl.ON else 0
            }
        case a if isinstance(a, AsusBlockAll):
            service_arguments = {KEY_PC_BLOCK_ALL: 1 if state == AsusBlockAll.ON else 0}

    # Get the correct service call
    service = "restart_firewall"

    # Call the service
    return await callback(
        service=service,
        arguments=service_arguments,
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )


async def set_rule(
    callback: Callable[..., Awaitable[bool]],
    rule: ParentalControlRule,
    **kwargs: Any,
) -> bool:
    """Set the parental control rule."""

    # Check if rule is available
    if not isinstance(rule, ParentalControlRule):
        return False

    # Get the current rules
    current_rules = (
        kwargs.get("router_state", {})
        .get(AsusData.PARENTAL_CONTROL, AsusDataState(data={}))
        .data.get("rules", {})
    )

    # Get rule action
    # If the rule is not available, we need to add it
    # update can also be handled as add
    action = add_rule
    if rule.type == PCRuleType.REMOVE:
        action = remove_rule

    # Perform the action
    current_rules = action(current_rules, rule)

    # Convert the rules to service arguments
    service_arguments = write_pc_rules(current_rules)

    # Get the correct service call
    service = "restart_firewall"

    # Call the service
    return await callback(
        service=service,
        arguments=service_arguments,
        apply=True,
    )


def check_rule(rule: Optional[ParentalControlRule]) -> Optional[ParentalControlRule]:
    """Check the parental control rule."""

    # Check if rule is available
    if not isinstance(rule, ParentalControlRule):
        return None

    # Check that mac is available
    if rule.mac is None:
        return None

    # Check that type is available and valid
    if not isinstance(rule.type, PCRuleType) or rule.type not in (
        PCRuleType.DISABLE,
        PCRuleType.TIME,
        PCRuleType.BLOCK,
    ):
        return None

    # Check that timemap is available and valid
    if not rule.timemap.strip():
        rule.timemap = DEFAULT_PC_TIMEMAP

    # Check that name is available
    if not rule.name.strip():
        rule.name = rule.mac

    # Return the rule
    return rule


def add_rule(
    current_rules: dict[str, ParentalControlRule],
    rule: Optional[ParentalControlRule] = None,
) -> dict[str, ParentalControlRule]:
    """Add a rule."""

    # Check that the current rules are available
    if not isinstance(current_rules, dict):
        current_rules = {}

    # Check if rule is available and valid
    rule = check_rule(rule)
    if rule is None or rule.mac is None:
        return current_rules

    # Add the new rule
    # This will also overwrite (update) the old rule if it exists
    current_rules[rule.mac] = rule

    return current_rules


def remove_rule(
    current_rules: dict[str, ParentalControlRule],
    rule: Optional[ParentalControlRule | str] = None,
) -> dict[str, ParentalControlRule]:
    """Remove a rule."""

    # Check that the current rules are available
    if not isinstance(current_rules, dict):
        current_rules = {}

    rule_mac = (
        rule.mac
        if isinstance(rule, ParentalControlRule)
        else rule
        if isinstance(rule, str)
        else None
    )

    # If mac is available, remove the rule
    if rule_mac is not None:
        current_rules.pop(rule_mac, None)

    return current_rules


def read_pc_string(key: str, data: dict[str, str]) -> list[str]:
    """Read the parental control string."""

    return data.get(key, "").split("&#62")


def read_pc_rules(data: dict[str, str]) -> dict[str, ParentalControlRule]:
    """Read the parental control data."""

    # If no data is provided, return empty list
    if data.get(KEY_PC_MAC) == data.get(KEY_PC_TYPE):
        return {}

    # The data is split in 4 strings. Each data value is split in the string
    # with a `&#62` separator. We need to map the data and make sure, that
    # each `ParentalControlRule` has all values

    # Map the values to a list of `ParentalControlRule`
    rules = {}
    for rule_mac, rule_name, rule_timemap, rule_type in zip(
        *[read_pc_string(key, data) for key in PC_RULE_MAP]
    ):
        # Map the values
        rule = ParentalControlRule(
            mac=safe_return(rule_mac),
            name=safe_return(rule_name),
            timemap=safe_return(rule_timemap),
            type=PCRuleType(safe_int(rule_type, default=-999)),
        )

        # Append the rule to the list
        rules[rule_mac] = rule

    return rules


def write_pc_rules(rules: dict[str, ParentalControlRule]) -> dict[str, str]:
    """Write the parental control data."""

    # If no rules are provided, return empty dict
    if not rules:
        return {key: "" for key in PC_RULE_MAP}

    # Join the values together
    data = {}
    for key, attribute in PC_RULE_MAP.items():
        data[key] = ">".join(
            str(getattr(rule, attribute, "")) for rule in rules.values()
        )

    data[KEY_PC_TIMEMAP] = data[KEY_PC_TIMEMAP].replace("&#60", "<")

    return data
