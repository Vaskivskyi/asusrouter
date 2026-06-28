"""Clients translation for AsusRouter."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from asusrouter.modules.clients.model import (
    ARClient,
    ARClientConnection,
    ARClientLink,
)
from asusrouter.modules.common.connection import ARConnectionType
from asusrouter.modules.common.device import ARDeviceType
from asusrouter.modules.common.internet import ARInternetMode
from asusrouter.modules.common.ip import ARIPMethod
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.wifi import ARWiFiAuth, ARWiFiBand, ARWiFiFrequency
from asusrouter.tools.converters import safe_time_from_delta
from asusrouter.tools.converters_v2.raw import (
    raw_to_bool,
    raw_to_int,
    raw_to_str,
)
from asusrouter.tools.identifiers import IpAddress, MacAddress
from asusrouter.tools.readers import read_units_data_rate
from asusrouter.tools.units import UnitOfDataRate

# Link rates come as binary Mibit/s; read them as bits/s
_read_mibps = read_units_data_rate(UnitOfDataRate.MEBIBIT_PER_SECOND)

# Raw hook keys that are not clients
_SKIP_KEYS = frozenset({"maclist", "ClientAPILevel"})

# `isWL` / `wireless` value -> frequency (0 = wired; 3 normalizes to 5G)
_WL_FREQUENCY: dict[int, ARWiFiFrequency] = {
    1: ARWiFiFrequency.FREQ_2G,
    2: ARWiFiFrequency.FREQ_5G,
    4: ARWiFiFrequency.FREQ_6G,
}

# Asus band tag, e.g. `5G1` / `6G` / `2G2`; the index is 1-based and a
# bare tag (`5G`) means the first band (`5G1`)
_BAND_TAG_RE = re.compile(r"^(\d)G(\d*)$", re.IGNORECASE)

# Main fronthaul SDN type - a client there is not a guest
_SDN_MAIN = "MAINFH"

# `isWL` value reported by some dualband firmwares for 5G
_ISWL_DUALBAND = 3


def _clean(entry: dict[str, Any]) -> dict[str, Any]:
    """Strip the firmware's trailing-space keys (e.g. `conn_ts `)."""

    return {(raw_to_str(key) or key): value for key, value in entry.items()}


def _rate(value: Any) -> float | None:
    """Convert a Mibit/s link rate to bits/s, or None when absent."""

    return _read_mibps(value) if raw_to_str(value) is not None else None


def _since_ts(value: Any) -> datetime | None:
    """Convert a unix connection timestamp to a datetime."""

    ts = raw_to_int(value)
    return datetime.fromtimestamp(ts, UTC) if ts else None


def _since_delta(value: Any) -> datetime | None:
    """Convert a `HH:MM:SS` connection duration to a datetime."""

    text = raw_to_str(value)
    return safe_time_from_delta(text) if text else None


def _band_frequency(band: ARWiFiBand) -> ARWiFiFrequency:
    """Map a specific band to its frequency."""

    return ARWiFiFrequency.from_value(band.value[:2])


def _tag_to_band(tag: str) -> ARWiFiBand | None:
    """Resolve an Asus band tag (`5G1`, `6G`, ...) to a band, or None."""

    match = _BAND_TAG_RE.match(tag)
    if match is None:
        return None
    freq, index = match.group(1), match.group(2) or "1"
    band = ARWiFiBand.from_value(f"{freq}g{index}")
    return band if band is not ARWiFiBand.UNKNOWN else None


def _is_mesh_node(entry: dict[str, Any]) -> bool:
    """Whether the entry is an AiMesh node rather than a client."""

    return raw_to_bool(entry.get("amesh_isRe")) is True


def _name(*entries: dict[str, Any]) -> str | None:
    """Pick a display name: nickName, then name, across entries."""

    for key in ("nickName", "name"):
        for entry in entries:
            value = raw_to_str(entry.get(key))
            if value:
                return value
    return None


def _mlo_live_links(mlo_links: dict[str, Any]) -> list[ARClientLink]:
    """Build MLO links from the live per-link metrics."""

    links = []
    for radio, info in mlo_links.items():
        if not isinstance(info, dict):
            continue
        band = _tag_to_band(radio)
        links.append(
            ARClientLink(
                frequency=(
                    _band_frequency(band) if band else ARWiFiFrequency.UNKNOWN
                ),
                band=band,
                mac=MacAddress.from_value_safe(info.get("mac")),
                rssi=raw_to_int(info.get("rssi")),
                rx_speed=_rate(info.get("rx")),
                tx_speed=_rate(info.get("tx")),
                connected_since=_since_delta(info.get("conn_time")),
            )
        )
    return links


def _mlo_db_links(db: dict[str, Any]) -> list[ARClientLink]:
    """Build MLO links from the database per-band MAC fields."""

    links = []
    for field, value in db.items():
        if field == "mlo_all_mac" or not (
            field.startswith("mlo_") and field.endswith("_mac")
        ):
            continue
        band = _tag_to_band(field[len("mlo_") : -len("_mac")])
        mac = MacAddress.from_value_safe(value)
        if band is not None and mac is not None:
            links.append(
                ARClientLink(
                    frequency=_band_frequency(band), band=band, mac=mac
                )
            )
    return links


def _single_link(
    live: dict[str, Any], db: dict[str, Any]
) -> list[ARClientLink]:
    """Build the single wireless link, of which only frequency is known."""

    unit = raw_to_int(live.get("isWL") or db.get("wireless"))
    if unit == _ISWL_DUALBAND:
        unit = 2
    frequency = _WL_FREQUENCY.get(unit) if unit is not None else None
    if frequency is None:
        return []
    return [
        ARClientLink(
            frequency=frequency,
            rssi=raw_to_int(live.get("rssi")),
            rx_speed=_rate(live.get("curRx")),
            tx_speed=_rate(live.get("curTx")),
        )
    ]


def _build_links(
    live: dict[str, Any], db: dict[str, Any]
) -> tuple[bool, list[ARClientLink]]:
    """Build wireless links, modelling MLO as one link per radio."""

    mlo = raw_to_bool(live.get("mlo")) or raw_to_bool(db.get("mlo")) or False
    mlo_links = live.get("mlo_links")

    if mlo and isinstance(mlo_links, dict) and mlo_links:
        return True, _mlo_live_links(mlo_links)
    if mlo and (links := _mlo_db_links(db)):
        return True, links
    return False, _single_link(live, db)


def _build_connection(
    live: dict[str, Any], db: dict[str, Any], router: MacAddress | None
) -> ARClientConnection:
    """Build the current connection from the live (and db) entry."""

    wired = raw_to_int(live.get("isWL") or db.get("wireless")) == 0
    mlo, links = (False, []) if wired else _build_links(live, db)

    sdn_type = raw_to_str(live.get("sdn_type"))
    guest = bool(raw_to_str(live.get("isGN"))) and sdn_type != _SDN_MAIN

    # wlAuth / ipMethod arrive upper/mixed case; the enums are lowercase
    auth = raw_to_str(live.get("wlAuth"))
    ip_method = raw_to_str(live.get("ipMethod"))

    return ARClientConnection(
        type=(ARConnectionType.WIRED if wired else ARConnectionType.WIRELESS),
        ip=IpAddress.from_value_safe(live.get("ip")),
        ip_method=ARIPMethod.from_value(
            ip_method.lower() if ip_method else None
        ),
        internet_access=raw_to_bool(live.get("internetState")),
        node=MacAddress.from_value_safe(live.get("amesh_papMac")) or router,
        ssid=raw_to_str(live.get("ssid")),
        security=ARWiFiAuth.from_value(auth.lower()) if auth else None,
        guest=guest,
        sdn=sdn_type,
        mlo=mlo,
        connected_since=_since_ts(db.get("conn_ts")),
        links=links,
    )


def _build_client(
    mac: MacAddress,
    live: dict[str, Any],
    db: dict[str, Any],
    router: MacAddress | None,
) -> ARClient:
    """Build a single client from its live and database entries."""

    online = raw_to_bool(live.get("isOnline")) is True

    client = ARClient(
        mac=mac,
        online=online,
        name=_name(live, db),
        vendor=raw_to_str(live.get("vendor")) or raw_to_str(db.get("vendor")),
        vendor_class=raw_to_str(db.get("vendorclass")),
        device_type=ARDeviceType.from_value(
            live.get("type") or db.get("type")
        ),
        os_type=raw_to_int(db.get("os_type")),
        bound_node=MacAddress.from_value_safe(
            live.get("amesh_bind_mac") or db.get("amesh_bind_mac")
        ),
        internet_mode=ARInternetMode.from_value(live.get("internetMode")),
    )
    if online:
        client.connection = _build_connection(live, db, router)
    return client


def _entries(
    raw: dict[str, Any], key: str
) -> dict[MacAddress, dict[str, Any]]:
    """Extract the per-MAC entries of one hook, MAC-keyed and cleaned."""

    section = raw.get(key)
    result: dict[MacAddress, dict[str, Any]] = {}
    if not isinstance(section, dict):
        return result
    for mac_raw, entry in section.items():
        if mac_raw in _SKIP_KEYS or not isinstance(entry, dict):
            continue
        mac = MacAddress.from_value_safe(mac_raw)
        if mac is not None:
            result[mac] = _clean(entry)
    return result


def build_clients(
    raw: Any, identity: ARDeviceIdentity | None
) -> dict[MacAddress, ARClient]:
    """Build all clients from the two hook payloads, merged.

    `get_clientlist` is the primary (live) source; the database adds
    identity-only clients not present there. AiMesh nodes and the router
    itself are excluded.
    """

    if not isinstance(raw, dict):
        return {}

    router = identity.mac if identity is not None else None
    live = _entries(raw, "get_clientlist")
    db = _entries(raw, "get_clientlist_from_json_database")

    clients: dict[MacAddress, ARClient] = {}
    for mac, entry in live.items():
        if _is_mesh_node(entry) or mac == router:
            continue
        clients[mac] = _build_client(mac, entry, db.get(mac, {}), router)
    for mac, entry in db.items():
        if mac in clients or _is_mesh_node(entry) or mac == router:
            continue
        clients[mac] = _build_client(mac, {}, entry, router)
    return clients
