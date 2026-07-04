"""Hostname tools."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.security import ARSecurityLevel, ARSensitive, hmac_digest

# Bytes of digest used to build a deterministic pseudo-hostname
_MASK_BYTES = 4


class Hostname(ARSensitive):
    """Hostname representation (IP address or DNS name).

    A hostname identifies the user's device, so it is exposed raw only at
    the reasonable level and can be replaced by a deterministic pseudo-host
    when sanitized.
    """

    __slots__ = ("_value",)

    reveal_level = ARSecurityLevel.REASONABLE
    maskable = True

    def __init__(self, value: Any) -> None:
        """Initialize the hostname."""

        self._value = str(value)

    @classmethod
    def from_value(cls, value: Any) -> Hostname:
        """Create a Hostname, returning the same instance if already one."""

        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def from_value_safe(cls, value: Any) -> Hostname | None:
        """Create a Hostname, or None for a missing or empty value."""

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if str(value) == "":
            return None
        return cls(value)

    @property
    def value(self) -> str:
        """Return the raw hostname value."""

        return self._value

    def mask(self) -> Hostname:
        """Return a deterministic pseudo-hostname."""

        digest = hmac_digest(self._value.encode())
        return Hostname(f"host-{digest[:_MASK_BYTES].hex()}")

    def __str__(self) -> str:
        """Return the raw hostname value."""

        return self._value

    def __repr__(self) -> str:
        """Return the hostname representation."""

        return f"Hostname({self._value!r})"

    def __eq__(self, other: object) -> bool:
        """Return whether two hostnames are equal."""

        if isinstance(other, Hostname):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the hostname."""

        return hash(self._value)
