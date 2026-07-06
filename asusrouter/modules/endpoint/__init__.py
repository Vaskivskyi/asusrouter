"""Endpoint module for AsusRouter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
import importlib
import logging
from types import ModuleType
from typing import TYPE_CHECKING, Any

from asusrouter.const import HTTPStatus
from asusrouter.error import AsusRouter404Error, AsusRouterRequestFormatError
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.tools.readers import read_json_content

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

_LOGGER = logging.getLogger(__name__)


_SUBMODULE_MAP: dict[str, str] = {
    AREndpoint.FETCH_DATA: "hook",
    AREndpoint.FETCH_VPN_STATUS: "vpn",
}


def _get_module(
    endpoint: AREndpoint,
) -> ModuleType | None:
    """Attempt to get the module for the endpoint."""

    try:
        submodule = _SUBMODULE_MAP.get(endpoint) or endpoint.name.lower()
        module_name = f"asusrouter.modules.endpoint.{submodule}"

        # Import in a separate thread to avoid blocking the main thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(importlib.import_module, module_name)
            return future.result()

    except ModuleNotFoundError:
        _LOGGER.debug("No module found for endpoint %s", endpoint)
        return None


def read(
    endpoint: AREndpoint,
    content: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Read the data from an endpoint."""

    _LOGGER.debug("Reading data from endpoint %s", endpoint)

    submodule = _get_module(endpoint)

    if submodule and hasattr(submodule, "read"):
        result = submodule.read(content, **kwargs)
        if isinstance(result, dict):
            return result
        return {}

    result = read_json_content(content)
    return result if isinstance(result, dict) else {}


def process(
    endpoint: AREndpoint,
    data: dict[str, Any],
    history: dict[AsusData, AsusDataState] | None = None,
    description: ARDeviceIdentity | None = None,
) -> dict[AsusData, Any]:
    """Process the data from an endpoint."""

    _LOGGER.debug("Processing data from endpoint %s", endpoint)

    submodule = _get_module(endpoint)

    if submodule:
        require_history = getattr(submodule, "REQUIRE_HISTORY", False)
        if require_history:
            data_set(data, history=history)
        require_firmware = getattr(submodule, "REQUIRE_FIRMWARE", False)
        if require_firmware:
            data_set(
                data,
                firmware=description.firmware if description else None,
            )
        try:
            result = submodule.process(data)
            if isinstance(result, dict):
                return result
            return {}
        except (AttributeError, ValueError) as ex:
            _LOGGER.error(
                "Error processing data from endpoint %s: %s",
                endpoint,
                ex,
            )
            return {}

    return {}


def data_set(data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Append the data to the data dict."""

    data.update(kwargs)
    return data


def data_get(data: dict[str, Any], key: str) -> Any | None:
    """Extract value from the data dict and update the data dict."""

    value = data.get(key)
    data.pop(key, None)
    return value


async def check_available(
    endpoint: AREndpoint,
    api_query: Callable[..., Awaitable[Any]],
) -> tuple[bool, Any | None]:
    """Check whether the endpoint is available or returns 404."""

    try:
        status, _, content = await api_query(endpoint)
        if status == HTTPStatus.OK:
            return (True, content)
    except AsusRouterRequestFormatError:
        return (True, None)
    except AsusRouter404Error:
        return (False, None)

    return (False, None)
