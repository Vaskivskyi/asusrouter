"""Sensitive value classification and rendering."""

from __future__ import annotations

from typing import Any, Final

from asusrouter.tools.security.level import ARSecurityLevel

# General placeholder shown in place of any redacted value
REDACTED_STR: Final[str] = "-=REDACTED=-"


class _Redacted:
    """Marker for a fully redacted sensitive value.

    A single shared instance (`REDACTED`) is used everywhere.
    """

    __slots__ = ()

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


class Sensitive(ARSensitive):
    """Generic sensitive value with a per-instance reveal level.

    Wraps an arbitrary value (e.g. a request payload) that cannot be
    deterministically sanitized: it is shown raw at or above its reveal
    level and redacted otherwise.
    """

    __slots__ = ("_reveal_level", "_value")

    def __init__(
        self,
        value: Any,
        reveal_level: ARSecurityLevel = ARSecurityLevel.UNSAFE,
    ) -> None:
        """Initialize the sensitive value."""

        self._value = value
        self._reveal_level = reveal_level

    @property
    def reveal_level(self) -> ARSecurityLevel:  # type: ignore[override]
        """Return the per-instance reveal level."""

        return self._reveal_level

    @property
    def value(self) -> Any:
        """Return the raw wrapped value."""

        return self._value

    def __str__(self) -> str:
        """Return the raw value as a string."""

        return str(self._value)

    def __repr__(self) -> str:
        """Return the sensitive value representation."""

        return f"Sensitive({self._value!r}, {self._reveal_level!r})"


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
