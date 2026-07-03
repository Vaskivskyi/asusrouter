"""Action module."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARActionType(FromStrMixin, StrEnum):
    """A modification applied to a device list, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ADD = "add"
    CLEAN = "clean"
    REMOVE = "remove"


class ARAction:
    """AsusRouter action.

    A universal class representing an action to run on the device.

    Actions are equal by exact type (router-global) by default;
    subclasses with defining parameters override equality and hash.
    """

    def __init__(self) -> None:
        """Initialize the action."""

    def __eq__(self, other: object) -> bool:
        """Equal by exact type (router-global by default)."""

        if not isinstance(other, ARAction):
            return NotImplemented
        return type(self) is type(other)

    def __hash__(self) -> int:
        """Hash by type."""

        return hash(type(self))

    def __repr__(self) -> str:
        """Representation of the action."""

        return f"<{type(self).__name__}>"


__all__ = [
    "ARAction",
    "ARActionType",
]
