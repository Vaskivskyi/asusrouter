"""Unified log filtering interface for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asusrouter.modules.log.enums import ARLogField
from asusrouter.modules.log.query.entries import (
    last_entries,
    summarize,
    unique_entries,
)
from asusrouter.modules.log.query.event import build_event

if TYPE_CHECKING:
    from asusrouter.modules.log.entry import ARLogEntry
    from asusrouter.modules.log.query.event import ARLogEvent
    from asusrouter.modules.log.query.predicate import ARLogPredicate


def filter_log(
    entries: list[ARLogEntry],
    *,
    predicate: ARLogPredicate | None = None,
    last: int | None = None,
    unique: bool = False,
    programs: bool = False,
) -> dict[ARLogField, Any]:
    """Filter, limit and summarize parsed log entries into the data dict."""

    total = len(entries)
    if unique:
        entries = unique_entries(entries)

    if predicate is None:
        return summarize(
            last_entries(entries, last), programs=programs, total=total
        )

    # Bound once: the lookup would otherwise repeat per entry
    prescreen = getattr(predicate, "prescreen", None)

    # The entries themselves are only needed to group the programs
    matched: list[ARLogEntry] = []
    events: list[ARLogEvent] = []
    for entry in entries:
        if prescreen is not None and not prescreen(entry):
            continue
        event = build_event(entry)
        if not predicate.matches(event):
            continue
        events.append(event)
        if programs:
            matched.append(entry)

    return summarize(
        last_entries(matched, last),
        events=last_entries(events, last),
        programs=programs,
        total=total,
    )
