"""Declarative message patterns for log event translation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final, cast

from asusrouter.modules.log.enums import AREventKey
from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.sensitive import ARSensitive
from asusrouter.tools.security.text import SensitiveText

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from enum import StrEnum

# The group picking the event type when a pattern covers several of them
EVENT_GROUP: Final[str] = AREventKey.EVENT_TYPE.value

ERROR_DERIVE_SOURCE: Final[str] = "derives from a key the pattern never reads"
ERROR_GROUP_KEY: Final[str] = "names a group without an event key"
ERROR_UNUSED_CONVERTER: Final[str] = "converts a key the pattern never reads"

# One planned field: the key it fills, its group number and its converter
_Field = tuple[AREventKey, int, "Callable[[str], Any] | None"]
# One derived field: the key it fills, the key it reads and its function
_Derived = tuple[AREventKey, AREventKey, "Callable[[Any], Any]"]


def _converter_level(
    converter: Callable[..., Any] | None,
) -> ARSecurityLevel | None:
    """Read the level of the sensitive type a converter builds, if any."""

    owner = getattr(converter, "__self__", None)
    if isinstance(owner, type) and issubclass(owner, ARSensitive):
        return owner.reveal_level

    return None


class ARLogPattern:
    """One recognized message shape and the event it yields."""

    __slots__ = (
        "_derived",
        "_event",
        "_events",
        "_fields",
        "_marker",
        "_raw_level",
        "_regex",
    )

    _derived: tuple[_Derived, ...]
    _event: StrEnum | None
    _events: Mapping[str, StrEnum] | None
    _fields: tuple[_Field, ...]
    _marker: str | None
    _raw_level: ARSecurityLevel | None
    _regex: re.Pattern[str]

    def __init__(
        self,
        event: StrEnum | Mapping[str, StrEnum],
        pattern: str,
        *,
        convert: Mapping[AREventKey, Callable[[str], Any]] | None = None,
        derive: Mapping[AREventKey, tuple[AREventKey, Callable[[Any], Any]]]
        | None = None,
        marker: str | None = None,
    ) -> None:
        """Compile the pattern and plan the fields it fills."""

        self._regex = re.compile(pattern)
        self._marker = marker

        # A mapping picks the event type from the `event_type` group
        self._event = event if isinstance(event, str) else None
        self._events = None if isinstance(event, str) else event

        converters = convert or {}
        fields: list[_Field] = []
        # Groups are read by number: the name only plans the field
        for name, number in self._regex.groupindex.items():
            if name == EVENT_GROUP:
                continue
            key = self._group_key(name)
            fields.append((key, number, converters.get(key)))
        self._fields = tuple(fields)

        self._derived = tuple(
            (key, source, func)
            for key, (source, func) in (derive or {}).items()
        )

        read = {key for key, _, _ in self._fields}
        self._reject(converters.keys() - read, ERROR_UNUSED_CONVERTER)
        self._reject(
            {source for _, source, _ in self._derived} - read,
            ERROR_DERIVE_SOURCE,
        )

        self._raw_level = self._classify()

    def _classify(self) -> ARSecurityLevel | None:
        """Find the level the raw message is exposed from, if at all."""

        levels = [
            level
            for converter in (
                [convert for _, _, convert in self._fields]
                + [func for _, _, func in self._derived]
            )
            if (level := _converter_level(converter)) is not None
        ]

        return max(levels) if levels else None

    def _group_key(self, name: str) -> AREventKey:
        """Resolve a group name into the event key it fills."""

        key = AREventKey.from_value(name)
        if key is AREventKey.UNKNOWN:
            raise ValueError(
                f"{self._regex.pattern!r} {ERROR_GROUP_KEY}: {name}"
            )

        return key

    def _reject(self, unknown: set[AREventKey], error: str) -> None:
        """Reject a plan naming a key the pattern does not fill."""

        if unknown:
            keys = ", ".join(sorted(unknown))
            raise ValueError(f"{self._regex.pattern!r} {error}: {keys}")

    def read(
        self, content: str, unknown: StrEnum
    ) -> dict[AREventKey, Any] | None:
        """Read the event out of a message, or None when it does not match."""

        if self._marker is not None and self._marker not in content:
            return None

        match = self._regex.search(content)
        if match is None:
            return None

        # The event type is either fixed or picked by the `event_type` group
        events = self._events
        event: dict[AREventKey, Any] = {
            AREventKey.EVENT_TYPE: cast("StrEnum", self._event)
            if events is None
            else events.get(match.group(EVENT_GROUP), unknown),
            # A shape carrying nothing sensitive is understood in full,
            # so its message needs no protection of its own
            AREventKey.RAW: content
            if self._raw_level is None
            else SensitiveText(content, self._raw_level),
        }
        for key, number, convert in self._fields:
            raw = match.group(number)
            if raw is None:
                continue
            value = convert(raw) if convert is not None else raw
            if value is not None:
                event[key] = value

        for key, source, derive in self._derived:
            value = event.get(source)
            if value is not None:
                event[key] = derive(value)

        return event


class ARLogPatternSet:
    """Every message shape one program emits, with its fallback type."""

    __slots__ = ("_patterns", "_unknown")

    def __init__(
        self,
        unknown: StrEnum,
        patterns: Iterable[ARLogPattern] = (),
    ) -> None:
        """Hold the patterns to try and the type an unread message gets."""

        self._unknown = unknown
        self._patterns = tuple(patterns)

    def translate(self, content: str) -> dict[AREventKey, Any]:
        """Read a message with the first pattern that matches it."""

        unknown = self._unknown
        for pattern in self._patterns:
            event = pattern.read(content, unknown)
            if event is not None:
                return event

        return {
            AREventKey.EVENT_TYPE: unknown,
            AREventKey.RAW: SensitiveText(content, ARSecurityLevel.UNSAFE),
        }


__all__ = [
    "ARLogPattern",
    "ARLogPatternSet",
]
