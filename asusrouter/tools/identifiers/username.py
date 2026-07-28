"""Username tools."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.security import (
    REDACTED_STR,
    ARSecurityLevel,
    ARSensitive,
)


class Username(ARSensitive):
    """Login name representation."""

    __slots__ = ("_value",)

    reveal_level = ARSecurityLevel.UNSAFE
    maskable = False

    def __init__(self, value: Any) -> None:
        """Initialize the username."""

        self._value = str(value)

    @classmethod
    def from_value(cls, value: Any) -> Username:
        """Create a Username."""

        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def from_value_safe(cls, value: Any) -> Username | None:
        """Create a Username, or None for a missing or empty value."""

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if str(value) == "":
            return None
        return cls(value)

    @property
    def value(self) -> str:
        """Return the raw username value."""

        return self._value

    def __str__(self) -> str:
        """Return the redacted representation."""

        return REDACTED_STR

    def __repr__(self) -> str:
        """Return the redacted representation."""

        return f"Username({REDACTED_STR})"

    def __eq__(self, other: object) -> bool:
        """Return whether two usernames are equal."""

        if isinstance(other, Username):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the username."""

        return hash(self._value)
