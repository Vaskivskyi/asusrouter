"""Program-based dispatch of log entries to their event translators."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final

from asusrouter.modules.log.enums import ARProgram
from asusrouter.modules.log.parser import parse_program
from asusrouter.modules.log.translate.ahs import PATTERNS as AHS
from asusrouter.modules.log.translate.auto_channel_daemon import (
    PATTERNS as AUTO_CHANNEL_DAEMON,
)
from asusrouter.modules.log.translate.avahi_daemon import (
    PATTERNS as AVAHI_DAEMON,
)
from asusrouter.modules.log.translate.band_steering_daemon import (
    PATTERNS as BAND_STEERING_DAEMON,
)
from asusrouter.modules.log.translate.cron import PATTERNS as CRON
from asusrouter.modules.log.translate.daemon import PATTERNS as DAEMON
from asusrouter.modules.log.translate.dhcp_client import (
    PATTERNS as DHCP_CLIENT,
)
from asusrouter.modules.log.translate.disk_monitor import (
    PATTERNS as DISK_MONITOR,
)
from asusrouter.modules.log.translate.dnsmasq_dhcp import (
    PATTERNS as DNSMASQ_DHCP,
)
from asusrouter.modules.log.translate.hostapd import PATTERNS as HOSTAPD
from asusrouter.modules.log.translate.http_daemon import (
    PATTERNS as HTTP_DAEMON,
)
from asusrouter.modules.log.translate.init import PATTERNS as INIT
from asusrouter.modules.log.translate.kernel import PATTERNS as KERNEL
from asusrouter.modules.log.translate.miniupnp import PATTERNS as MINIUPNP
from asusrouter.modules.log.translate.modprobe import PATTERNS as MODPROBE
from asusrouter.modules.log.translate.ntp import PATTERNS as NTP
from asusrouter.modules.log.translate.pattern import ARLogPatternSet
from asusrouter.modules.log.translate.rc_service import PATTERNS as RC_SERVICE
from asusrouter.modules.log.translate.roaming_assistant import (
    PATTERNS as ROAMING_ASSISTANT,
)
from asusrouter.modules.log.translate.syslog import PATTERNS as SYSLOG
from asusrouter.modules.log.translate.unknown import AREventUnknown
from asusrouter.modules.log.translate.wifi_scheduler import (
    PATTERNS as WIFI_SCHEDULER,
)
from asusrouter.modules.log.translate.wireless_client_daemon import (
    PATTERNS as WIRELESS_CLIENT_DAEMON,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from asusrouter.modules.log.entry import ARLogEntry

_CACHE_SIZE: Final[int] = 4096

# A program with no patterns of its own; every message stays unknown
_FALLBACK = ARLogPatternSet(AREventUnknown.UNKNOWN)

_PATTERNS: dict[ARProgram, ARLogPatternSet] = {
    ARProgram.AHS: AHS,
    ARProgram.AUTO_CHANNEL_DAEMON: AUTO_CHANNEL_DAEMON,
    ARProgram.AVAHI_DAEMON: AVAHI_DAEMON,
    ARProgram.BAND_STEERING_DAEMON: BAND_STEERING_DAEMON,
    ARProgram.CRON: CRON,
    ARProgram.DHCP_CLIENT: DHCP_CLIENT,
    ARProgram.DISK_MONITOR: DISK_MONITOR,
    ARProgram.DNSMASQ_DHCP: DNSMASQ_DHCP,
    ARProgram.FTP_SERVER: DAEMON,
    ARProgram.HOSTAPD: HOSTAPD,
    ARProgram.HTTP_DAEMON: HTTP_DAEMON,
    ARProgram.INIT: INIT,
    ARProgram.ITUNES: DAEMON,
    ARProgram.KERNEL: KERNEL,
    ARProgram.MINIUPNP: MINIUPNP,
    ARProgram.MODPROBE: MODPROBE,
    ARProgram.NTP: NTP,
    ARProgram.RC_SERVICE: RC_SERVICE,
    ARProgram.ROAMING_ASSISTANT: ROAMING_ASSISTANT,
    ARProgram.SAMBA_SERVER: DAEMON,
    ARProgram.SYSLOG: SYSLOG,
    ARProgram.TIMEMACHINE: DAEMON,
    ARProgram.WIFI_SCHEDULER: WIFI_SCHEDULER,
    ARProgram.WIRELESS_CLIENT_DAEMON: WIRELESS_CLIENT_DAEMON,
}


def resolve_program(entry: ARLogEntry) -> ARProgram:
    """Resolve the entry's typed program (UNKNOWN when tag-less)."""

    if entry.program is None:
        return ARProgram.UNKNOWN

    return parse_program(entry.program.name)[0]


@lru_cache(maxsize=_CACHE_SIZE)
def _translate_content(program: ARProgram, content: str) -> dict[Any, Any]:
    """Translate a message, cached: nothing else shapes the result."""

    return _PATTERNS.get(program, _FALLBACK).translate(content)


def translate_entry(
    entry: ARLogEntry, program: ARProgram | None = None
) -> dict[Any, Any]:
    """Translate one entry; unmapped programs fall back to unknown."""

    if program is None:
        program = resolve_program(entry)

    return dict(_translate_content(program, entry.content.value))


def translate_entries(
    entries: Iterable[ARLogEntry],
) -> list[dict[Any, Any]]:
    """Translate every entry (unmapped ones marked explicitly unknown)."""

    return [translate_entry(entry) for entry in entries]
