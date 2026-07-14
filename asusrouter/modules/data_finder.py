"""Data finder module."""

from __future__ import annotations

from collections.abc import Callable
import logging

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.tools import converters

_LOGGER = logging.getLogger(__name__)


class AsusDataFinder:
    """AsusRouter data finder class."""

    def __init__(
        self,
        endpoint: list[AREndpoint] | AREndpoint,
        request: list[tuple[str, ...]] | None = None,
        nvram: list[str] | str | None = None,
        method: Callable | None = None,
    ) -> None:
        """Initialize the data finder."""

        # Set the endpoint as list even if it's a single endpoint
        if not isinstance(endpoint, list):
            endpoint = [endpoint]
        self.endpoint = endpoint

        # Set the request and append nvram hooks to the request
        self.request = request or []
        if nvram:
            nvram_request = converters.nvram_get(nvram)
            if nvram_request:
                self.request.extend(nvram_request)

        self.method = method


# A constant list of requests for fetching data
ASUSDATA_REQUEST = {
    "devices": [
        ("get_clientlist", ""),
    ],
}

ASUSDATA_NVRAM: dict[str, list[str]] = {}

# A map of endptoins to get data from
ASUSDATA_MAP: dict[AsusData, AsusData | AsusDataFinder] = {}


def add_conditional_data_rule(data: AsusData, rule: AsusDataFinder) -> None:
    """Add or change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = rule
    _LOGGER.debug("Added conditional data rule: %s -> %s", data, rule)


def add_conditional_data_alias(data: AsusData, origin: AsusData) -> None:
    """Add or change rule for ASUSDATA_MAP."""

    ASUSDATA_MAP[data] = origin
    _LOGGER.debug("Added data alias: %s -> %s", origin, data)


def remove_data_rule(data: AsusData) -> None:
    """Remove rule for ASUSDATA_MAP."""

    ASUSDATA_MAP.pop(data, None)
    _LOGGER.debug("Removed data rule: %s", data)
