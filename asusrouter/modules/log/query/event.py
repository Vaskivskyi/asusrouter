"""Processed log event envelope for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from asusrouter.modules.log.clock import resolve_datetimes
from asusrouter.modules.log.enums import AREventKey, ARProgram
from asusrouter.modules.log.parser import parse_log
from asusrouter.modules.log.query.dimension import extract_facets
from asusrouter.modules.log.translate import resolve_program, translate_entry
from asusrouter.tools.security.text import SensitiveText

if TYPE_CHECKING:
    from datetime import datetime

    from asusrouter.modules.log.entry import ARLogEntry


@dataclass(frozen=True, slots=True)
class ARLogEvent:
    """A translated log entry with its metadata and queryable facets."""

    timestamp: datetime | None
    program: ARProgram
    # raw syslog tag
    program_name: str | None
    event_type: StrEnum
    # plain only when the translator read the message in full, otherwise
    # classified by what it holds, down to UNSAFE for an unread one
    raw: SensitiveText | str
    # excluded from the hash so the envelope stays hashable
    data: dict[AREventKey, Any] = field(default_factory=dict, hash=False)
    # `facets` derived from `data` on first query, never set by the caller
    _facets: frozenset[tuple[AREventKey, Any]] | None = field(
        default=None, compare=False, repr=False
    )

    @property
    def raw_text(self) -> str:
        """The message as text, whatever level `raw` is exposed at."""

        raw = self.raw

        return raw.value if isinstance(raw, SensitiveText) else raw

    @property
    def facets(self) -> frozenset[tuple[AREventKey, Any]]:
        """The queryable `(axis, value)` facets, derived once on demand."""

        facets = self._facets
        if facets is None:
            facets = extract_facets(self.data)
            object.__setattr__(self, "_facets", facets)

        return facets


def build_event(entry: ARLogEntry) -> ARLogEvent:
    """Translate one entry into an envelope with metadata and facets."""

    program = resolve_program(entry)
    # The translator hands over a fresh dict, so the metadata is moved out
    # of it instead of copying the rest into a second one
    data = translate_entry(entry, program)
    event_type = data.pop(AREventKey.EVENT_TYPE)
    raw = data.pop(AREventKey.RAW)

    return ARLogEvent(
        timestamp=entry.timestamp,
        program=program,
        program_name=entry.program_name,
        event_type=event_type,
        raw=raw,
        data=data,
    )


def build_events(
    content: str | None, *, anchor: datetime | None = None
) -> list[ARLogEvent]:
    """Parse, timestamp-resolve and translate a raw log into envelopes."""

    entries = resolve_datetimes(parse_log(content), anchor)

    return [build_event(entry) for entry in entries]
