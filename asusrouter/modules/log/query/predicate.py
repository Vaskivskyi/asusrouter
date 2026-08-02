"""Predicates for querying processed log events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from asusrouter.modules.log.query.dimension import coerce, has, prescreen

if TYPE_CHECKING:
    from datetime import datetime

    from asusrouter.modules.log.entry import ARLogEntry
    from asusrouter.modules.log.enums import AREventKey
    from asusrouter.modules.log.query.event import ARLogEvent


@runtime_checkable
class ARLogPredicate(Protocol):
    """A test applied to a single event."""

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the event satisfies the predicate."""

        ...

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether the untranslated entry can still match."""

        ...


def may_match(predicate: ARLogPredicate, entry: ARLogEntry) -> bool:
    """Whether a predicate keeps an entry in play before translation."""

    check = getattr(predicate, "prescreen", None)

    return True if check is None else check(entry)


@dataclass(frozen=True)
class ARLogMatch:
    """Match a dimension against a value (equality on the query axis)."""

    dimension: AREventKey
    value: object

    def __post_init__(self) -> None:
        """Coerce the query value to the dimension's own type."""

        object.__setattr__(self, "value", coerce(self.dimension, self.value))

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the event carries the value on this dimension."""

        return has(event, self.dimension, self.value)

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether the entry can carry the value before translation."""

        return prescreen(entry, self.dimension, self.value)


def _same_frame(
    bound: datetime | None, timestamp: datetime
) -> datetime | None:
    """Read a window bound in the same frame as the timestamp it meets."""

    if bound is None or (bound.tzinfo is None) == (timestamp.tzinfo is None):
        return bound

    return bound.replace(tzinfo=timestamp.tzinfo)


@dataclass(frozen=True)
class ARLogBetween:
    """Match events whose timestamp falls in an inclusive window."""

    after: datetime | None = None
    before: datetime | None = None

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the event's timestamp lies within the window."""

        return self._holds(event.timestamp)

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether the entry's timestamp lies within the window."""

        return self._holds(entry.timestamp)

    def _holds(self, timestamp: datetime | None) -> bool:
        """Whether a timestamp lies within the window."""

        if timestamp is None:
            return False

        after = _same_frame(self.after, timestamp)
        before = _same_frame(self.before, timestamp)
        if after is not None and timestamp < after:
            return False

        return before is None or timestamp <= before


@dataclass(frozen=True)
class ARLogContains:
    """Match events whose raw content holds a substring (case-folded)."""

    text: str

    def __post_init__(self) -> None:
        """Case-fold the query text once."""

        object.__setattr__(self, "text", self.text.casefold())

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the raw content contains the text."""

        return self.text in event.raw_text.casefold()

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether the entry contains the text."""

        return self.text in entry.content.value.casefold()


@dataclass(frozen=True)
class ARLogEverything:
    """Keep every event, translating the log without filtering it."""

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the event matches, which it always does."""

        return True

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether the entry stays in play, which it always does."""

        return True


class ARLogAll:
    """Match events satisfying every sub-predicate (AND)."""

    def __init__(self, *predicates: ARLogPredicate) -> None:
        """Store the sub-predicates to AND together."""

        self.predicates = predicates

    def matches(self, event: ARLogEvent) -> bool:
        """Whether every sub-predicate matches."""

        return all(predicate.matches(event) for predicate in self.predicates)

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether every sub-predicate keeps the entry in play."""

        return all(
            may_match(predicate, entry) for predicate in self.predicates
        )


class ARLogAny:
    """Match events satisfying any sub-predicate (OR)."""

    def __init__(self, *predicates: ARLogPredicate) -> None:
        """Store the sub-predicates to OR together."""

        self.predicates = predicates

    def matches(self, event: ARLogEvent) -> bool:
        """Whether at least one sub-predicate matches."""

        return any(predicate.matches(event) for predicate in self.predicates)

    def prescreen(self, entry: ARLogEntry) -> bool:
        """Whether any sub-predicate keeps the entry in play."""

        return any(
            may_match(predicate, entry) for predicate in self.predicates
        )


class ARLogNot:
    """Match events failing the wrapped predicate (negation)."""

    def __init__(self, predicate: ARLogPredicate) -> None:
        """Store the predicate to negate."""

        self.predicate = predicate

    def matches(self, event: ARLogEvent) -> bool:
        """Whether the wrapped predicate does not match."""

        return not self.predicate.matches(event)
