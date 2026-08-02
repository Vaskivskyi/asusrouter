"""Live device probe for the AsusRouter log module."""

from __future__ import annotations

import asyncio
from collections import Counter
from time import perf_counter
from typing import TYPE_CHECKING, Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.enums import AREventKey, ARLogField, ARProgram
from asusrouter.modules.log.query import (
    ARLogEverything,
    ARLogMatch,
    filter_log,
)
from asusrouter.modules.log.source import (
    ARLogSource,
    fetch_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.probe import ARProbeSection, build_section, render_value
from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.text import SensitiveText

if TYPE_CHECKING:
    from collections.abc import Callable

    from asusrouter.modules.log.entry import ARLogEntry
    from asusrouter.modules.log.query import ARLogEvent
    from asusrouter.tools.types import ARCallableType

# How many rows the ranked sections keep
_TOP_PROGRAMS = 15
_TOP_EVENTS = 25
_TOP_UNKNOWN = 12

# Characters of a message kept as the example of an untranslated event
_SAMPLE_LENGTH = 80

# Seconds between the two polls of the incremental section
_POLL_DELAY = 15.0


def _milliseconds(started: float) -> str:
    """Format the time elapsed since `started`."""

    return f"{(perf_counter() - started) * 1000:.1f} ms"


def _buffer_rows(state: dict[ARLogField, Any]) -> list[tuple[str, Any]]:
    """Report what one read of the log returned."""

    entries: list[ARLogEntry] = state.get(ARLogField.ENTRY_LIST) or []
    anchor = state.get(ARLogField.ANCHOR)
    # Only its length is reported, never the text it holds
    stored = anchor.value if isinstance(anchor, SensitiveText) else ""

    return [
        ("entries", len(entries)),
        ("total before filtering", state.get(ARLogField.TOTAL)),
        ("oldest", entries[0].timestamp if entries else None),
        ("newest", state.get(ARLogField.LAST_ENTRY)),
        ("anchor stored", f"{len(stored)} chars" if stored else "no"),
    ]


def _program_rows(entries: list[ARLogEntry]) -> list[tuple[str, Any]]:
    """Report the programs writing to this device's log."""

    groups = filter_log(entries, programs=True)[ARLogField.PROGRAM_LIST]

    rows: list[tuple[str, Any]] = []
    for group in sorted(groups, key=lambda item: -item.count)[:_TOP_PROGRAMS]:
        known = (
            group.program.value
            if group.program is not ARProgram.UNKNOWN
            else "no typed program"
        )
        rows.append((group.name, f"{group.count} -> {known}"))

    return rows


def _event_rows(events: list[ARLogEvent]) -> list[tuple[str, Any]]:
    """Report which event types the translators produced."""

    counter: Counter[tuple[str, str]] = Counter(
        (
            event.program_name or str(event.program),
            str(event.event_type),
        )
        for event in events
    )

    return [
        (f"{program} {event_type}", count)
        for (program, event_type), count in counter.most_common(_TOP_EVENTS)
    ]


def _sample(text: str, level: ARSecurityLevel) -> str:
    """Cut an example message down, after it has been made shareable."""

    return render_value(text, level)[:_SAMPLE_LENGTH]


def _untranslated_rows(
    events: list[ARLogEvent], level: ARSecurityLevel
) -> list[tuple[str, Any]]:
    """Report what the translators did not recognize."""

    unknown: dict[str, list[ARLogEvent]] = {}
    for event in events:
        if event.event_type.value == UNKNOWN_MEMBER_STR:
            name = event.program_name or "no program tag"
            unknown.setdefault(name, []).append(event)

    missed = sum(len(items) for items in unknown.values())
    total = len(events)
    share = (total - missed) / total * 100 if total else 100.0

    rows: list[tuple[str, Any]] = [
        ("translated", f"{total - missed}/{total} ({share:.1f}%)")
    ]
    ranked = sorted(unknown.items(), key=lambda item: -len(item[1]))
    rows.extend(
        # `raw_text` on purpose: an unread message is UNSAFE by class,
        # so rendering it would redact every example away. `_sample`
        # scrubs it by shape instead
        (name, f"{len(items)} e.g. {_sample(items[0].raw_text, level)}")
        for name, items in ranked[:_TOP_UNKNOWN]
    )

    return rows


def _timing_rows(entries: list[ARLogEntry]) -> list[tuple[str, Any]]:
    """Measure what the query interface costs on this device's buffer."""

    measured: tuple[tuple[str, Callable[[], Any]], ...] = (
        ("read, no filtering", lambda: filter_log(entries)),
        ("group the programs", lambda: filter_log(entries, programs=True)),
        (
            "one program",
            lambda: filter_log(
                entries,
                predicate=ARLogMatch(AREventKey.PROGRAM, ARProgram.KERNEL),
            ),
        ),
        (
            "translate everything",
            lambda: filter_log(entries, predicate=ARLogEverything()),
        ),
    )

    rows: list[tuple[str, Any]] = []
    for label, call in measured:
        started = perf_counter()
        call()
        rows.append((label, _milliseconds(started)))

    return rows


async def _incremental_rows(
    callback: ARCallableType,
    source: ARLogSource,
    *,
    fetch_raw_callback: ARCallableType | None,
    delay: float,
) -> list[tuple[str, Any]]:
    """Read the log twice and compare a full parse with a continued one."""

    if fetch_raw_callback is None:
        return [("skipped", "no raw fetch available")]

    first_raw = await fetch_state(
        callback, source, fetch_raw_callback=fetch_raw_callback
    )
    if not first_raw:
        return [("skipped", "the device returned an empty log")]
    first = translate_state(first_raw)

    await asyncio.sleep(delay)

    second_raw = await fetch_state(
        callback, source, fetch_raw_callback=fetch_raw_callback
    )
    if not second_raw:
        return [("skipped", "the second read returned an empty log")]

    started = perf_counter()
    full = translate_state(second_raw)
    full_ms = _milliseconds(started)

    started = perf_counter()
    continued = translate_state(second_raw, previous=first)
    continued_ms = _milliseconds(started)

    held = len(first[ARLogField.ENTRY_LIST])
    on_device = len(full[ARLogField.ENTRY_LIST])
    parsed = len(continued[ARLogField.ENTRY_LIST]) - held

    # An unchanged buffer proves only that the anchor was found, never
    # that the records after it are read
    if parsed >= on_device:
        anchor = "not found, read in full"
    elif parsed:
        anchor = "matched, continued"
    else:
        anchor = "matched, but nothing new was written"

    return [
        ("delay between reads", f"{delay:.1f} s"),
        ("first read", held),
        ("second read, on device", on_device),
        ("second read, parsed", parsed),
        ("kept across the reads", len(continued[ARLogField.ENTRY_LIST])),
        ("parse, full", full_ms),
        ("parse, continued", continued_ms),
        ("anchor", anchor),
    ]


async def async_probe_state(
    callback: ARCallableType,
    source: ARLogSource,
    *,
    fetch_data_callback: ARCallableType | None = None,
    level: ARSecurityLevel = ARSecurityLevel.SANITIZED,
    **kwargs: Any,
) -> list[ARProbeSection]:
    """Probe the log against a live device."""

    if fetch_data_callback is None:
        return []

    data = await fetch_data_callback(source) or {}
    state: dict[ARLogField, Any] = data.get(source) or {}
    entries: list[ARLogEntry] = state.get(ARLogField.ENTRY_LIST) or []
    events: list[ARLogEvent] = filter_log(
        entries, predicate=ARLogEverything()
    )[ARLogField.EVENT_LIST]

    incremental = await _incremental_rows(
        callback,
        source,
        fetch_raw_callback=kwargs.get("fetch_raw_callback"),
        delay=kwargs.get("probe_delay", _POLL_DELAY),
    )

    return [
        build_section(title, rows, level=level)
        for title, rows in (
            ("buffer", _buffer_rows(state)),
            ("programs", _program_rows(entries)),
            ("event types", _event_rows(events)),
            ("untranslated", _untranslated_rows(events, level)),
            ("incremental read", incremental),
            ("timing", _timing_rows(entries)),
        )
    ]


ARCallReg.register_source(ARLogSource, probe_state=async_probe_state)


__all__ = [
    "async_probe_state",
]
