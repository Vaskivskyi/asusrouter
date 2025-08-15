"""Security tools."""

from __future__ import annotations

from enum import IntEnum, unique
from typing import Any

from asusrouter.tools.converters import safe_int


@unique
class ARSecurityLevel(IntEnum):
    """Security levels for the data processed by AsusRouter.

    Levels:
    - **STRICT** - no user-related data is exposed outside
    - **DEFAULT** - non-sensitive user-related data is exposed
    - **SANITIZED** - user-related data is available but is
      automatically sanitized before being exposed
    - **UNSAFE** - user-related data is exposed
    """

    UNKNOWN = -999
    STRICT = 0
    DEFAULT = 1
    SANITIZED = 5
    UNSAFE = 9

    @classmethod
    def from_value(cls, value: Any) -> ARSecurityLevel:
        """Create an ARSecurityLevel from any value."""

        # Already an enum member
        if isinstance(value, cls):
            return value

        # Try integer conversion
        vint = safe_int(value)
        if vint is not None:
            try:
                return cls(vint)
            except ValueError:
                return cls.UNKNOWN

        # Fallback: try string names
        if isinstance(value, str):
            try:
                return cls[value.strip().upper()]
            except KeyError:
                return cls.UNKNOWN

        return cls.UNKNOWN
