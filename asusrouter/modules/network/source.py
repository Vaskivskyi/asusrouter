"""Network data source for AsusRouter.

The wireless networks (main + guest/IoT). On modern firmware they live in
SDN; on legacy firmware they come from per-band nvram. `fetch_state` picks the
backend by the `MaxRule_SDN` support flag; `translate_state` picks the parser
by the shape of the fetched data. Both yield the same output: networks grouped
by type -> list of network profiles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.network import legacy, sdn
from asusrouter.modules.network.enums import ARNetworkField, ARNetworkType
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.source import ARDataSource
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


class ARNetworkSource(ARDataSource):
    """AsusRouter network data source (router-global)."""


# Universal instance - preferred
ARNetworkSourceUniversal: ARNetworkSource = ARNetworkSource()


def _sdn_supported(identity: ARDeviceIdentity | None) -> bool:
    """Whether the device supports SDN (has a positive `MaxRule_SDN`)."""

    if identity is None:
        return False
    rules = raw_to_int(identity.support.get(ARSupportType.SDN_MAX_RULES))
    return rules is not None and rules > 0


async def fetch_state(
    callback: ARCallbackType,
    source: ARNetworkSource,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> Any:
    """Fetch the networks from SDN or, on legacy firmware, per-band nvram."""

    if _sdn_supported(identity):
        return await sdn.fetch(callback)

    wifi = identity.wifi if identity is not None else {}
    return await legacy.fetch(callback, wifi)


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> dict[ARNetworkType, list[dict[ARNetworkField, Any]]]:
    """Translate the fetched data into networks grouped by type."""

    if not isinstance(data, dict):
        return {}

    if ARNvramType.SDN_RL.value in data:
        bands = list(identity.wifi) if identity is not None else []
        return sdn.translate(data, bands)

    wifi = identity.wifi if identity is not None else {}
    return legacy.translate(data, wifi)


ARCallReg.register_source(
    ARNetworkSource, fetch_state=fetch_state, translate_state=translate_state
)


__all__ = [
    "ARNetworkSource",
    "ARNetworkSourceUniversal",
    "fetch_state",
    "translate_state",
]
