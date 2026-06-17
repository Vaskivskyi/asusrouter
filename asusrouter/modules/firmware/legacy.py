"""Legacy firmware enums."""

from __future__ import annotations

from enum import Enum


class WebsError(Enum):
    """Webs Upgrade error status."""

    UNKNOWN = -999
    NONE = 0
    DOWNLOAD_ERROR = 1
    SPACE_ERROR = 2
    FW_ERROR = 3


class WebsFlag(Enum):
    """Webs flag status."""

    UNKNOWN = -999
    DONT = 0  # Don't do upgrade
    AVAILABLE = 1  # New FW available
    FORCE = 2  # Force upgrade


class WebsUpdate(Enum):
    """Webs Update status."""

    UNKNOWN = -999
    ACTIVE = 0
    INACTIVE = 1


class WebsUpgrade(Enum):
    """Webs Upgrade status."""

    UNKNOWN = -999
    INACTIVE = -1
    DOWNLOADING = 0
    FINISHED = 1
    ACTIVE = 2
