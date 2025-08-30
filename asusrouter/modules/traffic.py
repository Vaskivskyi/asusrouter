"""Traffic module."""

from __future__ import annotations

from enum import StrEnum
import logging
from typing import Any, Final

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    HTTPStatus,
)
from asusrouter.modules.endpoint import (
    EndpointTools,
    EndpointType,
    get_request_type,
)
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters import flatten_dict, safe_bool_nn
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.readers import read_units_data_rate
from asusrouter.tools.types import ARCallableType, ARCallbackType
from asusrouter.tools.units import UnitOfDataRate
from asusrouter.tools.writers import dict_to_request

_LOGGER = logging.getLogger(__name__)

# Initialize data rate readers once
_read_kibps = read_units_data_rate(UnitOfDataRate.KIBIBIT_PER_SECOND)
_read_Mibps = read_units_data_rate(UnitOfDataRate.MEBIBIT_PER_SECOND)  # noqa: N816

_TRANSLATION_TABLE: dict[str, tuple[str, ARCallableType]] = {
    # Data rate / speed (current)
    "data_rx": ("rx_speed", _read_kibps),
    "data_tx": ("tx_speed", _read_kibps),
    # Data rate / speed (average)
    "data_avg_rx": ("rx_speed_avg", _read_kibps),
    "data_avg_tx": ("tx_speed_avg", _read_kibps),
    # Physical layer rate / speed
    "phy_rx": ("phy_rx", _read_Mibps),
    "phy_tx": ("phy_tx", _read_Mibps),
    # Status code
    "error_status": ("status", HTTPStatus.from_value),
}


class ARTrafficType(FromStrMixin, StrEnum):
    """Traffic type."""

    UNKNOWN = "unknown"

    BACKHAUL = "backhaul"
    ETHERNET = "ethernet"
    WIFI = "wifi"


AR_TRAFFIC_SOURCE: Final[dict[ARTrafficType, EndpointType]] = {
    ARTrafficType.BACKHAUL: EndpointTools.TRAFFIC_BACKHAUL,
    ARTrafficType.ETHERNET: EndpointTools.TRAFFIC_ETHERNET,
    ARTrafficType.WIFI: EndpointTools.TRAFFIC_WIFI,
}


class ARTrafficSource(ARDataSource):
    """Traffic data source."""

    def __init__(self, target: Any, type: Any = None) -> None:
        """Initialize the traffic source."""

        super().__init__()

        self._target: MacAddress | None = None
        self._type: ARTrafficType = ARTrafficType.UNKNOWN

        # Try to set the target and type from input
        self.target = target
        self.type = type

    def __repr__(self) -> str:
        """Representation of the traffic source."""

        return f"<ARTrafficSource type=`{self.type}`>"

    @property
    def target(self) -> MacAddress | None:
        """Get the target."""

        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        """Set the target."""

        try:
            self._target = MacAddress(value)
        except ValueError:
            self._target = None

    @property
    def type(self) -> ARTrafficType:
        """Get the traffic type."""

        return self._type

    @type.setter
    def type(self, type: ARTrafficType) -> None:
        """Set the traffic type."""

        self._type = ARTrafficType.from_value(type)


class ARTrafficSourceEthernet(ARTrafficSource):
    """Ethernet traffic source.

    This source provides data for:

    - LAN if `bh_flag` is `False`
    - Wired backhaul to the parent (if `bh_flag` is `True`)
    """

    def __init__(
        self, target: Any, type: Any = None, bh_flag: Any = None
    ) -> None:
        """Initialize the Ethernet traffic source."""

        super().__init__(target, type)
        self.type = ARTrafficType.ETHERNET

        self._bh_flag: bool
        self.bh_flag = bh_flag

    @property
    def bh_flag(self) -> bool:
        """Get the backhaul flag."""

        return self._bh_flag

    @bh_flag.setter
    def bh_flag(self, value: Any) -> None:
        """Set the backhaul flag."""

        self._bh_flag = safe_bool_nn(value)


class ARTrafficSourceBetween(ARTrafficSource):
    """Traffic source between two points."""

    def __init__(
        self, target: Any, type: Any = None, towards: Any = None
    ) -> None:
        """Initialize the traffic source between two points."""

        super().__init__(target, type)

        self._towards: MacAddress | None
        self.towards = towards

    @property
    def towards(self) -> MacAddress | None:
        """Get the target MAC address."""

        return self._towards

    @towards.setter
    def towards(self, value: Any) -> None:
        """Set the target MAC address."""

        try:
            self._towards = MacAddress(value)
        except ValueError:
            self._towards = None


class ARTrafficSourceWiFi(ARTrafficSourceBetween):
    """WiFi traffic source.

    Traffic of the router / node (`target`) on the specific
    wireless band (`towards`) defined by its MAC address.
    """

    def __init__(self, target: Any, towards: Any) -> None:
        """Initialize the WiFi traffic source."""

        super().__init__(target, type=ARTrafficType.WIFI, towards=towards)
        self.type = ARTrafficType.WIFI


class ARTrafficSourceBackhaul(ARTrafficSourceBetween):
    """Backhaul traffic source.

    Traffic from the router / node (`target`) to the specific
    node (`towards`) defined by its MAC address.
    """

    def __init__(self, target: Any, towards: Any) -> None:
        """Initialize the backhaul traffic source."""

        super().__init__(target, type=ARTrafficType.BACKHAUL, towards=towards)
        self.type = ARTrafficType.BACKHAUL


def _check_state(source: Any) -> None:
    """Check the state of the traffic source.

    This helper allows checking that all the required arguments
    are present and valid.
    """

    # Is a traffic source
    if not isinstance(source, ARTrafficSource):
        raise TypeError(f"Expected `ARTrafficSource`, got `{type(source)}`")

    # Has target and type set
    if source.target is None:
        raise ValueError("Traffic source must have a `target` property set")
    if source.type == ARTrafficType.UNKNOWN:
        raise ValueError("Traffic source must have a `type` property set")

    # Has a `toward` property if required
    if isinstance(source, ARTrafficSourceBetween) and source.towards is None:
        raise ValueError(
            f"Traffic source of type `{source.type}` requires "
            "a `towards` property set"
        )


async def get_state(
    callback: ARCallbackType,
    source: ARTrafficSource,
    **kwargs: Any,
) -> Any:
    """Get the state of the traffic source."""

    # Check the input source
    _check_state(source)

    # Get the correct traffic endpoint
    endpoint: EndpointType | None = AR_TRAFFIC_SOURCE.get(source.type, None)
    if endpoint is None:
        raise ValueError(
            f"Cannot find endpoint for traffic type `{source.type}`"
        )

    _LOGGER.debug("Getting state for traffic source: %s", source)

    arguments: dict[str, Any] = {
        "node_mac": source.target,
    }

    # Add backhaul flag if required
    if isinstance(source, ARTrafficSourceEthernet):
        arguments["is_bh"] = source.bh_flag

    # Add towards channel if required
    if isinstance(source, ARTrafficSourceBackhaul):
        arguments["sta_mac"] = source.towards
    if isinstance(source, ARTrafficSourceWiFi):
        arguments["band_mac"] = source.towards

    # Call the callback to get the state
    request = dict_to_request(
        arguments, request_type=get_request_type(endpoint)
    )
    return await callback(endpoint=endpoint, request=request)


def translate_state(
    data: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Translate the traffic data to a simple format."""

    result: dict[str, Any] = {}

    simplified_data = flatten_dict(data)
    if not simplified_data:
        return {}

    for key, value in simplified_data.items():
        if key in _TRANSLATION_TABLE:
            new_key, transform = _TRANSLATION_TABLE[key]
            result[new_key] = transform(value)
            continue
        result[key] = value

    return result


# Register callables for traffic sources
calls: dict[str, ARCallableType] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}
ARCallReg.register(ARTrafficSourceEthernet, **calls)
ARCallReg.register(ARTrafficSourceWiFi, **calls)
ARCallReg.register(ARTrafficSourceBackhaul, **calls)
