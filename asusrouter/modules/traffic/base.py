"""Traffic Base module for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.source import ARDataSource
from asusrouter.modules.traffic.enums import ARTrafficType
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.identifiers import MacAddress

# A traffic link: a fixed type or a specific wifi band (wireless)
ARTrafficLink = ARTrafficType | ARWiFiBand


def _coerce_link(value: Any) -> ARTrafficLink | None:
    """Coerce a value to a traffic link (band preferred), or None."""

    if value is None:
        return None
    if isinstance(value, (ARTrafficType, ARWiFiBand)):
        return value
    band = ARWiFiBand.from_value(value)
    if band is not ARWiFiBand.UNKNOWN:
        return band
    traffic_type = ARTrafficType.from_value(value)
    return traffic_type if traffic_type is not ARTrafficType.UNKNOWN else None


class ARTrafficSource(ARDataSource):
    """Traffic data source for one device (`target`) and `link`.

    `target` None means the connected router; `link` None means all of
    the device's available links.
    """

    def __init__(self, link: Any = None, target: Any = None) -> None:
        """Initialize the traffic source."""

        super().__init__()

        self._target: MacAddress | None = None
        self._link: ARTrafficLink | None = None
        self.target = target
        self.link = link

    @property
    def target(self) -> MacAddress | None:
        """Get the target device MAC address."""

        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        """Set the target device MAC address."""

        self._target = MacAddress.from_value_safe(value)

    @property
    def link(self) -> ARTrafficLink | None:
        """Get the traffic link (type or band), or None for all."""

        return self._link

    @link.setter
    def link(self, value: Any) -> None:
        """Set the traffic link."""

        self._link = _coerce_link(value)

    def __eq__(self, other: object) -> bool:
        """Equal by exact type, target and link."""

        if not isinstance(other, ARTrafficSource):
            return NotImplemented
        return (
            type(self) is type(other)
            and self._target == other._target
            and self._link == other._link
        )

    def __hash__(self) -> int:
        """Hash by type, target and link."""

        return hash((type(self), self._target, self._link))

    def __repr__(self) -> str:
        """Representation of the traffic source."""

        return (
            f"<{type(self).__name__} target=`{self._target}` "
            f"link=`{self._link}`>"
        )
