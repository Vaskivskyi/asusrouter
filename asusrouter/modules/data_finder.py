"""Data finder module."""

from __future__ import annotations

from collections.abc import Callable

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.tools import converters


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


# A map of endpoints to get data from
ASUSDATA_MAP: dict[AsusData, AsusData | AsusDataFinder] = {}
