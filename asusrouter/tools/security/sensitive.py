"""Sensitive value classification and rendering."""

from __future__ import annotations

from typing import Any, Final, Self

from asusrouter.tools.security.level import ARSecurityLevel

# General placeholder shown in place of any redacted value
REDACTED_STR: Final[str] = "-=REDACTED=-"


class _Redacted:
    """Singleton marker for a fully redacted sensitive value."""

    __slots__ = ()
    _instance: _Redacted | None = None

    def __new__(cls) -> Self:
        """Return the shared singleton instance."""

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __str__(self) -> str:
        """Return the redacted string representation."""

        return REDACTED_STR

    def __repr__(self) -> str:
        """Return the marker representation."""

        return "<redacted>"


# Shared marker returned when a value is fully hidden
REDACTED: Final[_Redacted] = _Redacted()


class ARSensitive:
    """Mixin marking a value as sensitive.

    A subclass declares its `reveal_level` (the minimum security level at
    which the raw value may be exposed) and whether it is `maskable` (can
    produce a deterministic sanitized representation via `mask`).
    """

    __slots__ = ()

    # Minimum level to expose the raw value; safest default is UNSAFE
    reveal_level: ARSecurityLevel = ARSecurityLevel.UNSAFE
    # Whether a deterministic sanitized representation is available
    maskable: bool = False

    def mask(self) -> Any:
        """Return a deterministic sanitized representation.

        Overridden by maskable types; the base returns the redaction marker.
        """

        return REDACTED


def render(value: Any, level: ARSecurityLevel) -> Any:
    """Render a value for the given security level.

    Non-sensitive values pass through unchanged. Sensitive values are
    exposed raw at or above their reveal level, sanitized in the masking
    band (maskable and at least SANITIZED), or redacted otherwise.
    """

    if not isinstance(value, ARSensitive):
        return value

    if level >= value.reveal_level:
        return value

    if value.maskable and level >= ARSecurityLevel.SANITIZED:
        return value.mask()

    return REDACTED
