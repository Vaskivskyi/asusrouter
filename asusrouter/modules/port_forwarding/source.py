"""Port forwarding data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.port_forwarding.enums import (
    ARPortForwardingField,
    ARPortForwardingProtocol,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers.ip import IpAddress, IpInterface
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

KEY_STATE = ARNvramType.PORT_FORWARDING_STATE
# Per-WAN rule lists; secondary is only populated on dual-WAN load-balance
_RULE_KEYS: dict[int, ARNvramType] = {
    0: ARNvramType.PORT_FORWARDING_LIST,
    1: ARNvramType.PORT_FORWARDING_LIST_SECONDARY,
}

# Full NVRAM request for the port forwarding state, built once
_PF_REQUEST: tuple[ARNvramType, ...] = (KEY_STATE, *_RULE_KEYS.values())

# nvram rule columns: name > external_port > internal_ip > internal_port >
# protocol > source_ip
_COL_NAME = 0
_COL_EXTERNAL_PORT = 1
_COL_INTERNAL_IP = 2
_COL_INTERNAL_PORT = 3
_COL_PROTOCOL = 4
_COL_SOURCE_IP = 5


class ARPortForwardingSource(ARDataSource):
    """AsusRouter port forwarding data source."""


# Universal instance - preferred
ARPortForwardingSourceUniversal: ARPortForwardingSource = (
    ARPortForwardingSource()
)


async def get_state(
    callback: ARCallbackType,
    source: ARPortForwardingSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the port forwarding configuration through the NVRAM module."""

    return await async_fetch_values(get_data_callback, _PF_REQUEST)


def _decode(raw: Any) -> str:
    """Decode the char-encoded nvram separators to `<`/`>`."""

    if not isinstance(raw, str):
        return ""
    return raw.replace("&#60", "<").replace("&#62", ">")


def _parse_rule(
    parts: list[str], wan_unit: int
) -> dict[ARPortForwardingField, Any]:
    """Build a single rule dict from its nvram columns."""

    def col(index: int) -> str | None:
        return parts[index] if len(parts) > index else None

    protocol = ARPortForwardingProtocol.from_value(col(_COL_PROTOCOL))

    rule: dict[ARPortForwardingField, Any] = {
        ARPortForwardingField.PROTOCOL: protocol,
        ARPortForwardingField.WAN_UNIT: wan_unit,
    }

    name = raw_to_str(col(_COL_NAME))
    if name is not None:
        rule[ARPortForwardingField.NAME] = name

    external = raw_to_str(col(_COL_EXTERNAL_PORT))
    if protocol is ARPortForwardingProtocol.OTHER:
        # For OTHER the external-port slot carries a raw IP protocol number
        number = raw_to_int(external)
        if number is not None:
            rule[ARPortForwardingField.PROTOCOL_NUMBER] = number
    elif external is not None:
        rule[ARPortForwardingField.EXTERNAL_PORT] = external

    internal_ip = IpAddress.from_value_safe(col(_COL_INTERNAL_IP))
    if internal_ip is not None:
        rule[ARPortForwardingField.INTERNAL_IP] = internal_ip

    internal_port = raw_to_str(col(_COL_INTERNAL_PORT))
    if internal_port is not None:
        rule[ARPortForwardingField.INTERNAL_PORT] = internal_port

    source_ip = IpInterface.from_value_safe(col(_COL_SOURCE_IP))
    if source_ip is not None:
        rule[ARPortForwardingField.SOURCE_IP] = source_ip

    return rule


def _parse_rules(
    raw: Any, wan_unit: int
) -> list[dict[ARPortForwardingField, Any]]:
    """Parse one WAN's rule list into rule dicts."""

    rules: list[dict[ARPortForwardingField, Any]] = []
    for row in _decode(raw).split("<"):
        if row == "":
            continue
        rules.append(_parse_rule(row.split(">"), wan_unit))

    return rules


def _rule_columns(rule: dict[ARPortForwardingField, Any]) -> list[str]:
    """Serialize a rule dict back into its ordered nvram columns."""

    protocol = ARPortForwardingProtocol.from_value(
        rule.get(ARPortForwardingField.PROTOCOL)
    )
    if protocol is ARPortForwardingProtocol.OTHER:
        external = rule.get(ARPortForwardingField.PROTOCOL_NUMBER)
    else:
        external = rule.get(ARPortForwardingField.EXTERNAL_PORT)

    # In nvram column order: name, external, internal_ip, internal_port,
    # protocol, source_ip
    values = (
        rule.get(ARPortForwardingField.NAME),
        external,
        rule.get(ARPortForwardingField.INTERNAL_IP),
        rule.get(ARPortForwardingField.INTERNAL_PORT),
        protocol,
        rule.get(ARPortForwardingField.SOURCE_IP),
    )
    return ["" if value is None else str(value) for value in values]


def serialize_rules(rules: list[dict[ARPortForwardingField, Any]]) -> str:
    """Serialize a list of rule dicts into the raw nvram list string."""

    return "".join(f"<{'>'.join(_rule_columns(rule))}" for rule in rules)


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARPortForwardingField, Any]:
    """Translate raw port forwarding nvram into a structured dict."""

    if not isinstance(data, dict) or not data:
        return {}

    rules: list[dict[ARPortForwardingField, Any]] = []
    for wan_unit, key in _RULE_KEYS.items():
        rules.extend(_parse_rules(data.get(key), wan_unit))

    return {
        ARPortForwardingField.STATE: raw_to_bool(data.get(KEY_STATE)) or False,
        ARPortForwardingField.RULES: rules,
    }


ARCallReg.register_module(
    ARPortForwardingSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARPortForwardingSource",
    "ARPortForwardingSourceUniversal",
    "get_state",
    "serialize_rules",
    "translate_state",
]
