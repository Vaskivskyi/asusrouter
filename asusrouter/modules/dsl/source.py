"""DSL data source for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.metrics import ARMetricType
from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import support_available
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.units import DataRateUnitConverter, UnitOfDataRate

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# The nvram key for each data rate direction and its target metric
_RATE_KEYS: tuple[tuple[ARNvramType, ARMetricType], ...] = (
    (ARNvramType.DSL_DATARATE_DOWN, ARMetricType.DOWNLOAD_SPEED),
    (ARNvramType.DSL_DATARATE_UP, ARMetricType.UPLOAD_SPEED),
)

# Full NVRAM request for the DSL rates, built once
_DSL_REQUEST: tuple[ARNvramType, ...] = tuple(key for key, _ in _RATE_KEYS)


def _read_rate(value: Any) -> float | None:
    """Read a DSL data rate (`<n> Kbps`) as a rate in bits per second."""

    if value is None:
        return None
    # The value carries a unit suffix (e.g. `12345 Kbps`); keep the number
    number = raw_to_int(str(value).split(" ")[0])
    if number is None:
        return None
    return DataRateUnitConverter.convert_to_base(
        number, UnitOfDataRate.KILOBIT_PER_SECOND
    )


class ARDSLSource(ARDataSource):
    """DSL data source for the connected router."""


# Universal instance - preferred
ARDSLSourceUniversal: ARDSLSource = ARDSLSource()


async def fetch_state(
    callback: ARCallbackType,
    source: ARDSLSource,
    *,
    fetch_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the DSL data rates through the NVRAM module."""

    if identity is None or not support_available(
        identity.support, ARSupportType.DSL
    ):
        return {}

    return await async_fetch_values(fetch_data_callback, _DSL_REQUEST)


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARMetricType, Any]:
    """Translate raw DSL data into the flat data rate metrics."""

    if not isinstance(data, dict):
        return {}

    result: dict[ARMetricType, Any] = {}
    for key, metric in _RATE_KEYS:
        rate = _read_rate(data.get(key))
        if rate is not None:
            result[metric] = rate

    return result


ARCallReg.register_source(
    ARDSLSource, fetch_state=fetch_state, translate_state=translate_state
)


__all__ = [
    "ARDSLSource",
    "ARDSLSourceUniversal",
    "fetch_state",
    "translate_state",
]
