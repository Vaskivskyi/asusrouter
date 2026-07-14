"""Connection module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.tools.enum import FromStrMixin


class ARConnection(FromStrMixin, StrEnum):
    """Connection types."""

    UNKNOWN = "unknown"

    HTTPS = "https"
    SSH = "ssh"
