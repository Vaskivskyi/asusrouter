"""Log event translation module for AsusRouter."""

from __future__ import annotations

from asusrouter.modules.log.translate.ahs import AREventAhs
from asusrouter.modules.log.translate.auto_channel_daemon import (
    AREventAutoChannelDaemon,
)
from asusrouter.modules.log.translate.avahi_daemon import AREventAvahiDaemon
from asusrouter.modules.log.translate.band_steering_daemon import (
    AREventBandSteeringDaemon,
)
from asusrouter.modules.log.translate.cron import AREventCron
from asusrouter.modules.log.translate.daemon import AREventDaemon
from asusrouter.modules.log.translate.dhcp_client import AREventDhcpClient
from asusrouter.modules.log.translate.disk_monitor import AREventDiskMonitor
from asusrouter.modules.log.translate.dispatch import (
    resolve_program,
    translate_entries,
    translate_entry,
)
from asusrouter.modules.log.translate.dnsmasq_dhcp import AREventDnsmasqDhcp
from asusrouter.modules.log.translate.hostapd import AREventHostapd
from asusrouter.modules.log.translate.http_daemon import AREventHttpDaemon
from asusrouter.modules.log.translate.init import AREventInit
from asusrouter.modules.log.translate.kernel import AREventKernel
from asusrouter.modules.log.translate.miniupnp import AREventMiniupnp
from asusrouter.modules.log.translate.modprobe import AREventModprobe
from asusrouter.modules.log.translate.ntp import AREventNtp
from asusrouter.modules.log.translate.rc_service import AREventRcService
from asusrouter.modules.log.translate.roaming_assistant import (
    AREventRoamingAssistant,
)
from asusrouter.modules.log.translate.syslog import AREventSyslog
from asusrouter.modules.log.translate.unknown import AREventUnknown
from asusrouter.modules.log.translate.wifi_scheduler import (
    AREventWifiScheduler,
)
from asusrouter.modules.log.translate.wireless_client_daemon import (
    AREventWirelessClientDaemon,
)

__all__ = [
    "AREventAhs",
    "AREventAutoChannelDaemon",
    "AREventAvahiDaemon",
    "AREventBandSteeringDaemon",
    "AREventCron",
    "AREventDaemon",
    "AREventDhcpClient",
    "AREventDiskMonitor",
    "AREventDnsmasqDhcp",
    "AREventHostapd",
    "AREventHttpDaemon",
    "AREventInit",
    "AREventKernel",
    "AREventMiniupnp",
    "AREventModprobe",
    "AREventNtp",
    "AREventRcService",
    "AREventRoamingAssistant",
    "AREventSyslog",
    "AREventUnknown",
    "AREventWifiScheduler",
    "AREventWirelessClientDaemon",
    "resolve_program",
    "translate_entries",
    "translate_entry",
]
