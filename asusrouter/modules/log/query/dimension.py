"""Query dimensions over processed log events."""

from __future__ import annotations

from collections.abc import Callable
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.translate import resolve_program
from asusrouter.modules.wifi import ARWiFiFrequency
from asusrouter.tools.identifiers import IpAddress, MacAddress, WiFiInterface

if TYPE_CHECKING:
    from asusrouter.modules.log.entry import ARLogEntry
    from asusrouter.modules.log.query.event import ARLogEvent

# Source field key -> queryable axis. A field absent here is not
# queryable. Several fields may feed one axis (`SERVICES` -> `SERVICE`)
_FACETABLE: dict[AREventKey, AREventKey] = {
    AREventKey.CALLER: AREventKey.CALLER,
    AREventKey.CLIENT_IP: AREventKey.CLIENT_IP,
    AREventKey.CLIENT_MAC: AREventKey.CLIENT_MAC,
    AREventKey.FREQUENCY: AREventKey.FREQUENCY,
    AREventKey.GATEWAY: AREventKey.GATEWAY,
    AREventKey.HOSTNAME: AREventKey.HOSTNAME,
    AREventKey.INTERFACE: AREventKey.INTERFACE,
    AREventKey.LOCAL_IP: AREventKey.LOCAL_IP,
    AREventKey.NODE_MAC: AREventKey.NODE_MAC,
    AREventKey.SERVICE: AREventKey.SERVICE,
    AREventKey.SERVICES: AREventKey.SERVICE,
    AREventKey.TARGET: AREventKey.TARGET,
    AREventKey.WL_ID: AREventKey.WL_ID,
}

# A facet value collection is expanded per item (but never a string)
_COLLECTIONS = (tuple, list, set, frozenset)

# A dimension already readable from an untranslated entry
_ENTRY: dict[AREventKey, Callable[[ARLogEntry], Any]] = {
    AREventKey.PROGRAM: resolve_program,
    AREventKey.PROGRAM_NAME: attrgetter("program_name"),
}

# A dimension whose value lives on the envelope, not in the facet set
_ENVELOPE: dict[AREventKey, Callable[[ARLogEvent], Any]] = {
    AREventKey.EVENT_TYPE: attrgetter("event_type"),
    AREventKey.PROGRAM: attrgetter("program"),
    AREventKey.PROGRAM_NAME: attrgetter("program_name"),
}

# Query-value coercion per dimension (missing -> value kept as-is)
_COERCE: dict[AREventKey, Callable[[Any], Any]] = {
    AREventKey.CLIENT_IP: IpAddress.from_value_safe,
    AREventKey.CLIENT_MAC: MacAddress.from_value_safe,
    AREventKey.FREQUENCY: ARWiFiFrequency.from_value,
    AREventKey.GATEWAY: IpAddress.from_value_safe,
    AREventKey.LOCAL_IP: IpAddress.from_value_safe,
    AREventKey.NODE_MAC: MacAddress.from_value_safe,
    AREventKey.PROGRAM: ARProgram.from_value,
    AREventKey.SERVICE: ARService.from_value,
    AREventKey.TARGET: WiFiInterface.from_value_safe,
    AREventKey.WL_ID: WiFiInterface.from_value_safe,
}


# Every axis a query may name, for a caller building its own filters
QUERYABLE: frozenset[AREventKey] = frozenset(_FACETABLE.values()) | frozenset(
    _ENVELOPE
)


def coerce(dimension: AREventKey, value: Any) -> Any:
    """Normalize a query value to the dimension's own type."""

    func = _COERCE.get(dimension)

    return func(value) if func is not None else value


def extract_facets(
    data: dict[AREventKey, Any],
) -> frozenset[tuple[AREventKey, Any]]:
    """Derive queryable `(axis, value)` facets from an event's data."""

    facets: set[tuple[AREventKey, Any]] = set()
    for field, value in data.items():
        axis = _FACETABLE.get(field)
        if axis is None:
            continue
        if isinstance(value, _COLLECTIONS):
            facets.update((axis, item) for item in value if item is not None)
        elif value is not None:
            facets.add((axis, value))

    return frozenset(facets)


def has(event: ARLogEvent, dimension: AREventKey, value: Any) -> bool:
    """Whether the event carries a value on a dimension."""

    getter = _ENVELOPE.get(dimension)
    if getter is not None:
        return bool(getter(event) == value)

    # Facets are stored as `(axis, value)`, so this is a single lookup
    return (dimension, value) in event.facets


def prescreen(entry: ARLogEntry, dimension: AREventKey, value: Any) -> bool:
    """Whether an untranslated entry can still carry a value."""

    getter = _ENTRY.get(dimension)

    return True if getter is None else bool(getter(entry) == value)


def resolve(event: ARLogEvent, dimension: AREventKey) -> frozenset[Any]:
    """Return the event's value(s) on a dimension (empty when absent)."""

    getter = _ENVELOPE.get(dimension)
    if getter is not None:
        return frozenset({getter(event)})

    return frozenset(
        value for axis, value in event.facets if axis is dimension
    )
