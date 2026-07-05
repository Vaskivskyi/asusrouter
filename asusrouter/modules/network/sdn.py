"""SDN backend for the network module.

Reads the Software-Defined Network profiles (main + guest/IoT) on modern
firmware and builds the per-type network profiles.
"""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.network.common import (
    decode,
    mac_filter_mode,
    read_mac_list,
)
from asusrouter.modules.network.enums import (
    ARNetworkField,
    ARNetworkSchedule,
    ARNetworkType,
)
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import Password, Ssid
from asusrouter.tools.types import ARCallbackType
from asusrouter.tools.writers import nvram

# `sdn_rl` column indices (see `set_sdn_profile` in the firmware)
_COL_IDX = 0
_COL_NAME = 1
_COL_ENABLE = 2
_COL_APG_IDX = 5

# SDN profile names that store their AP group under the `apm` prefix
_MAIN_NAMES = ("MAINFH", "MAINBH")

# Minimum `>`-columns in a security / dut_list row to be usable
_SECURITY_COLS = 4
_DUT_COLS = 2

# Per-profile AP-group keys we read and parse
_AP_KEYS = (
    "enable",
    "ssid",
    "hide_ssid",
    "security",
    "ap_isolate",
    "macmode",
    "mlo",
    "maclist",
    "dut_list",
    "11be",
    "timesched",
    "sched",
    "expiretime",
)

# WiFi band bitmask -> band (`wifi_band_options_cb`): a band matches any of
# its bits (single vs dual-band variants)
_BAND_BITS: dict[ARWiFiBand, int] = {
    ARWiFiBand.BAND_2G1: 1,
    ARWiFiBand.BAND_5G1: 2 | 4,
    ARWiFiBand.BAND_5G2: 8,
    ARWiFiBand.BAND_6G1: 16 | 32,
    ARWiFiBand.BAND_6G2: 64,
}


def _split_rules(decoded: str) -> list[list[str]]:
    """Split a decoded rule-list into rows of `>`-separated columns."""

    return [chunk.split(">") for chunk in decoded.split("<") if chunk != ""]


def _parse_sdn_rl(raw: Any) -> list[tuple[str, str, int, bool]]:
    """Parse `sdn_rl` into `(name, prefix, apg_idx, enabled)` per profile."""

    profiles: list[tuple[str, str, int, bool]] = []
    for cols in _split_rules(decode(raw)):
        if len(cols) <= _COL_APG_IDX or cols[_COL_IDX] == "0":
            continue
        name = cols[_COL_NAME]
        apg_idx = raw_to_int(cols[_COL_APG_IDX])
        if apg_idx is None:
            continue
        prefix = "apm" if name in _MAIN_NAMES else "apg"
        enabled = raw_to_bool(cols[_COL_ENABLE]) or False
        profiles.append((name, prefix, apg_idx, enabled))
    return profiles


def _parse_security(
    raw: Any, bands: list[ARWiFiBand]
) -> tuple[Password | None, dict[ARWiFiBand, dict[ARNetworkField, Any]]]:
    """Decode `security` into the network password and per-band auth/cipher.

    The password is shared by the whole network (each band group repeats it);
    only auth and cipher vary per band (6G forces SAE).
    """

    entries = [
        (raw_to_int(cols[0]) or 0, cols[1], cols[2], cols[3])
        for cols in _split_rules(decode(raw))
        if len(cols) >= _SECURITY_COLS
    ]

    password: Password | None = None
    for *_, raw_password in entries:
        password = Password.from_value_safe(raw_password)
        if password is not None:
            break

    per_band: dict[ARWiFiBand, dict[ARNetworkField, Any]] = {}
    for band in bands:
        band_bits = _BAND_BITS.get(band, 0)
        for bitmask, auth, cipher, _ in entries:
            if bitmask & band_bits:
                per_band[band] = {
                    ARNetworkField.AUTH: ARWiFiAuthMode.from_value(auth),
                    ARNetworkField.CIPHER: cipher,
                }
                break

    return password, per_band


def _dut_bands(raw: Any, bands: list[ARWiFiBand]) -> list[ARWiFiBand]:
    """Decode `dut_list` into the device bands the profile is bound to."""

    union = 0
    for cols in _split_rules(decode(raw)):
        if len(cols) >= _DUT_COLS:
            union |= raw_to_int(cols[1]) or 0

    return [band for band in bands if _BAND_BITS.get(band, 0) & union]


def _schedule(
    timesched: Any, sched: Any, expiretime: Any
) -> dict[ARNetworkField, Any]:
    """Build the scheduling fields, empty when scheduling is off."""

    mode = ARNetworkSchedule.from_value(timesched)
    if mode in (ARNetworkSchedule.UNKNOWN, ARNetworkSchedule.DISABLED):
        return {}

    fields: dict[ARNetworkField, Any] = {ARNetworkField.SCHEDULE_MODE: mode}
    if weekly := raw_to_str(sched):
        fields[ARNetworkField.SCHEDULE] = weekly
    if expiry := raw_to_str(expiretime):
        fields[ARNetworkField.EXPIRY] = expiry
    return fields


def _ap_request(profiles: list[tuple[str, str, int, bool]]) -> str:
    """Build the appGet request for the referenced AP groups."""

    keys = [
        f"{prefix}{apg_idx}_{key}"
        for _, prefix, apg_idx, _ in profiles
        for key in _AP_KEYS
    ]
    return f"hook={nvram(keys) or ''}"


async def fetch(callback: ARCallbackType) -> Any:
    """Fetch `sdn_rl`, then the AP groups it references."""

    request = f"hook={nvram(['sdn_rl']) or ''}"
    first = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)
    sdn_rl = first.get("sdn_rl") if isinstance(first, dict) else None
    if sdn_rl is None:
        return None

    profiles = _parse_sdn_rl(sdn_rl)
    if not profiles:
        return {"sdn_rl": sdn_rl}

    second = await callback(
        endpoint=AREndpoint.FETCH_DATA, request=_ap_request(profiles)
    )
    ap_data = second if isinstance(second, dict) else {}
    return {"sdn_rl": sdn_rl, **ap_data}


def _build_network(
    data: dict[str, Any],
    prefix: str,
    apg_idx: int,
    bands: list[ARWiFiBand],
    sdn_enabled: bool,
) -> dict[ARNetworkField, Any]:
    """Build the network profile dict for one AP group."""

    def _get(key: str) -> Any:
        return data.get(f"{prefix}{apg_idx}_{key}")

    # A network is on only when both the SDN profile and its AP group are on
    enabled = sdn_enabled and (raw_to_bool(_get("enable")) or False)

    fields: dict[ARNetworkField, Any] = {
        ARNetworkField.ENABLED: enabled,
        ARNetworkField.HIDDEN: raw_to_bool(_get("hide_ssid")) or False,
        ARNetworkField.WIFI7: raw_to_bool(_get("11be")) or False,
        ARNetworkField.AP_ISOLATE: raw_to_bool(_get("ap_isolate")) or False,
    }

    ssid = Ssid.from_value_safe(_get("ssid"))
    if ssid is not None:
        fields[ARNetworkField.SSID] = ssid

    mlo = raw_to_int(_get("mlo"))
    if mlo is not None:
        fields[ARNetworkField.MLO] = mlo

    fields.update(
        _schedule(_get("timesched"), _get("sched"), _get("expiretime"))
    )

    mode = mac_filter_mode(_get("macmode"))
    if mode is not None:
        fields[ARNetworkField.MAC_FILTER_MODE] = mode
    mac_list = read_mac_list(_get("maclist"))
    if mac_list:
        fields[ARNetworkField.MAC_FILTER_LIST] = mac_list

    dut_bands = _dut_bands(_get("dut_list"), bands)
    if dut_bands:
        fields[ARNetworkField.BANDS] = dut_bands

    # Security only for the bands the network is actually bound to
    password, security = _parse_security(_get("security"), dut_bands)
    if password is not None:
        fields[ARNetworkField.PASSWORD] = password
    if security:
        fields[ARNetworkField.SECURITY] = security

    return fields


def translate(
    data: dict[str, Any], bands: list[ARWiFiBand]
) -> dict[ARNetworkType, list[dict[ARNetworkField, Any]]]:
    """Translate raw SDN data into networks grouped by type."""

    result: dict[ARNetworkType, list[dict[ARNetworkField, Any]]] = {}
    for name, prefix, apg_idx, sdn_enabled in _parse_sdn_rl(
        data.get("sdn_rl")
    ):
        network = _build_network(data, prefix, apg_idx, bands, sdn_enabled)
        net_type = ARNetworkType.from_value(name)
        result.setdefault(net_type, []).append(network)

    return result
