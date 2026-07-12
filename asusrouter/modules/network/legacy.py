"""Legacy backend for the network module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import hook_request, nvram_hooks
from asusrouter.modules.network.common import (
    bandwidth_limit,
    mac_filter_mode,
    read_mac_list,
)
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import Password, Ssid
from asusrouter.tools.types import ARCallbackType

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
        endpoint=AREndpoint.FETCH_DATA,
        request=hook_request(*nvram_hooks(*keys)),
    )


def _new_network(
    data: dict[str, Any],
    prefix: str,
    ssid: Ssid,
    maclist: str,
) -> dict[ARNetworkField, Any]:
    """Build the network-level fields for a new SSID group."""

    def _get(key: str) -> Any:
        return data.get(f"{prefix}_{key}")

    fields: dict[ARNetworkField, Any] = {
        ARNetworkField.SSID: ssid,
        # Aggregated from every band in the group by `_group`; a multi-band
        # network is on if any of its bands is on
        ARNetworkField.ENABLED: False,
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
    band_specs: list[tuple[ARWiFiBand, int, int | None]],
    enable_key: str,
    maclist: str,
) -> list[dict[ARNetworkField, Any]]:
    """Group per-band configs by SSID into networks."""

    groups: dict[str, dict[ARNetworkField, Any]] = {}
    order: list[str] = []
    units: dict[str, list[tuple[int, int | None]]] = {}

    for band, unit, slot in band_specs:
        prefix = f"wl{unit}" if slot is None else f"wl{unit}.{slot}"
        raw_ssid = data.get(f"{prefix}_ssid")
        ssid = Ssid.from_value_safe(raw_ssid)
        if ssid is None:
            continue

        key = str(raw_ssid)
        network = groups.get(key)
        if network is None:
            # Network-level fields come from the first band of the group;
            # bands sharing an SSID share these settings
            network = _new_network(data, prefix, ssid, maclist)
            groups[key] = network
            order.append(key)
            units[key] = []

        units[key].append((unit, slot))

        # Enable is per-band (main uses the radio state); the network is on
        # when any of its bands is on, so a single disabled band never hides it
        if raw_to_bool(data.get(f"{prefix}_{enable_key}")):
            network[ARNetworkField.ENABLED] = True

        network[ARNetworkField.BANDS].append(band)
        band_security: dict[ARNetworkField, Any] = {
            ARNetworkField.AUTH: ARWiFiAuthMode.from_value(
                data.get(f"{prefix}_auth_mode_x")
            ),
        }
        if cipher := raw_to_str(data.get(f"{prefix}_crypto")):
            band_security[ARNetworkField.CIPHER] = cipher
        network[ARNetworkField.SECURITY][band] = band_security

    for key in order:
        groups[key][ARNetworkField.HANDLE] = ARNetworkHandle(
            backend=ARNetworkBackend.LEGACY, units=tuple(units[key])
        )

    return [groups[key] for key in order]


def translate(
    data: dict[str, Any], wifi: dict[ARWiFiBand, int]
) -> dict[ARNetworkType, list[dict[ARNetworkField, Any]]]:
    """Translate raw per-band nvram into networks grouped by type."""

    result: dict[ARNetworkType, list[dict[ARNetworkField, Any]]] = {}

    main = _group(
        data,
        [(band, unit, None) for band, unit in wifi.items()],
        "radio",
        "maclist_x",
    )
    if main:
        result[ARNetworkType.MAINFH] = main

    guests = _group(
        data,
        [
            (band, unit, slot)
            for slot in _GUEST_SLOTS
            for band, unit in wifi.items()
        ],
        "bss_enabled",
        "maclist",
    )
    if guests:
        result[ARNetworkType.GUEST] = guests

    return result


def build_toggle_payload(
    handle: ARNetworkHandle, state: bool
) -> tuple[str, dict[str, Any]]:
    """Build the `(rc_service, arguments)` to enable/disable a network."""

    arguments: dict[str, Any] = {}
    has_guest = False
    for unit, slot in handle.units:
        if slot is None:
            arguments[f"wl{unit}_radio"] = int(state)
            continue
        has_guest = True
        arguments[f"wl{unit}.{slot}_bss_enabled"] = int(state)
        if state:
            arguments[f"wl{unit}.{slot}_expire"] = 0

    rc_service = (
        "restart_wireless;restart_firewall"
        if has_guest
        else "restart_wireless"
    )
    return rc_service, arguments
