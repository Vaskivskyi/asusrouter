"""Tests for the log translate module."""

from __future__ import annotations

from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.text import SensitiveText

# The levels the raw message is classified at, named for why it got one
IDENTIFIER = ARSecurityLevel.REASONABLE
UNREAD = ARSecurityLevel.UNSAFE


def classified(content: str, level: ARSecurityLevel) -> SensitiveText:
    """Build the raw message a pattern carrying `level` fields yields."""

    return SensitiveText(content, level)


def unread(content: str) -> SensitiveText:
    """Build the raw message of a line no pattern matched."""

    return SensitiveText(content, UNREAD)


__all__ = [
    "IDENTIFIER",
    "UNREAD",
    "classified",
    "unread",
]
