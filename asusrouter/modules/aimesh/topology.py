"""AiMesh Topology module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from asusrouter.modules.aimesh.capability import (
    is_fully_decoded,
    translate_features,
)
from asusrouter.modules.aimesh.enums import (
    ARAiMeshFeature,
    ARAiMeshMedium,
    ARAiMeshRole,
)
from asusrouter.modules.common.region import ARRegion, translate_region
from asusrouter.modules.firmware import ARFirmware
from asusrouter.modules.ports.enums import ARPortSpeed
from asusrouter.modules.ports.legacy import read_ethernet_port_speed
from asusrouter.modules.wifi import ARWiFiBand
from asusrouter.tools.converters.raw import raw_to_bool, raw_to_int
from asusrouter.tools.identifiers import IpAddress, MacAddress

# === Radio ===

# AP field suffix -> wifi band
_AP_BANDS: dict[str, ARWiFiBand] = {
    "2g": ARWiFiBand.BAND_2G1,
    "5g": ARWiFiBand.BAND_5G1,
    "5g1": ARWiFiBand.BAND_5G2,
    "6g": ARWiFiBand.BAND_6G1,
    "6g1": ARWiFiBand.BAND_6G2,
}

# wifi band -> sta field suffix (one station per frequency)
_BAND_STA: dict[ARWiFiBand, str] = {
    ARWiFiBand.BAND_2G1: "2g",
    ARWiFiBand.BAND_2G2: "2g",
    ARWiFiBand.BAND_5G1: "5g",
    ARWiFiBand.BAND_5G2: "5g",
    ARWiFiBand.BAND_6G1: "6g",
    ARWiFiBand.BAND_6G2: "6g",
}

# band_info index -> ap field suffix
_BAND_INFO_SUFFIX: dict[str, str] = {
    "0": "2g",
    "1": "5g",
    "2": "5g",
    "3": "5g1",
    "4": "6g",
    "5": "6g",
    "6": "6g1",
}


@dataclass
class ARAiMeshRadio:
    """A fronthaul radio of an AiMesh node."""

    band: ARWiFiBand
    mac_ap: MacAddress | None = None
    mac_fh: MacAddress | None = None
    mac_iot: MacAddress | None = None
    mac_sta: MacAddress | None = None
    ssid: str | None = None
    ssid_fh: str | None = None
    unit: int | None = None
    state: bool | None = None
    dwb: bool = False


def _translate_band_units(raw: dict[str, Any]) -> dict[str, int]:
    """Map AP field suffix -> wl unit from `band_info`."""

    band_info = raw.get("band_info")
    if not isinstance(band_info, dict):
        return {}

    units: dict[str, int] = {}
    for index, info in band_info.items():
        suffix = _BAND_INFO_SUFFIX.get(str(index))
        unit = raw_to_int(info.get("unit")) if isinstance(info, dict) else None
        if suffix is not None and unit is not None:
            units[suffix] = unit
    return units


def _translate_radios(raw: dict[str, Any]) -> dict[ARWiFiBand, ARAiMeshRadio]:
    """Build the per-band fronthaul radios of a node."""

    units = _translate_band_units(raw)
    config = raw.get("config") or {}
    wireless = config.get("wireless") if isinstance(config, dict) else {}
    wireless = wireless if isinstance(wireless, dict) else {}
    dwb_mac = MacAddress.from_value_safe(raw.get("apdwb"))

    radios: dict[ARWiFiBand, ARAiMeshRadio] = {}
    for suffix, band in _AP_BANDS.items():
        mac_ap = MacAddress.from_value_safe(raw.get(f"ap{suffix}"))
        mac_fh = MacAddress.from_value_safe(raw.get(f"ap{suffix}_fh"))
        mac_iot = MacAddress.from_value_safe(raw.get(f"ap{suffix}_iot_fh"))
        unit = units.get(suffix)
        # A radio is present if `band_info` lists it (even with radios off
        # and empty MACs) or any MAC is populated
        if unit is None and mac_ap is None and mac_fh is None:
            continue
        state = None
        if unit is not None and f"wl{unit}_radio" in wireless:
            state = wireless[f"wl{unit}_radio"] == "1"
        radios[band] = ARAiMeshRadio(
            band=band,
            mac_ap=mac_ap,
            mac_fh=mac_fh,
            mac_iot=mac_iot,
            mac_sta=MacAddress.from_value_safe(
                raw.get(f"sta{_BAND_STA[band]}")
            ),
            ssid=raw.get(f"ap{suffix}_ssid") or None,
            ssid_fh=raw.get(f"ap{suffix}_ssid_fh") or None,
            unit=unit,
            state=state,
            dwb=dwb_mac is not None and dwb_mac == mac_ap,
        )

    return radios


# === Virtual interface (VIF) ===


@dataclass
class ARAiMeshVif:
    """A virtual interface (VIF) slot on an AiMesh radio."""

    index: int
    # TODO: decode the type bitmask into purposes; only `free` (type == 1)
    # is currently confirmed
    type: int
    free: bool = False


def _parse_vif_prefix(prefix: str) -> tuple[int | None, int | None]:
    """Parse a vif prefix `wl{unit}.{index}` into (unit, index)."""

    unit_str, _, index_str = prefix.removeprefix("wl").partition(".")
    return raw_to_int(unit_str), raw_to_int(index_str)


def _translate_vifs(
    raw: dict[str, Any],
) -> dict[ARWiFiBand, list[ARAiMeshVif]]:
    """Build the per-band virtual interfaces from capability 26."""

    capability = raw.get("capability")
    cap = capability.get("26") if isinstance(capability, dict) else None
    wifi_band = cap.get("wifi_band") if isinstance(cap, dict) else None
    if not isinstance(wifi_band, dict):
        return {}

    units = _translate_band_units(raw)
    unit_to_band = {unit: _AP_BANDS[suffix] for suffix, unit in units.items()}

    result: dict[ARWiFiBand, list[ARAiMeshVif]] = {}
    for band_entry in wifi_band.values():
        vifs = band_entry.get("vif") if isinstance(band_entry, dict) else None
        if not isinstance(vifs, dict):
            continue
        for prefix, vif in vifs.items():
            if not isinstance(vif, dict):
                continue
            unit, index = _parse_vif_prefix(prefix)
            kind = raw_to_int(vif.get("type"))
            if index is None or kind is None:
                continue
            band = (
                unit_to_band.get(unit, ARWiFiBand.UNKNOWN)
                if unit is not None
                else ARWiFiBand.UNKNOWN
            )
            result.setdefault(band, []).append(
                ARAiMeshVif(index=index, type=kind, free=kind == 1)
            )

    return result


# === Port ===


@dataclass
class ARAiMeshPort:
    """A wired port of an AiMesh node."""

    max_rate: ARPortSpeed
    label: str | None = None
    is_wan: bool = False
    index: int | None = None


def _translate_ports(raw: dict[str, Any]) -> list[ARAiMeshPort]:
    """Build the wired ports of a node from capability 27/28."""

    capability = raw.get("capability")
    if not isinstance(capability, dict):
        return []

    ports: list[ARAiMeshPort] = []
    for cap_key, sub_key, is_wan in (
        ("27", "lan_port", False),
        ("28", "wan_port", True),
    ):
        section = capability.get(cap_key)
        group = section.get(sub_key) if isinstance(section, dict) else None
        if not isinstance(group, dict):
            continue
        for info in group.values():
            if not isinstance(info, dict):
                continue
            ports.append(
                ARAiMeshPort(
                    label=info.get("label_name") or None,
                    is_wan=is_wan,
                    max_rate=ARPortSpeed.from_value(info.get("max_rate")),
                    index=raw_to_int(info.get("index")),
                )
            )
    return ports


# === Capability passthrough ===

# Capability keys already decoded into typed fields, stripped from the
# raw `capability` passthrough so data is not duplicated
_CONSUMED_CAPABILITY: frozenset[str] = frozenset({"26", "27", "28"})


def _remaining_capability(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Return the raw capability without the keys we already decoded."""

    capability = raw.get("capability")
    if not isinstance(capability, dict):
        return None
    remaining = {
        key: value
        for key, value in capability.items()
        if key not in _CONSUMED_CAPABILITY and not is_fully_decoded(key, value)
    }
    return remaining or None


# === Backhaul ===

# pap field suffix -> (band, ap fields to match a parent on, sta field)
_BACKHAUL_BANDS: dict[str, tuple[ARWiFiBand, tuple[str, ...], str]] = {
    "2g": (ARWiFiBand.BAND_2G1, ("ap2g",), "sta2g"),
    "5g": (ARWiFiBand.BAND_5G1, ("ap5g", "ap5g1"), "sta5g"),
    "6g": (ARWiFiBand.BAND_6G1, ("ap6g", "ap6g1"), "sta6g"),
}

# Wired re_path -> backhaul port sequence index
_ETH_RE_PATH_PORT: dict[int, int] = {1: 1, 16: 2, 32: 3, 64: 4}
_WIRED_RE_PATHS = frozenset(_ETH_RE_PATH_PORT)

# re_path -> wireless backhaul band suffix
_WIRELESS_RE_PATHS: dict[int, str] = {
    2: "2g",
    4: "5g",
    6: "5g",
    8: "5g",
    10: "5g",
    128: "6g",
}
_MLO_RE_PATH = 512
# On tri-band routers re_path 8 is the secondary 5 GHz (5G-2)
_RE_PATH_5G_SECONDARY = 8
_TRI_BAND = "3"


@dataclass
class ARAiMeshBackhaul:
    """An uplink of an AiMesh node to its parent."""

    medium: ARAiMeshMedium
    mac_parent: MacAddress | None = None
    ssid_parent: str | None = None
    band: ARWiFiBand | None = None
    mac_sta: MacAddress | None = None
    rssi: int | None = None
    port: int | None = None
    link_rate: ARPortSpeed = ARPortSpeed.UNKNOWN


def _parent_wired(
    raw: dict[str, Any], nodes: list[dict[str, Any]]
) -> MacAddress | None:
    """Find the parent whose `wired_mac` lists this node."""

    mac = raw.get("mac")
    for other in nodes:
        wired = other.get("wired_mac")
        if isinstance(wired, list) and mac in wired:
            return MacAddress.from_value_safe(other.get("mac"))
    return None


def _parent_wireless(
    raw: dict[str, Any],
    suffix: str,
    ap_fields: tuple[str, ...],
    nodes: list[dict[str, Any]],
) -> MacAddress | None:
    """Find the parent whose AP BSSID matches this node's `pap`."""

    pap = raw.get(f"pap{suffix}")
    if not pap:
        return None
    for other in nodes:
        if any(other.get(ap) == pap for ap in ap_fields):
            return MacAddress.from_value_safe(other.get("mac"))
    return None


def _wired_link_rate(raw: dict[str, Any]) -> ARPortSpeed:
    """Read the wired uplink link rate from `wired_port`."""

    wired_port = raw.get("wired_port")
    ports = (
        wired_port.get("wan_port") if isinstance(wired_port, dict) else None
    )
    if not isinstance(ports, dict):
        return ARPortSpeed.UNKNOWN
    for info in ports.values():
        code = info.get("link_rate") if isinstance(info, dict) else None
        if code:
            return read_ethernet_port_speed(code)
    return ARPortSpeed.UNKNOWN


def _translate_backhaul(
    raw: dict[str, Any], re_path: int, nodes: list[dict[str, Any]]
) -> ARAiMeshBackhaul | None:
    """Resolve the single backhaul uplink of a node."""

    if re_path in _WIRED_RE_PATHS:
        medium = ARAiMeshMedium.WIRED
        if raw.get("plc_status"):
            medium = ARAiMeshMedium.PLC
        elif raw.get("moca_status"):
            medium = ARAiMeshMedium.MOCA
        return ARAiMeshBackhaul(
            medium=medium,
            mac_parent=_parent_wired(raw, nodes),
            mac_sta=MacAddress.from_value_safe(raw.get("mac")),
            port=_ETH_RE_PATH_PORT.get(re_path),
            link_rate=_wired_link_rate(raw),
        )

    if re_path == _MLO_RE_PATH:
        mlo = raw.get("mlo_status") or {}
        return ARAiMeshBackhaul(
            medium=ARAiMeshMedium.MLO,
            mac_parent=MacAddress.from_value_safe(raw.get("papmlo")),
            mac_sta=MacAddress.from_value_safe(
                mlo.get("msta") if isinstance(mlo, dict) else None
            ),
        )

    suffix = _WIRELESS_RE_PATHS.get(re_path)
    if suffix is None:
        return None

    band, ap_fields, sta_field = _BACKHAUL_BANDS[suffix]
    # Tri-band 5 GHz second radio is the 5G-2 backhaul band
    if (
        suffix == "5g"
        and re_path == _RE_PATH_5G_SECONDARY
        and str(raw.get("band_num")) == _TRI_BAND
    ):
        band = ARWiFiBand.BAND_5G2
    return ARAiMeshBackhaul(
        medium=ARAiMeshMedium.WIRELESS,
        mac_parent=_parent_wireless(raw, suffix, ap_fields, nodes),
        ssid_parent=raw.get(f"pap{suffix}_ssid") or None,
        band=band,
        mac_sta=MacAddress.from_value_safe(raw.get(sta_field)),
        rssi=raw_to_int(raw.get(f"rssi{suffix}")),
    )


# === Node ===


@dataclass
class ARAiMeshNode:
    """An AiMesh device description."""

    mac: MacAddress
    alias: str | MacAddress | None = None
    model: str | None = None
    model_original: str | None = None
    model_display: str | None = None
    icon: str | None = None
    ip: IpAddress | None = None
    region: ARRegion = ARRegion.UNKNOWN
    region_area: int | None = None
    firmware: ARFirmware = field(default_factory=ARFirmware)
    firmware_available: ARFirmware = field(default_factory=ARFirmware)
    firmware_update: bool = False
    online: bool = False
    level: int = 0
    role: ARAiMeshRole = ARAiMeshRole.UNKNOWN
    backhaul: ARAiMeshBackhaul | None = None
    preferred_parent: MacAddress | None = None
    radios: dict[ARWiFiBand, ARAiMeshRadio] = field(default_factory=dict)
    virtual_if: dict[ARWiFiBand, list[ARAiMeshVif]] = field(
        default_factory=dict
    )
    features: frozenset[ARAiMeshFeature] = frozenset()
    dwb: ARWiFiBand | None = None
    ports: list[ARAiMeshPort] = field(default_factory=list)
    lacp: bool | None = None
    led: bool | None = None
    # Kept raw for now (option b) - decoded incrementally later
    plc_status: dict[str, Any] | None = None
    moca_status: dict[str, Any] | None = None
    mlo_status: dict[str, Any] | None = None
    capability: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


def _config_flag(
    config: dict[str, Any], section: str, key: str
) -> bool | None:
    """Read a boolean flag from a config section."""

    sub = config.get(section)
    if not isinstance(sub, dict) or key not in sub:
        return None
    return raw_to_bool(sub[key])


def _preferred_parent(config: dict[str, Any]) -> MacAddress | None:
    """Read the configured preferred parent BSSID (`<` prefix stripped)."""

    prefer = config.get("prefer_ap")
    bssid = (
        prefer.get("amas_wlc_target_bssid")
        if isinstance(prefer, dict)
        else None
    )
    if not isinstance(bssid, str):
        return None
    return MacAddress.from_value_safe(bssid.lstrip("<"))


def _dwb_band(
    raw: dict[str, Any], radios: dict[ARWiFiBand, ARAiMeshRadio]
) -> ARWiFiBand | None:
    """Resolve the dedicated wireless backhaul band from `dwb_band`."""

    unit = raw_to_int(raw.get("dwb_band"))
    if unit is None or unit < 0:
        return None
    return next((b for b, radio in radios.items() if radio.unit == unit), None)


def _firmware_update(current: ARFirmware, available: ARFirmware) -> bool:
    """Whether a newer firmware is available for the node."""

    if current.major is None or available.major is None:
        return False
    return current < available


def _raw_dict(value: Any) -> dict[str, Any] | None:
    """Return the value as-is if it is a dict, else None."""

    return value if isinstance(value, dict) else None


def _translate_node(
    raw: dict[str, Any], nodes: list[dict[str, Any]]
) -> ARAiMeshNode | None:
    """Build a single node description."""

    mac = MacAddress.from_value_safe(raw.get("mac"))
    if mac is None:
        return None

    re_path = raw_to_int(raw.get("re_path")) or 0
    role = ARAiMeshRole.ROUTER if re_path == 0 else ARAiMeshRole.NODE
    backhaul = (
        None if re_path == 0 else _translate_backhaul(raw, re_path, nodes)
    )

    # An alias that is a MAC is wrapped so it can be masked when logged
    alias: str | MacAddress | None = raw.get("alias") or None
    if alias is not None:
        alias = MacAddress.from_value_safe(alias) or alias

    radios = _translate_radios(raw)
    raw_config = raw.get("config")
    config: dict[str, Any] = raw_config if isinstance(raw_config, dict) else {}
    region, region_area = translate_region(raw.get("tcode"))
    firmware = ARFirmware.from_string(raw.get("fwver"))
    firmware_available = ARFirmware.from_string(raw.get("newfwver"))

    return ARAiMeshNode(
        mac=mac,
        alias=alias,
        model=raw.get("product_id") or None,
        model_original=raw.get("model_name") or None,
        model_display=raw.get("ui_model_name") or None,
        icon=raw.get("icon_model_name") or None,
        ip=IpAddress.from_value_safe(raw.get("ip")),
        region=region,
        region_area=region_area,
        firmware=firmware,
        firmware_available=firmware_available,
        firmware_update=_firmware_update(firmware, firmware_available),
        online=raw.get("online") == "1",
        level=raw_to_int(raw.get("level")) or 0,
        role=role,
        backhaul=backhaul,
        preferred_parent=_preferred_parent(config),
        radios=radios,
        virtual_if=_translate_vifs(raw),
        features=translate_features(raw.get("capability")),
        dwb=_dwb_band(raw, radios),
        ports=_translate_ports(raw),
        lacp=_config_flag(config, "link_aggregation", "lacp_enabled"),
        led=_config_flag(config, "ctrl_led", "led_val"),
        plc_status=_raw_dict(raw.get("plc_status")),
        moca_status=_raw_dict(raw.get("moca_status")),
        mlo_status=_raw_dict(raw.get("mlo_status")),
        capability=_remaining_capability(raw),
        config=config or None,
    )


# === Onboarding status ===


@dataclass
class ARAiMeshOnboardingStatus:
    """AiMesh onboarding process state (`get_onboardingstatus`)."""

    ready: bool = False
    status: int | None = None
    stage: int | None = None
    result: int | None = None
    fail_result: int | None = None
    count: int | None = None
    re_count: int | None = None
    re_maxnum: int | None = None
    wifi_quality: int | None = None
    rssi: int | None = None
    model: str | None = None


def translate_onboarding_status(raw: Any) -> ARAiMeshOnboardingStatus:
    """Build the onboarding status from `get_onboardingstatus`."""

    if not isinstance(raw, dict):
        return ARAiMeshOnboardingStatus()

    return ARAiMeshOnboardingStatus(
        ready=raw.get("cfg_ready") == "1",
        status=raw_to_int(raw.get("cfg_obstatus")),
        stage=raw_to_int(raw.get("cfg_obstage")),
        result=raw_to_int(raw.get("cfg_obresult")),
        fail_result=raw_to_int(raw.get("cfg_obfailresult")),
        count=raw_to_int(raw.get("cfg_obcount")),
        re_count=raw_to_int(raw.get("cfg_recount")),
        re_maxnum=raw_to_int(raw.get("cfg_re_maxnum")),
        wifi_quality=raw_to_int(raw.get("cfg_wifi_quality")),
        rssi=raw_to_int(raw.get("cfg_obrssi")),
        model=raw.get("cfg_ui_obmodel") or raw.get("cfg_obmodel") or None,
    )


# === Topology ===


@dataclass
class ARAiMeshTopology:
    """A graph of AiMesh nodes with reconstruction helpers."""

    nodes: dict[MacAddress, ARAiMeshNode] = field(default_factory=dict)
    status: ARAiMeshOnboardingStatus = field(
        default_factory=ARAiMeshOnboardingStatus
    )
    onboarding: dict[str, Any] | None = None

    def get(self, mac: Any) -> ARAiMeshNode | None:
        """Get a node by MAC."""

        key = MacAddress.from_value_safe(mac)
        return self.nodes.get(key) if key is not None else None

    def macs(self) -> list[MacAddress]:
        """All node MACs (for `all nodes` discovery)."""

        return list(self.nodes)

    def root(self) -> ARAiMeshNode | None:
        """Return the router / CAP node, if present."""

        return next(
            (n for n in self.nodes.values() if n.role is ARAiMeshRole.ROUTER),
            None,
        )

    def parent(self, mac: Any) -> ARAiMeshNode | None:
        """Return the direct parent of a node."""

        node = self.get(mac)
        if node is None or node.backhaul is None:
            return None
        parent = node.backhaul.mac_parent
        return self.nodes.get(parent) if parent is not None else None

    def children(self, mac: Any) -> list[ARAiMeshNode]:
        """Return the direct children of a node."""

        target = MacAddress.from_value_safe(mac)
        if target is None:
            return []
        return [
            n
            for n in self.nodes.values()
            if n.backhaul is not None and n.backhaul.mac_parent == target
        ]

    def descendants(self, mac: Any) -> list[ARAiMeshNode]:
        """All nodes below a node (every generation)."""

        result: list[ARAiMeshNode] = []
        queue = self.children(mac)
        while queue:
            node = queue.pop(0)
            result.append(node)
            queue.extend(self.children(node.mac))
        return result

    def path_to_root(self, mac: Any) -> list[ARAiMeshNode]:
        """Nodes from the given node up to the root (inclusive)."""

        path: list[ARAiMeshNode] = []
        node = self.get(mac)
        seen: set[MacAddress] = set()
        while node is not None and node.mac not in seen:
            seen.add(node.mac)
            path.append(node)
            node = self.parent(node.mac)
        return path


def translate_topology(
    nodes: Any,
    status: ARAiMeshOnboardingStatus | None = None,
    onboarding: dict[str, Any] | None = None,
) -> ARAiMeshTopology:
    """Build a topology from the `get_cfg_clientlist` node list."""

    raw_nodes = (
        [n for n in nodes if isinstance(n, dict)]
        if isinstance(nodes, list)
        else []
    )
    result: dict[MacAddress, ARAiMeshNode] = {}
    for raw in raw_nodes:
        node = _translate_node(raw, raw_nodes)
        if node is not None:
            result[node.mac] = node

    return ARAiMeshTopology(
        nodes=result,
        status=status or ARAiMeshOnboardingStatus(),
        onboarding=onboarding,
    )
