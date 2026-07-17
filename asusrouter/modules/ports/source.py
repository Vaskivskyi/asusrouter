"""Ports data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.ports.base import ARPortsData
from asusrouter.modules.ports.legacy import translate_ethernet_ports
from asusrouter.modules.ports.status import translate_port_status
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Request fetching the whole AiMesh network in one call
_PORT_STATUS_REQUEST = "node_mac=all"


class ARPortsSource(ARDataSource):
    """AsusRouter ports data source."""


# Universal instance - preferred
ARPortsSourceUniversal: ARPortsSource = ARPortsSource()


async def fetch_state(
    callback: ARCallbackType,
    source: ARPortsSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch raw port data, preferring the modern endpoint."""

    data = await callback(
        endpoint=AREndpoint.FETCH_PORT_STATUS,
        request=_PORT_STATUS_REQUEST,
    )
    if not isinstance(data, dict) or not data:
        data = await callback(endpoint=AREndpoint.FETCH_PORTS_ETHERNET)

    return data if isinstance(data, dict) else {}


def translate_state(
    data: dict[str, Any],
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[MacAddress, ARPortsData]:
    """Translate raw port data to the unified per-MAC format."""

    if not isinstance(data, dict) or not data:
        return {}

    if "port_info" in data:
        return translate_port_status(data, identity)
    if "portSpeed" in data:
        return translate_ethernet_ports(data, identity)

    return {}


ARCallReg.register_module(
    ARPortsSource, fetch_state=fetch_state, translate_state=translate_state
)


__all__ = [
    "ARPortsSource",
    "ARPortsSourceUniversal",
    "fetch_state",
    "translate_state",
]
