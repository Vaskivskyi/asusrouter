"""Security tools."""

from __future__ import annotations

from enum import IntEnum, unique

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


@unique
class ARSecurityLevel(FromIntMixin, IntEnum):
    """Security levels for the data processed by AsusRouter.

    Levels:
    - **STRICT** - no user-related data is exposed outside
    - **DEFAULT** - non-sensitive user-related data is exposed
    - **SANITIZED** - user-related data is available but is
      automatically sanitized before being exposed
    - **UNSAFE** - user-related data is exposed
    """

    UNKNOWN = UNKNOWN_MEMBER
    STRICT = 0
    DEFAULT = 1
    SANITIZED = 5
    UNSAFE = 9

    @classmethod
    def at_least_strict(cls, level: ARSecurityLevel) -> bool:
        """Check if the security level is at least strict."""

        return level.value >= cls.STRICT.value

    @classmethod
    def at_least_default(cls, level: ARSecurityLevel) -> bool:
        """Check if the security level is at least default."""

        return level.value >= cls.DEFAULT.value

    @classmethod
    def at_least_sanitized(cls, level: ARSecurityLevel) -> bool:
        """Check if the security level is at least sanitized."""

        return level.value >= cls.SANITIZED.value
