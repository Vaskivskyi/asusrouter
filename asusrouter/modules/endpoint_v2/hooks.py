"""AsusRouter appGet hooks."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARHook(FromStrMixin, StrEnum):
    """appGet hook commands, sent as `hook=name(args)`."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # System
    CPU_USAGE = "cpu_usage"
    HEADER_INFO = "get_header_info"
    LABEL_MAC = "get_label_mac"
    LAN_HWADDR = "get_lan_hwaddr"
    LANGUAGE_SUPPORT_LIST = "language_support_list"
    MEMORY_USAGE = "memory_usage"
    NVRAM_GET = "nvram_get"
    UI_SUPPORT = "get_ui_support"
    UPTIME = "uptime"

    # SpeedTest
    OOKLA_SPEEDTEST_HISTORY = "ookla_speedtest_get_history"
    OOKLA_SPEEDTEST_RESULT = "ookla_speedtest_get_result"
    OOKLA_SPEEDTEST_SERVERS = "ookla_speedtest_get_servers"

    # Traffic
    NETDEV = "netdev"

    # Clients
    CFG_CLIENTLIST = "get_cfg_clientlist"
    CLIENTLIST = "get_clientlist"
    CLIENTLIST_DATABASE = "get_clientlist_from_json_database"
    NEWOB_ONBOARDINGLIST = "get_newob_onboardinglist"

    # VPN
    IPSEC_CONNECTIONS = "get_ipsec_conn"
    VPNC_NONDEF_WAN_PROFILES = "get_vpnc_nondef_wan_prof_list"
    VPNC_STATUS = "get_vpnc_status"
    WIREGUARD_SERVER_STATUS = "get_wgsc_status"

    # WAN
    WAN_UNIT = "get_wan_unit"

    # WiFi
    CHANNEL_LIST_2G = "channel_list_2g"
    CHANNEL_LIST_5G = "channel_list_5g"
    CHANNEL_LIST_5G2 = "channel_list_5g_2"
    CHANNEL_LIST_6G = "channel_list_6g"
    CHANNEL_LIST_6G2 = "channel_list_6g_2"
    CHANSPECS_2G = "chanspecs_2g"
    CHANSPECS_5G = "chanspecs_5g"
    CHANSPECS_5G2 = "chanspecs_5g_2"
    CHANSPECS_6G = "chanspecs_6g"
    CHANSPECS_6G2 = "chanspecs_6g_2"
    WL_CAP_2G = "wl_cap_2g"
    WL_CAP_5G = "wl_cap_5g"
    WL_CAP_5G2 = "wl_cap_5g_2"
    WL_CAP_6G = "wl_cap_6g"
    WL_CAP_6G2 = "wl_cap_6g_2"
    WL_CHANNEL_LIST_2G = "get_wl_channel_list_2g"
    WL_CHANNEL_LIST_5G = "get_wl_channel_list_5g"
    WL_CHANNEL_LIST_5G2 = "get_wl_channel_list_5g_2"
    WL_CHANNEL_LIST_6G = "get_wl_channel_list_6g"
    WL_CHANNEL_LIST_6G2 = "get_wl_channel_list_6g_2"
    WL_CONTROL_CHANNEL = "wl_control_channel"
    WL_NBAND_INFO = "wl_nband_info"


class ARHookItem(Protocol):
    """An item that renders itself as a single appGet hook call."""

    def as_hook(self) -> tuple[ARHook, str]:
        """Return the hook and its argument string."""


def hook_request(*items: ARHook | tuple[ARHook, str] | ARHookItem) -> str:
    """Build an appGet `hook=` request string from one or more hooks."""

    parts: list[str] = []
    for item in items:
        if isinstance(item, ARHook):
            hook, args = item, ""
        elif isinstance(item, tuple):
            hook, args = item
        else:
            hook, args = item.as_hook()
        parts.append(f"{hook.value}({args})")
    return "hook=" + ";".join(parts)


def nvram_hooks(*keys: str) -> tuple[tuple[ARHook, str], ...]:
    """Render dynamically built NVRAM keys as `nvram_get` hook calls."""

    return tuple((ARHook.NVRAM_GET, key) for key in keys)
