"""Password tools."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.security import (
    REDACTED_STR,
    ARSecurityLevel,
    ARSensitive,
)


class Password(ARSensitive):
    """Password representation.

    A password is a secret: its raw value is exposed only at the unsafe
    security level, and its string form is always redacted to prevent
    accidental leaks in logs or tracebacks. Use `value` for explicit access.
    """

    __slots__ = ("_value",)

    reveal_level = ARSecurityLevel.UNSAFE
    maskable = False

    def __init__(self, value: Any) -> None:
        """Initialize the password."""

        self._value = str(value)

    @classmethod
    def from_value(cls, value: Any) -> Password:
        """Create a Password, returning the same instance if already one."""

        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def from_value_safe(cls, value: Any) -> Password | None:
        """Create a Password, or None for a missing or empty value."""

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if str(value) == "":
            return None
        return cls(value)

    @property
    def value(self) -> str:
        """Return the raw password value."""

        return self._value

    def __str__(self) -> str:
        """Return the redacted representation."""

        return REDACTED_STR

    def __repr__(self) -> str:
        """Return the redacted representation."""

        return f"Password({REDACTED_STR})"

    def __eq__(self, other: object) -> bool:
        """Return whether two passwords are equal."""

        if isinstance(other, Password):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the password."""

        return hash(self._value)
