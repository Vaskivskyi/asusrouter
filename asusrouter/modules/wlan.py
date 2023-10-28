"""WLAN module."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Optional

from asusrouter.tools.converters import safe_bool, safe_int, safe_unpack_key
from asusrouter.tools.writers import nvram


class Wlan(str, Enum):
    """WLAN type class."""

    FREQ_2G = "2ghz"
    FREQ_5G = "5ghz"
    FREQ_5G2 = "5ghz2"
    FREQ_6G = "6ghz"
    UNKNOWN = "unknown"


# A map to correspond possible values to the WlanType
# E.g. `wlc_0` -> FREQ_2G, `wlc_1` -> FREQ_5G, etc.
# But also `wl0` -> FREQ_2G, `wl1` -> FREQ_5G, etc.
WLAN_TYPE: dict[str | int, Wlan] = {
    0: Wlan.FREQ_2G,
    1: Wlan.FREQ_5G,
    2: Wlan.FREQ_5G2,
    3: Wlan.FREQ_6G,
    "2.4G": Wlan.FREQ_2G,
    "5G": Wlan.FREQ_5G,
    "5G-2": Wlan.FREQ_5G2,
    "6G": Wlan.FREQ_6G,
    "wlc_0": Wlan.FREQ_2G,
    "wlc_1": Wlan.FREQ_5G,
    "wlc_2": Wlan.FREQ_5G2,
    "wlc_3": Wlan.FREQ_6G,
    "wl0": Wlan.FREQ_2G,
    "wl1": Wlan.FREQ_5G,
    "wl2": Wlan.FREQ_5G2,
    "wl3": Wlan.FREQ_6G,
}

# A map of NVRAM values for a GWLAN
MAP_GWLAN = (
    ("wl{}_akm"),
    ("wl{}_ap_isolate"),
    ("wl{}_auth"),
    ("wl{}_auth_mode"),
    ("wl{}_auth_mode_x"),
    ("wl{}_bridge"),
    ("wl{}_bss_enabled", safe_bool),
    ("wl{}_bss_maxassoc", safe_int),
    ("wl{}_bw_dl", safe_int),  # Bandwidth limit download
    ("wl{}_bw_enabled", safe_bool),  # Bandwidth limit switch
    ("wl{}_bw_ul", safe_int),  # Bandwidth limit upload
    ("wl{}_closed", safe_bool),
    ("wl{}_crypto"),
    ("wl{}_expire", safe_int),  # Expire time in s
    ("wl{}_expire_tmp", safe_int),  # Expire time left in s
    ("wl{}_gn_wbl_enable"),
    ("wl{}_gn_wbl_rule"),
    ("wl{}_gn_wbl_type"),
    ("wl{}_hwaddr"),  # MAC address
    ("wl{}_ifname"),  # Interface name
    ("wl{}_infra"),
    ("wl{}_key"),
    ("wl{}_key1"),
    ("wl{}_key2"),
    ("wl{}_key3"),
    ("wl{}_key4"),
    ("wl{}_lanaccess", safe_bool),  # LAN access
    ("wl{}_maclist"),
    ("wl{}_macmode"),
    ("wl{}_maxassoc", safe_int),
    ("wl{}_mbss"),
    ("wl{}_mfp"),
    ("wl{}_mode"),
    ("wl{}_net_reauth", safe_int),
    ("wl{}_preauth"),
    ("wl{}_radio", safe_bool),
    ("wl{}_radius_ipaddr"),
    ("wl{}_radius_key"),
    ("wl{}_radius_port", safe_int),
    ("wl{}_sae_anti_clog_threshold"),
    ("wl{}_sae_groups"),
    ("wl{}_sae_sync"),
    ("wl{}_ssid"),  # SSID
    ("wl{}_sta_retry_time"),
    ("wl{}_sync_node", safe_bool),  # Sync AiMesh nodes
    ("wl{}_unit"),  # GWLAN unit id
    ("wl{}_wep", safe_bool),
    ("wl{}_wep_x", safe_bool),
    ("wl{}_wfi_enable", safe_bool),
    ("wl{}_wfi_pinmode"),
    ("wl{}_wme"),
    ("wl{}_wme_bss_disable", safe_bool),
    ("wl{}_wpa_gtk_rekey"),
    ("wl{}_wpa_psk"),  # Password
    ("wl{}_wps_mode"),
)

# A map of NVRAM values for a WLAN
MAP_WLAN = (
    ("wl{}_auth_mode_x"),
    ("wl{}_bw"),
    ("wl{}_channel"),
    ("wl{}_chanspec"),
    ("wl{}_closed", safe_bool),
    ("wl{}_country_code"),
    ("wl{}_crypto"),
    ("wl{}_gmode_check"),
    ("wl{}_maclist_x"),
    ("wl{}_macmode"),
    ("wl{}_mbo_enable"),
    ("wl{}_mfp"),
    ("wl{}_nmode_x"),
    ("wl{}_optimizexbox_ckb"),
    ("wl{}_radio", safe_bool),
    ("wl{}_radius_ipaddr"),
    ("wl{}_radius_key"),
    ("wl{}_radius_port", safe_int),
    ("wl{}_ssid"),
    ("wl{}_wpa_gtk_rekey"),
    ("wl{}_wpa_psk"),
)


class AsusWLAN(IntEnum):
    """Asus WLAN state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


def wlan_nvram_request(wlan: list[Wlan] | None) -> str | None:
    """Create an NVRAM request for WLAN."""

    if not wlan:
        return None

    request = []

    for interface in wlan:
        for pair in MAP_WLAN:
            key, _ = safe_unpack_key(pair)
            index = list(Wlan).index(interface)
            request.append(key.format(index))

    return nvram(request)


def gwlan_nvram_request(wlan: list[Wlan] | None) -> str | None:
    """Create an NVRAM request for GWLAN."""

    if not wlan:
        return None

    request = []

    for interface in wlan:
        for pair in MAP_GWLAN:
            key, _ = safe_unpack_key(pair)
            index = list(Wlan).index(interface)
            for gid in range(1, 4):
                request.append(key.format(f"{index}.{gid}"))

    return nvram(request)


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusWLAN,
    arguments: Optional[dict[str, Any]] = None,
    expect_modify: bool = False,
) -> bool:
    """Set the parental control state."""

    # Check if arguments are available
    if not arguments:
        return False

    # Get the wlan type and id from arguments
    wlan_type = arguments.get("api_type")
    wlan_id = arguments.get("api_id")

    # Prepare the arguments
    arguments = {}

    service = None

    # Check wlan type
    if wlan_type == "wlan":
        service = "restart_wireless"
        arguments[f"wl{wlan_id}_radio"] = 1 if state == AsusWLAN.ON else 0
    elif wlan_type == "gwlan":
        service = "restart_wireless;restart_firewall"
        arguments[f"wl{wlan_id}_bss_enabled"] = 1 if state == AsusWLAN.ON else 0
        if state == AsusWLAN.ON:
            arguments[f"wl{wlan_id}_expire"] = 0

    if not service:
        return False

    # Call the service
    return await callback(
        service, arguments=arguments, apply=True, expect_modify=expect_modify
    )
