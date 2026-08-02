"""Log module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.log.entry import (
    ARLogEntry,
    ARLogProgram,
    ARLogProgramGroup,
)
from asusrouter.modules.log.enums import AREventKey, ARLogField, ARProgram
from asusrouter.modules.log.parser import parse_program
from asusrouter.modules.log.query import (
    QUERYABLE,
    ARLogAll,
    ARLogAny,
    ARLogBetween,
    ARLogContains,
    ARLogEvent,
    ARLogEverything,
    ARLogMatch,
    ARLogNot,
    ARLogPredicate,
    build_event,
    build_events,
    filter_log,
    find,
    group,
)
from asusrouter.modules.log.source import ARLogSource, ARLogSourceUniversal

__all__ = [
    "AREventKey",
    "ARLogAll",
    "ARLogAny",
    "ARLogBetween",
    "ARLogContains",
    "ARLogEntry",
    "ARLogEvent",
    "ARLogEverything",
    "ARLogField",
    "ARLogMatch",
    "ARLogNot",
    "ARLogPredicate",
    "ARLogProgram",
    "ARLogProgramGroup",
    "ARLogSource",
    "ARLogSourceUniversal",
    "ARProgram",
    "QUERYABLE",
    "build_event",
    "build_events",
    "filter_log",
    "find",
    "group",
    "parse_program",
]
