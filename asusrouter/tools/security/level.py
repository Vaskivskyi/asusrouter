"""Security level."""

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
    - **REASONABLE** - reasonably-sensitive user-related data (MAC, IP)
      is exposed raw, but secrets (passwords) are not
    - **UNSAFE** - user-related data is exposed
    """

    UNKNOWN = UNKNOWN_MEMBER

    STRICT = 0
    DEFAULT = 1
    SANITIZED = 5
    REASONABLE = 7
    UNSAFE = 9
