"""Text security tools."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from asusrouter.tools.security.level import ARSecurityLevel
from asusrouter.tools.security.sensitive import (
    REDACTED_STR,
    ARSensitive,
    render,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class SensitiveText(ARSensitive):
    """A device string exposed only from its own level upwards."""

    __slots__ = ("_reveal_level", "_value")

    maskable = False

    def __init__(
        self,
        value: str,
        reveal_level: ARSecurityLevel = ARSecurityLevel.UNSAFE,
    ) -> None:
        """Initialize the text and the level it may be shown at."""

        self._value = value
        self._reveal_level = reveal_level

    @property
    def reveal_level(self) -> ARSecurityLevel:  # type: ignore[override]
        """Return the level from which the text may be shown."""

        return self._reveal_level

    @property
    def value(self) -> str:
        """Return the text itself."""

        return self._value

    def __str__(self) -> str:
        """Return the redacted representation."""

        return REDACTED_STR

    def __repr__(self) -> str:
        """Return the redacted representation."""

        return f"SensitiveText({REDACTED_STR})"

    def __eq__(self, other: object) -> bool:
        """Return whether two texts hold the same value and level."""

        if isinstance(other, SensitiveText):
            return (
                self._value == other._value
                and self._reveal_level == other._reveal_level
            )
        return NotImplemented

    def __hash__(self) -> int:
        """Return the hash of the text and its level."""

        return hash((self._value, self._reveal_level))


def searchable(secret: ARSensitive) -> str | None:
    """Return a secret's text as a message would spell it, if it has one."""

    value = getattr(secret, "value", None)
    text = str(value) if value is not None else str(secret)

    return text if text and text != REDACTED_STR else None


def remove_secrets(
    text: str, secrets: Iterable[ARSensitive], level: ARSecurityLevel
) -> str:
    """Take known secret values out of free text below their level."""

    for secret in secrets:
        if level >= secret.reveal_level:
            continue
        value = searchable(secret)
        if value is None:
            continue

        replacement = str(render(secret, level)).replace("\\", "\\\\")
        text = re.sub(re.escape(value), replacement, text, flags=re.I)

    return text


__all__ = [
    "SensitiveText",
    "remove_secrets",
    "searchable",
]
