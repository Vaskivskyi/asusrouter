"""SSID tools."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.security import ARSecurityLevel, ARSensitive


class Ssid(ARSensitive):
    """WiFi SSID representation.

    An SSID is broadcast unless the network is hidden, so it is shown by
    default and only hidden under a strict security level.
    """

    __slots__ = ("_value",)

    reveal_level = ARSecurityLevel.DEFAULT
    maskable = False

    def __init__(self, value: Any) -> None:
        """Initialize the SSID."""

        self._value = str(value)

    @classmethod
    def from_value(cls, value: Any) -> Ssid:
        """Create an Ssid, returning the same instance if already one."""

        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def from_value_safe(cls, value: Any) -> Ssid | None:
        """Create an Ssid, or None for a missing or empty value."""

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if str(value) == "":
            return None
        return cls(value)

    @property
    def value(self) -> str:
        """Return the raw SSID value."""

        return self._value

    def __str__(self) -> str:
        """Return the raw SSID value."""

        return self._value

    def __repr__(self) -> str:
        """Return the SSID representation."""

        return f"Ssid({self._value!r})"

    def __eq__(self, other: object) -> bool:
        """Return whether two SSIDs are equal."""

        if isinstance(other, Ssid):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the SSID."""

        return hash(self._value)
