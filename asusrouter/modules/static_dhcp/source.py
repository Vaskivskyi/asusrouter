"""Static DHCP data source for AsusRouter."""

from __future__ import annotations

import logging
from typing import Any

from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.static_dhcp.enums import ARStaticDHCPField
from asusrouter.modules.static_dhcp.model import parse_static_dhcp_leases
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_bool
from asusrouter.tools.types import ARCallbackType

_LOGGER = logging.getLogger(__name__)

STATIC_DHCP_REQUEST: tuple[ARNvramType, ...] = (
    ARNvramType.STATIC_DHCP_STATE,
    ARNvramType.STATIC_DHCP_LIST,
)


class ARStaticDHCPSource(ARDataSource):
    """AsusRouter static DHCP data source."""


ARStaticDHCPSourceUniversal = ARStaticDHCPSource()


async def fetch_state(
    callback: ARCallbackType,
    source: ARStaticDHCPSource,
    *,
    fetch_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch static DHCP configuration through the NVRAM module."""

    return await async_fetch_values(fetch_data_callback, STATIC_DHCP_REQUEST)


def translate_state(data: Any, **kwargs: Any) -> dict[ARStaticDHCPField, Any]:
    """Translate raw NVRAM while preserving disabled saved reservations."""

    if not isinstance(data, dict) or not data:
        return {}

    state_present = ARNvramType.STATIC_DHCP_STATE in data
    raw_list = data.get(ARNvramType.STATIC_DHCP_LIST)
    list_present = isinstance(raw_list, str)
    state = raw_to_bool(data.get(ARNvramType.STATIC_DHCP_STATE))

    try:
        leases = parse_static_dhcp_leases(raw_list)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "Static DHCP data contains an unrecognized row; mutations disabled"
        )
        leases = []
        complete = False
    else:
        complete = state_present and list_present and state is not None

    return {
        ARStaticDHCPField.COMPLETE: complete,
        ARStaticDHCPField.LEASES: leases,
        ARStaticDHCPField.STATE: state,
    }


ARCallReg.register_source(
    ARStaticDHCPSource,
    fetch_state=fetch_state,
    translate_state=translate_state,
)


__all__ = [
    "STATIC_DHCP_REQUEST",
    "ARStaticDHCPSource",
    "ARStaticDHCPSourceUniversal",
    "fetch_state",
    "translate_state",
]
