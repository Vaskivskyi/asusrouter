"""Find and group processed log events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.log.query.dimension import resolve

if TYPE_CHECKING:
    from collections.abc import Iterable

    from asusrouter.modules.log.enums import AREventKey
    from asusrouter.modules.log.query.event import ARLogEvent
    from asusrouter.modules.log.query.predicate import ARLogPredicate


def find(
    events: Iterable[ARLogEvent], predicate: ARLogPredicate
) -> list[ARLogEvent]:
    """Return the events matching a predicate, order preserved."""

    return [event for event in events if predicate.matches(event)]


def group(
    events: Iterable[ARLogEvent], by: AREventKey
) -> dict[Any, list[ARLogEvent]]:
    """Partition events by a dimension's value (multi-valued events repeat)."""

    result: dict[Any, list[ARLogEvent]] = {}
    for event in events:
        for value in resolve(event, by):
            result.setdefault(value, []).append(event)

    return result
