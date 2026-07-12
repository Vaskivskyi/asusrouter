"""Legacy backend for the network module."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import hook_request
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
from asusrouter.modules.nvram import ARNvramIndexSource, ARNvramIndexType
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
    ARNvramIndexType.WL_SSID,
    ARNvramIndexType.WL_WPA_PSK,
    ARNvramIndexType.WL_AUTH_MODE,
    ARNvramIndexType.WL_CRYPTO,
    ARNvramIndexType.WL_CLOSED,
    ARNvramIndexType.WL_MACMODE,
    ARNvramIndexType.WL_MACLIST_X,
    ARNvramIndexType.WL_RADIO,
    ARNvramIndexType.WL_AP_ISOLATE,
)

# Per-band guest network keys (`wl{unit}.{slot}_*`)
_GUEST_KEYS = (
    ARNvramIndexType.WL_SSID,
    ARNvramIndexType.WL_WPA_PSK,
    ARNvramIndexType.WL_AUTH_MODE,
    ARNvramIndexType.WL_CRYPTO,
    ARNvramIndexType.WL_CLOSED,
    ARNvramIndexType.WL_MACMODE,
    ARNvramIndexType.WL_MACLIST,
    ARNvramIndexType.WL_BSS_ENABLED,
    ARNvramIndexType.WL_AP_ISOLATE,
    ARNvramIndexType.WL_LANACCESS,
    ARNvramIndexType.WL_EXPIRE,
    ARNvramIndexType.WL_EXPIRE_TMP,
    ARNvramIndexType.WL_BW_ENABLED,
    ARNvramIndexType.WL_BW_DL,
    ARNvramIndexType.WL_BW_UL,
)
_GUEST_SLOTS = (1, 2, 3)


async def fetch(callback: ARCallbackType, wifi: dict[ARWiFiBand, int]) -> Any:
    """Fetch the per-band main and guest nvram for all bands."""

    if not wifi:
        return None

    items: list[ARNvramIndexSource] = []
    for unit in wifi.values():
        items.extend(ARNvramIndexSource(kind, unit) for kind in _MAIN_KEYS)
        for slot in _GUEST_SLOTS:
            items.extend(
                ARNvramIndexSource(kind, f"{unit}.{slot}")
                for kind in _GUEST_KEYS
            )

    return await callback(
        endpoint=AREndpoint.FETCH_DATA, request=hook_request(*items)
    )


def _new_network(
    data: dict[str, Any],
    index: int | str,
    ssid: Ssid,
    maclist: ARNvramIndexType,
) -> dict[ARNetworkField, Any]:
    """Build the network-level fields for a new SSID group."""

    def _get(kind: ARNvramIndexType) -> Any:
        return data.get(kind.key(index))

    fields: dict[ARNetworkField, Any] = {
        ARNetworkField.SSID: ssid,
        # Aggregated from every band in the group by `_group`; a multi-band
        # network is on if any of its bands is on
        ARNetworkField.ENABLED: False,
        ARNetworkField.HIDDEN: (
            raw_to_bool(_get(ARNvramIndexType.WL_CLOSED)) or False
        ),
        ARNetworkField.AP_ISOLATE: (
            raw_to_bool(_get(ARNvramIndexType.WL_AP_ISOLATE)) or False
        ),
        ARNetworkField.BANDS: [],
        ARNetworkField.SECURITY: {},
    }

    password = Password.from_value_safe(_get(ARNvramIndexType.WL_WPA_PSK))
    if password is not None:
        fields[ARNetworkField.PASSWORD] = password

    # Guest-only nvram (absent on the main network -> skipped)
    lan_access = raw_to_bool(_get(ARNvramIndexType.WL_LANACCESS))
    if lan_access is not None:
        fields[ARNetworkField.LAN_ACCESS] = lan_access
    expire = raw_to_int(_get(ARNvramIndexType.WL_EXPIRE))
    if expire is not None:
        fields[ARNetworkField.EXPIRE] = expire
    remaining = raw_to_int(_get(ARNvramIndexType.WL_EXPIRE_TMP))
    if remaining is not None:
        fields[ARNetworkField.EXPIRE_REMAINING] = remaining

    fields.update(
        bandwidth_limit(
            _get(ARNvramIndexType.WL_BW_ENABLED),
            _get(ARNvramIndexType.WL_BW_DL),
            _get(ARNvramIndexType.WL_BW_UL),
        )
    )

    mode = mac_filter_mode(_get(ARNvramIndexType.WL_MACMODE))
    if mode is not None:
        fields[ARNetworkField.MAC_FILTER_MODE] = mode
    macs = read_mac_list(_get(maclist))
    if macs:
        fields[ARNetworkField.MAC_FILTER_LIST] = macs

    return fields


def _group(
    data: dict[str, Any],
    band_specs: list[tuple[ARWiFiBand, int, int | None]],
    enable_key: ARNvramIndexType,
    maclist: ARNvramIndexType,
) -> list[dict[ARNetworkField, Any]]:
    """Group per-band configs by SSID into networks."""

    groups: dict[str, dict[ARNetworkField, Any]] = {}
    order: list[str] = []
    units: dict[str, list[tuple[int, int | None]]] = {}

    for band, unit, slot in band_specs:
        index = unit if slot is None else f"{unit}.{slot}"
        raw_ssid = data.get(ARNvramIndexType.WL_SSID.key(index))
        ssid = Ssid.from_value_safe(raw_ssid)
        if ssid is None:
            continue

        key = str(raw_ssid)
        network = groups.get(key)
        if network is None:
            # Network-level fields come from the first band of the group;
            # bands sharing an SSID share these settings
            network = _new_network(data, index, ssid, maclist)
            groups[key] = network
            order.append(key)
            units[key] = []

        units[key].append((unit, slot))

        # Enable is per-band (main uses the radio state); the network is on
        # when any of its bands is on, so a single disabled band never hides it
        if raw_to_bool(data.get(enable_key.key(index))):
            network[ARNetworkField.ENABLED] = True

        network[ARNetworkField.BANDS].append(band)
        band_security: dict[ARNetworkField, Any] = {
            ARNetworkField.AUTH: ARWiFiAuthMode.from_value(
                data.get(ARNvramIndexType.WL_AUTH_MODE.key(index))
            ),
        }
        if cipher := raw_to_str(
            data.get(ARNvramIndexType.WL_CRYPTO.key(index))
        ):
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
        ARNvramIndexType.WL_RADIO,
        ARNvramIndexType.WL_MACLIST_X,
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
        ARNvramIndexType.WL_BSS_ENABLED,
        ARNvramIndexType.WL_MACLIST,
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
            arguments[ARNvramIndexType.WL_RADIO.key(unit)] = int(state)
            continue
        has_guest = True
        index = f"{unit}.{slot}"
        arguments[ARNvramIndexType.WL_BSS_ENABLED.key(index)] = int(state)
        if state:
            arguments[ARNvramIndexType.WL_EXPIRE.key(index)] = 0

    rc_service = (
        "restart_wireless;restart_firewall"
        if has_guest
        else "restart_wireless"
    )
    return rc_service, arguments
