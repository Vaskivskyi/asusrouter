"""Common status module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin

# Key holding the status code in a device action response
STATUS_CODE_KEY = "statusCode"

# Key holding the modify flag in an applyapp response (truthy on success)
MODIFY_KEY = "modify"


class ARStatusCode(FromStrMixin, StrEnum):
    """A status code returned by a device action, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    SUCCESS = "success"
