"""Avahi daemon (avahi-daemon) log event translation for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin


class AREventAvahiDaemon(FromStrMixin, StrEnum):
    """Avahi daemon event types."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ALIAS_ESTABLISHED = "alias_established"
    NSS_UNSUPPORTED = "nss_unsupported"


PATTERNS = ARLogPatternSet(
    AREventAvahiDaemon.UNKNOWN,
    (
        # The mDNS alias the device announces itself under
        ARLogPattern(
            AREventAvahiDaemon.ALIAS_ESTABLISHED,
            r"Alias name \"(?P<alias>[^\"]+)\" successfully established",
            marker="Alias name",
        ),
        ARLogPattern(
            AREventAvahiDaemon.NSS_UNSUPPORTED,
            r"No NSS support for mDNS detected",
            marker="No NSS support",
        ),
    ),
)
