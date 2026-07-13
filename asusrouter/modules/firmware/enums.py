"""Firmware enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARFirmwareType(FromStrMixin, StrEnum):
    """Firmware types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    GNUTON = "gnuton"
    MERLIN = "merlin"
    STOCK = "stock"


class ARFirmwareWebError(FromIntMixin, IntEnum):
    """Firmware update error (`webs_state_error`)."""

    UNKNOWN = UNKNOWN_MEMBER

    NONE = 0
    DOWNLOAD_ERROR = 1
    SPACE_ERROR = 2
    FW_ERROR = 3


class ARFirmwareWebFetch(FromIntMixin, IntEnum):
    """Firmware update-info fetch state (`webs_state_update`)."""

    UNKNOWN = UNKNOWN_MEMBER

    ACTIVE = 0
    INACTIVE = 1


class ARFirmwareWebNotify(FromIntMixin, IntEnum):
    """Router firmware update signal (`webs_state_flag`)."""

    UNKNOWN = UNKNOWN_MEMBER

    DONT = 0  # No update / don't upgrade
    AVAILABLE = 1  # New firmware available
    FORCE = 2  # Force upgrade


class ARFirmwareWebUpgrade(FromIntMixin, IntEnum):
    """Firmware upgrade (install) state (`webs_state_upgrade`)."""

    UNKNOWN = UNKNOWN_MEMBER

    INACTIVE = -1
    DOWNLOADING = 0
    FINISHED = 1
    ACTIVE = 2


AR_FW_MERLIN_LIKE: frozenset[ARFirmwareType] = frozenset(
    {ARFirmwareType.MERLIN, ARFirmwareType.GNUTON}
)


__all__ = [
    "AR_FW_MERLIN_LIKE",
    "ARFirmwareType",
    "ARFirmwareWebError",
    "ARFirmwareWebFetch",
    "ARFirmwareWebNotify",
    "ARFirmwareWebUpgrade",
]
