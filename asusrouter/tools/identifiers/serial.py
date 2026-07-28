"""Serial number tools."""

from __future__ import annotations

from typing import Any

from asusrouter.tools.security import ARSecurityLevel, ARSensitive, hmac_digest

# Bytes of digest used to build a deterministic pseudo-serial
_MASK_BYTES = 4


class Serial(ARSensitive):
    """Serial number representation."""

    __slots__ = ("_value",)

    reveal_level = ARSecurityLevel.REASONABLE
    maskable = True

    def __init__(self, value: Any) -> None:
        """Initialize the serial."""

        self._value = str(value)

    @classmethod
    def from_value(cls, value: Any) -> Serial:
        """Create a Serial."""

        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def from_value_safe(cls, value: Any) -> Serial | None:
        """Create a Serial, or None for a missing or empty value."""

        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if str(value) == "":
            return None
        return cls(value)

    @property
    def value(self) -> str:
        """Return the raw serial value."""

        return self._value

    def mask(self) -> Serial:
        """Return a deterministic pseudo-serial."""

        digest = hmac_digest(self._value.encode())
        return Serial(f"sn-{digest[:_MASK_BYTES].hex()}")

    def __str__(self) -> str:
        """Return the raw serial value."""

        return self._value

    def __repr__(self) -> str:
        """Return the serial representation."""

        return f"Serial({self._value})"

    def __eq__(self, other: object) -> bool:
        """Return whether two serials are equal."""

        if isinstance(other, Serial):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the serial."""

        return hash(self._value)
