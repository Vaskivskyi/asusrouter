"""DDNS data source for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from asusrouter.modules.ddns.enums import (
    ARDdnsField,
    ARDdnsServer,
    ARDdnsStatus,
)
from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import Hostname, IpAddress, Password
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Numeric status codes matched as substrings, e.g. `register,230`
# The values are distinct, so match order does not matter
_STATUS_CODES: tuple[ARDdnsStatus, ...] = tuple(
    status for status in ARDdnsStatus if status.value.lstrip("-").isdigit()
)


class ARDdnsSource(ARDataSource):
    """AsusRouter DDNS data source."""


# Universal instance - preferred
ARDdnsSourceUniversal: ARDdnsSource = ARDdnsSource()


async def get_state(
    callback: ARCallbackType,
    source: ARDdnsSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the DDNS configuration through the NVRAM module."""

    return await async_fetch_values(get_data_callback, DDNS_REQUEST)


def read_status(raw: Any) -> ARDdnsStatus:
    """Read the DDNS status from a raw return code."""

    value = raw_to_str(raw)
    if value is None:
        return ARDdnsStatus.NONE

    # Text statuses are full-string values
    status = ARDdnsStatus.from_value(value)
    if status is not ARDdnsStatus.UNKNOWN:
        return status

    # Numeric codes can be embedded in a longer string
    for code in _STATUS_CODES:
        if code.value in value:
            return code

    return ARDdnsStatus.UNKNOWN


def _read_server(raw: Any) -> ARDdnsServer | None:
    """Read the DDNS server, None when not selected."""

    value = raw_to_str(raw)
    if value is None:
        return None
    return ARDdnsServer.from_value(value)


def _read_state(raw: Any) -> bool:
    """Read the master DDNS state."""

    return raw_to_bool(raw) or False


# Translation map: nvram key -> field, converter
_TRANSLATION: tuple[
    tuple[ARNvramType, ARDdnsField, Callable[[Any], Any]], ...
] = (
    (
        ARNvramType.DDNS_HOSTNAME,
        ARDdnsField.HOSTNAME,
        Hostname.from_value_safe,
    ),
    (
        ARNvramType.DDNS_HOSTNAME_OLD,
        ARDdnsField.HOSTNAME_OLD,
        Hostname.from_value_safe,
    ),
    (
        ARNvramType.DDNS_IP_ADDRESS,
        ARDdnsField.IP_ADDRESS,
        IpAddress.from_value_safe,
    ),
    (ARNvramType.DDNS_IPV6_UPDATE, ARDdnsField.IPV6_UPDATE, raw_to_bool),
    (
        ARNvramType.DDNS_PASSWORD,
        ARDdnsField.PASSWORD,
        Password.from_value_safe,
    ),
    (
        ARNvramType.DDNS_REFRESH_INTERVAL,
        ARDdnsField.REFRESH_INTERVAL,
        raw_to_int,
    ),
    (ARNvramType.DDNS_REGULAR_CHECK, ARDdnsField.VERIFICATION, raw_to_bool),
    (
        ARNvramType.DDNS_REGULAR_PERIOD,
        ARDdnsField.VERIFICATION_PERIOD,
        raw_to_int,
    ),
    (ARNvramType.DDNS_REPLACE_STATUS, ARDdnsField.REPLACE_STATUS, raw_to_bool),
    (ARNvramType.DDNS_RETURN_CODE_CHK, ARDdnsField.STATUS, read_status),
    (ARNvramType.DDNS_SERVER, ARDdnsField.SERVER, _read_server),
    (ARNvramType.DDNS_STATE, ARDdnsField.STATE, _read_state),
    (ARNvramType.DDNS_TOKEN_STATE, ARDdnsField.TOKEN_STATE, raw_to_bool),
    (ARNvramType.DDNS_UPDATED, ARDdnsField.UPDATED, raw_to_bool),
    (ARNvramType.DDNS_USERNAME, ARDdnsField.USERNAME, raw_to_str),
    (ARNvramType.DDNS_WAN_UNIT, ARDdnsField.WAN_UNIT, raw_to_int),
    (ARNvramType.DDNS_WILDCARD, ARDdnsField.WILDCARD, raw_to_bool),
)

# Full NVRAM request for the DDNS state, built once
DDNS_REQUEST: tuple[ARNvramType, ...] = tuple(
    key for key, _, _ in _TRANSLATION
)


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARDdnsField, Any]:
    """Translate raw DDNS nvram into a structured dict."""

    if not isinstance(data, dict) or not data:
        return {}

    return {
        field: convert(data.get(key)) for key, field, convert in _TRANSLATION
    }


ARCallReg.register_module(
    ARDdnsSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARDdnsSource",
    "ARDdnsSourceUniversal",
    "DDNS_REQUEST",
    "get_state",
    "read_status",
    "translate_state",
]
