"""Log query helpers for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from asusrouter.modules.log.entry import ARLogEntry, ARLogProgramGroup
from asusrouter.modules.log.enums import ARLogField
from asusrouter.modules.log.parser import parse_program

if TYPE_CHECKING:
    from asusrouter.modules.log.query.event import ARLogEvent

_T = TypeVar("_T")


@dataclass
class _ProgramTally:
    """Running per-program totals collected in a single pass."""

    pids: dict[int, None] = field(default_factory=dict)
    pidless: bool = False
    count: int = 0


def summarize(
    entries: list[ARLogEntry],
    *,
    total: int,
    events: list[ARLogEvent] | None = None,
    programs: bool = False,
) -> dict[ARLogField, Any]:
    """Build the log data dict; `events` swaps the list key and format."""

    kept: list[ARLogEntry] | list[ARLogEvent] = (
        entries if events is None else events
    )
    data: dict[ARLogField, Any] = {
        ARLogField.ENTRY_COUNT: len(kept),
        ARLogField.LAST_ENTRY: kept[-1].timestamp if kept else None,
        ARLogField.TOTAL: total,
    }
    if events is not None:
        data[ARLogField.EVENT_LIST] = events
    else:
        data[ARLogField.ENTRY_LIST] = entries
    if programs:
        data[ARLogField.PROGRAM_LIST] = group_programs(entries)

    return data


def last_entries(items: list[_T], count: int | None = None) -> list[_T]:
    """Return all items, or only the last `count` when given."""

    if count is None or count >= len(items):
        return items
    if count <= 0:
        return []

    return items[-count:]


def group_programs(entries: list[ARLogEntry]) -> list[ARLogProgramGroup]:
    """Group programs by name into `ARLogProgramGroup`s (one per name)."""

    # `pids` is an ordered set: a dict keeps first-seen order at O(1)
    seen: dict[str, _ProgramTally] = {}
    for entry in entries:
        program = entry.program
        if program is None:
            continue
        tally = seen.get(program.name)
        if tally is None:
            tally = seen[program.name] = _ProgramTally()
        tally.count += 1
        if program.pid is None:
            tally.pidless = True
        else:
            tally.pids[program.pid] = None

    groups: list[ARLogProgramGroup] = []
    for name, tally in seen.items():
        kind, index = parse_program(name)
        groups.append(
            ARLogProgramGroup(
                name=name,
                program=kind,
                index=index,
                pids=tuple(tally.pids),
                pidless=tally.pidless,
                count=tally.count,
            )
        )

    return groups


def unique_entries(entries: list[ARLogEntry]) -> list[ARLogEntry]:
    """Return entries with a unique content, keeping first occurrence."""

    seen: set[str] = set()
    result: list[ARLogEntry] = []
    for entry in entries:
        content = entry.content.value
        if content in seen:
            continue
        seen.add(content)
        result.append(entry)

    return result
