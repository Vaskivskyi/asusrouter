"""WLAN module."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable

from asusrouter.modules.const import MapValueType
from asusrouter.tools.converters import (
    get_arguments,
    safe_bool,
    safe_int,
    safe_unpack_key,
)
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
    "wifi6e": Wlan.FREQ_6G,
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
MAP_GWLAN: list[MapValueType] = [
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
]


# A map of NVRAM values for a WLAN
MAP_WLAN: list[MapValueType] = [
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
]


class AsusWLAN(IntEnum):
    """Asus WLAN state."""

    UNKNOWN = -999
    OFF = 0
    ON = 1


def _nvram_request(
    wlan: list[Wlan] | None, mapping: list[MapValueType], guest: bool = False
) -> str | None:
    """Create an NVRAM request."""

    if not wlan:
        return None

    request = []

    for interface in wlan:
        for pair in mapping:
            key, _ = safe_unpack_key(pair)
            index = list(Wlan).index(interface)
            if guest:
                for gid in range(1, 4):
                    request.append(key.format(f"{index}.{gid}"))
            else:
                request.append(key.format(index))

    return nvram(request)


def wlan_nvram_request(wlan: list[Wlan] | None) -> str | None:
    """Create an NVRAM request for WLAN."""

    return _nvram_request(wlan, MAP_WLAN)


def gwlan_nvram_request(wlan: list[Wlan] | None) -> str | None:
    """Create an NVRAM request for GWLAN."""

    return _nvram_request(wlan, MAP_GWLAN, guest=True)


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusWLAN,
    **kwargs: Any,
) -> bool:
    """Set the parental control state."""

    # Get the arguments
    api_type, api_id = get_arguments(("api_type", "api_id"), **kwargs)

    # Check if the api_type and api_id are available
    if api_type is None or api_id is None:
        return False

    # Define the service and callback arguments for each api_type
    api_values = {
        "wlan": {
            "service": "restart_wireless",
            "callback_arguments": {
                f"wl{api_id}_radio": 1 if state == AsusWLAN.ON else 0
            },
        },
        "gwlan": {
            "service": "restart_wireless;restart_firewall",
            "callback_arguments": {
                f"wl{api_id}_bss_enabled": 1 if state == AsusWLAN.ON else 0,
                **({f"wl{api_id}_expire": 0} if state == AsusWLAN.ON else {}),
            },
        },
    }

    # Get the service and callback arguments for the given api_type
    api_value = api_values.get(api_type)
    if not api_value:
        return False

    # Call the service
    return await callback(
        api_value["service"],
        arguments=api_value["callback_arguments"],
        apply=True,
        expect_modify=kwargs.get("expect_modify", False),
    )
