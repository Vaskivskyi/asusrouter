"""Legacy backend for the network module.

Builds network profiles from per-band nvram on firmware without SDN: the
main network from `wl{unit}_*` and guests from `wl{unit}.{slot}_*`. Per-band
configs are grouped by SSID into one network each (handles smart-connect and
split-SSID setups alike).

Best-effort - the key set follows the v1 WLAN maps; not yet validated against
a real legacy-firmware device.
"""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network.common import (
    bandwidth_limit,
    mac_filter_mode,
    read_mac_list,
)
from asusrouter.modules.network.enums import ARNetworkField, ARNetworkType
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import Password, Ssid
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import nvram

# Per-band main network keys (`wl{unit}_*`)
_MAIN_KEYS = (
    "ssid",
    "wpa_psk",
    "auth_mode_x",
    "crypto",
    "closed",
    "macmode",
    "maclist_x",
    "radio",
    "ap_isolate",
)

# Per-band guest network keys (`wl{unit}.{slot}_*`)
_GUEST_KEYS = (
    "ssid",
    "wpa_psk",
    "auth_mode_x",
    "crypto",
    "closed",
    "macmode",
    "maclist",
    "bss_enabled",
    "ap_isolate",
    "lanaccess",
    "expire",
    "expire_tmp",
    "bw_enabled",
    "bw_dl",
    "bw_ul",
)
_GUEST_SLOTS = (1, 2, 3)


async def fetch(callback: ARCallbackType, wifi: dict[ARWiFiBand, int]) -> Any:
    """Fetch the per-band main and guest nvram for all bands."""

    if not wifi:
        return None

    keys: list[str] = []
    for unit in wifi.values():
        keys.extend(f"wl{unit}_{key}" for key in _MAIN_KEYS)
        for slot in _GUEST_SLOTS:
            keys.extend(f"wl{unit}.{slot}_{key}" for key in _GUEST_KEYS)

    return await callback(
        endpoint=AREndpoint.FETCH_DATA, request=f"hook={nvram(keys) or ''}"
    )


def _new_network(
    data: dict[str, Any],
    prefix: str,
    ssid: Ssid,
    enable_key: str,
    maclist: str,
) -> dict[ARNetworkField, Any]:
    """Build the network-level fields for a new SSID group."""

    def _get(key: str) -> Any:
        return data.get(f"{prefix}_{key}")

    fields: dict[ARNetworkField, Any] = {
        ARNetworkField.SSID: ssid,
        ARNetworkField.ENABLED: raw_to_bool(_get(enable_key)) or False,
        ARNetworkField.HIDDEN: raw_to_bool(_get("closed")) or False,
        ARNetworkField.AP_ISOLATE: raw_to_bool(_get("ap_isolate")) or False,
        ARNetworkField.BANDS: [],
        ARNetworkField.SECURITY: {},
    }

    password = Password.from_value_safe(_get("wpa_psk"))
    if password is not None:
        fields[ARNetworkField.PASSWORD] = password

    # Guest-only nvram (absent on the main network -> skipped)
    lan_access = raw_to_bool(_get("lanaccess"))
    if lan_access is not None:
        fields[ARNetworkField.LAN_ACCESS] = lan_access
    expire = raw_to_int(_get("expire"))
    if expire is not None:
        fields[ARNetworkField.EXPIRE] = expire
    remaining = raw_to_int(_get("expire_tmp"))
    if remaining is not None:
        fields[ARNetworkField.EXPIRE_REMAINING] = remaining

    fields.update(
        bandwidth_limit(_get("bw_enabled"), _get("bw_dl"), _get("bw_ul"))
    )

    mode = mac_filter_mode(_get("macmode"))
    if mode is not None:
        fields[ARNetworkField.MAC_FILTER_MODE] = mode
    macs = read_mac_list(_get(maclist))
    if macs:
        fields[ARNetworkField.MAC_FILTER_LIST] = macs

    return fields


def _group(
    data: dict[str, Any],
    band_prefixes: list[tuple[ARWiFiBand, str]],
    enable_key: str,
    maclist: str,
) -> list[dict[ARNetworkField, Any]]:
    """Group per-band configs by SSID into networks."""

    groups: dict[str, dict[ARNetworkField, Any]] = {}
    order: list[str] = []

    for band, prefix in band_prefixes:
        raw_ssid = data.get(f"{prefix}_ssid")
        ssid = Ssid.from_value_safe(raw_ssid)
        if ssid is None:
            continue

        key = str(raw_ssid)
        network = groups.get(key)
        if network is None:
            network = _new_network(data, prefix, ssid, enable_key, maclist)
            groups[key] = network
            order.append(key)

        network[ARNetworkField.BANDS].append(band)
        band_security: dict[ARNetworkField, Any] = {
            ARNetworkField.AUTH: ARWiFiAuthMode.from_value(
                data.get(f"{prefix}_auth_mode_x")
            ),
        }
        if cipher := raw_to_str(data.get(f"{prefix}_crypto")):
            band_security[ARNetworkField.CIPHER] = cipher
        network[ARNetworkField.SECURITY][band] = band_security

    return [groups[key] for key in order]


def translate(
    data: dict[str, Any], wifi: dict[ARWiFiBand, int]
) -> dict[ARNetworkType, list[dict[ARNetworkField, Any]]]:
    """Translate raw per-band nvram into networks grouped by type."""

    result: dict[ARNetworkType, list[dict[ARNetworkField, Any]]] = {}

    main = _group(
        data,
        [(band, f"wl{unit}") for band, unit in wifi.items()],
        "radio",
        "maclist_x",
    )
    if main:
        result[ARNetworkType.MAINFH] = main

    guests = _group(
        data,
        [
            (band, f"wl{unit}.{slot}")
            for slot in _GUEST_SLOTS
            for band, unit in wifi.items()
        ],
        "bss_enabled",
        "maclist",
    )
    if guests:
        result[ARNetworkType.GUEST] = guests

    return result
