"""Log query module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.log.query.dimension import QUERYABLE
from asusrouter.modules.log.query.engine import find, group
from asusrouter.modules.log.query.event import (
    ARLogEvent,
    build_event,
    build_events,
)
from asusrouter.modules.log.query.filter import filter_log
from asusrouter.modules.log.query.predicate import (
    ARLogAll,
    ARLogAny,
    ARLogBetween,
    ARLogContains,
    ARLogEverything,
    ARLogMatch,
    ARLogNot,
    ARLogPredicate,
)

__all__ = [
    "ARLogAll",
    "ARLogAny",
    "ARLogBetween",
    "ARLogContains",
    "ARLogEvent",
    "ARLogEverything",
    "ARLogMatch",
    "ARLogNot",
    "ARLogPredicate",
    "QUERYABLE",
    "build_event",
    "build_events",
    "filter_log",
    "find",
    "group",
]
