"""SDN backend for the network module.

Reads the Software-Defined Network profiles (main + guest/IoT) on modern
firmware and builds the per-type network profiles.
"""

from __future__ import annotations

from typing import Any

from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import hook_request, hook_value
from asusrouter.modules.network.common import (
    bandwidth_limit,
    decode,
    mac_filter_mode,
    read_mac_list,
)
from asusrouter.modules.network.enums import (
    ARNetworkBackend,
    ARNetworkField,
    ARNetworkSchedule,
    ARNetworkType,
)
from asusrouter.modules.network.handle import ARNetworkHandle
from asusrouter.modules.nvram import (
    ARNvramIndexSource,
    ARNvramIndexType,
    ARNvramType,
)
from asusrouter.modules.wifi import ARWiFiAuthMode, ARWiFiBand
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import Password, Ssid
from asusrouter.tools.types import ARCallbackType

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

# `bw_limit` row columns (`<enabled>up>down`)
_BW_ENABLED_COL = 0
_BW_UPLOAD_COL = 1
_BW_DOWNLOAD_COL = 2

# Per-profile AP-group keys we read and parse
_AP_KEYS = (
    ARNvramIndexType.AP_ENABLE,
    ARNvramIndexType.AP_SSID,
    ARNvramIndexType.AP_HIDE_SSID,
    ARNvramIndexType.AP_SECURITY,
    ARNvramIndexType.AP_AP_ISOLATE,
    ARNvramIndexType.AP_MACMODE,
    ARNvramIndexType.AP_MLO,
    ARNvramIndexType.AP_MACLIST,
    ARNvramIndexType.AP_DUT_LIST,
    ARNvramIndexType.AP_11BE,
    ARNvramIndexType.AP_TIMESCHED,
    ARNvramIndexType.AP_SCHED,
    ARNvramIndexType.AP_EXPIRETIME,
    ARNvramIndexType.AP_BW_LIMIT,
)


def _ap_index(prefix: str | None, idx: int | None) -> str:
    """Build the AP-group template index (`g1` for `apg1`)."""

    return f"{(prefix or '').removeprefix('ap')}{idx}"


# WiFi band bitmask -> band (`wifi_band_options_cb`): a band matches any of
# its bits (single vs dual-band variants)
_BAND_BITS: dict[ARWiFiBand, int] = {
    ARWiFiBand.BAND_2G1: 1,
    ARWiFiBand.BAND_5G1: 2 | 4,
    ARWiFiBand.BAND_5G2: 8,
    ARWiFiBand.BAND_6G1: 16 | 32,
    ARWiFiBand.BAND_6G2: 64,
}


def _rows(raw: Any) -> list[list[str]]:
    """Decode a char-encoded rule-list into rows of `>`-separated columns."""

    decoded = decode(raw)
    return [chunk.split(">") for chunk in decoded.split("<") if chunk != ""]


def _parse_sdn_rl(raw: Any) -> list[tuple[str, str, int, int, bool]]:
    """Parse `sdn_rl` into `(name, prefix, apg_idx, sdn_idx, enabled)`."""

    profiles: list[tuple[str, str, int, int, bool]] = []
    for cols in _rows(raw):
        if len(cols) <= _COL_APG_IDX or cols[_COL_IDX] == "0":
            continue
        name = cols[_COL_NAME]
        apg_idx = raw_to_int(cols[_COL_APG_IDX])
        sdn_idx = raw_to_int(cols[_COL_IDX])
        if apg_idx is None or sdn_idx is None:
            continue
        prefix = "apm" if name in _MAIN_NAMES else "apg"
        enabled = raw_to_bool(cols[_COL_ENABLE]) or False
        profiles.append((name, prefix, apg_idx, sdn_idx, enabled))
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
        for cols in _rows(raw)
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
    for cols in _rows(raw):
        if len(cols) >= _DUT_COLS:
            union |= raw_to_int(cols[1]) or 0

    return [band for band in bands if _BAND_BITS.get(band, 0) & union]


def _bandwidth(raw: Any) -> dict[ARNetworkField, Any]:
    """Decode `bw_limit` (`<enabled>up>down`, Kib/s) into rate fields."""

    rows = _rows(raw)
    if not rows:
        return {}

    row = rows[0]
    enabled = row[_BW_ENABLED_COL] if len(row) > _BW_ENABLED_COL else None
    upload = row[_BW_UPLOAD_COL] if len(row) > _BW_UPLOAD_COL else None
    download = row[_BW_DOWNLOAD_COL] if len(row) > _BW_DOWNLOAD_COL else None
    return bandwidth_limit(enabled, download, upload)


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


def _ap_request(profiles: list[tuple[str, str, int, int, bool]]) -> str:
    """Build the appGet request for the referenced AP groups."""

    items = [
        ARNvramIndexSource(kind, _ap_index(prefix, apg_idx))
        for _, prefix, apg_idx, _, _ in profiles
        for kind in _AP_KEYS
    ]
    return hook_request(*items)


async def fetch_sdn_rl(callback: ARCallbackType) -> Any:
    """Fetch the raw `sdn_rl` rule list, or None if unavailable."""

    request = hook_request(ARNvramType.SDN_RL)
    data = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)
    return hook_value(data, ARNvramType.SDN_RL)


async def fetch(callback: ARCallbackType) -> Any:
    """Fetch `sdn_rl`, then the AP groups it references."""

    sdn_rl = await fetch_sdn_rl(callback)
    if sdn_rl is None:
        return None

    profiles = _parse_sdn_rl(sdn_rl)
    if not profiles:
        return {ARNvramType.SDN_RL.value: sdn_rl}

    second = await callback(
        endpoint=AREndpoint.FETCH_DATA, request=_ap_request(profiles)
    )
    ap_data = second if isinstance(second, dict) else {}
    return {ARNvramType.SDN_RL.value: sdn_rl, **ap_data}


def _build_network(
    data: dict[str, Any],
    handle: ARNetworkHandle,
    bands: list[ARWiFiBand],
    sdn_enabled: bool,
) -> dict[ARNetworkField, Any]:
    """Build the network profile dict for one AP group."""

    index = _ap_index(handle.ap_prefix, handle.ap_idx)

    def _get(kind: ARNvramIndexType) -> Any:
        return data.get(kind.key(index))

    # A network is on only when both the SDN profile and its AP group are on
    enabled = sdn_enabled and (
        raw_to_bool(_get(ARNvramIndexType.AP_ENABLE)) or False
    )

    fields: dict[ARNetworkField, Any] = {
        ARNetworkField.ENABLED: enabled,
        ARNetworkField.HANDLE: handle,
        ARNetworkField.HIDDEN: (
            raw_to_bool(_get(ARNvramIndexType.AP_HIDE_SSID)) or False
        ),
        ARNetworkField.WIFI7: (
            raw_to_bool(_get(ARNvramIndexType.AP_11BE)) or False
        ),
        ARNetworkField.AP_ISOLATE: (
            raw_to_bool(_get(ARNvramIndexType.AP_AP_ISOLATE)) or False
        ),
    }

    ssid = Ssid.from_value_safe(_get(ARNvramIndexType.AP_SSID))
    if ssid is not None:
        fields[ARNetworkField.SSID] = ssid

    mlo = raw_to_int(_get(ARNvramIndexType.AP_MLO))
    if mlo is not None:
        fields[ARNetworkField.MLO] = mlo

    fields.update(
        _schedule(
            _get(ARNvramIndexType.AP_TIMESCHED),
            _get(ARNvramIndexType.AP_SCHED),
            _get(ARNvramIndexType.AP_EXPIRETIME),
        )
    )
    fields.update(_bandwidth(_get(ARNvramIndexType.AP_BW_LIMIT)))

    mode = mac_filter_mode(_get(ARNvramIndexType.AP_MACMODE))
    if mode is not None:
        fields[ARNetworkField.MAC_FILTER_MODE] = mode
    mac_list = read_mac_list(_get(ARNvramIndexType.AP_MACLIST))
    if mac_list:
        fields[ARNetworkField.MAC_FILTER_LIST] = mac_list

    dut_bands = _dut_bands(_get(ARNvramIndexType.AP_DUT_LIST), bands)
    if dut_bands:
        fields[ARNetworkField.BANDS] = dut_bands

    # Security only for the bands the network is actually bound to
    password, security = _parse_security(
        _get(ARNvramIndexType.AP_SECURITY), dut_bands
    )
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
    for name, prefix, apg_idx, sdn_idx, sdn_enabled in _parse_sdn_rl(
        data.get(ARNvramType.SDN_RL.value)
    ):
        handle = ARNetworkHandle(
            backend=ARNetworkBackend.SDN,
            sdn_idx=sdn_idx,
            ap_prefix=prefix,
            ap_idx=apg_idx,
        )
        network = _build_network(data, handle, bands, sdn_enabled)
        net_type = ARNetworkType.from_value(name)
        result.setdefault(net_type, []).append(network)

    return result


def build_toggle_payload(
    raw_sdn_rl: Any, handle: ARNetworkHandle, state: bool
) -> tuple[str, dict[str, Any]]:
    """Build the `(rc_service, arguments)` to enable/disable an SDN profile."""

    rows = _rows(raw_sdn_rl)
    for cols in rows:
        if len(cols) > _COL_ENABLE and raw_to_int(cols[_COL_IDX]) == (
            handle.sdn_idx
        ):
            cols[_COL_ENABLE] = "1" if state else "0"
            break

    new_sdn_rl = "".join("<" + ">".join(cols) for cols in rows)
    rc_service = f"restart_wireless;restart_sdn {handle.sdn_idx};"
    ap_enable = ARNvramIndexType.AP_ENABLE.key(
        _ap_index(handle.ap_prefix, handle.ap_idx)
    )
    arguments: dict[str, Any] = {
        ARNvramType.SDN_RL.value: new_sdn_rl,
        ap_enable: int(state),
    }
    return rc_service, arguments
