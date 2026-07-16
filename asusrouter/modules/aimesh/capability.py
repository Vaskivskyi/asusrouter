"""AiMesh Capability module for AsusRouter."""

from __future__ import annotations

import logging
import threading
from typing import Any

from asusrouter.modules.aimesh.enums import ARAiMeshFeature
from asusrouter.tools.converters.raw import raw_to_int

_LOGGER = logging.getLogger(__name__)

# capability index -> unknown bit positions already reported, so each
# distinct unknown bit is warned about only once
_reported_unknown_bits: dict[int, set[int]] = {}
_unknown_caps_lock = threading.Lock()

# Unmapped bits we already know about but cannot decode yet. We keep the
# raw value, but do not warn about these - they are not new data
_ACKNOWLEDGED_UNKNOWN: dict[int, frozenset[int]] = {
    4: frozenset({6, 11, 13, 15, 19, 23, 24, 25}),
}


_F = ARAiMeshFeature

# Capability index -> {bit -> feature}
_CAPABILITY_MAP: dict[int, dict[int, ARAiMeshFeature]] = {
    1: {
        0: _F.CENTRAL_LED,
        1: _F.LP55XX_LED,
        2: _F.LED_ON_OFF,
        3: _F.LED_BRIGHTNESS,
        4: _F.LED_AURA,
        5: _F.LED_NIGHT_MODE,
        6: _F.CENTRAL_LED_ON_OFF,
    },
    2: {0: _F.MANUAL_REBOOT},
    3: {0: _F.PREFERABLE_BACKHAUL, 1: _F.PREFER_NODE_APPLY},
    4: {
        0: _F.USB,
        1: _F.GUEST_NETWORK,
        2: _F.WPA3,
        3: _F.VIF_ONBOARDING,
        4: _F.SCHED_V2,
        5: _F.WIFI_RADIO,
        8: _F.SWITCHCTRL,
        9: _F.PORT_STATUS,
        10: _F.LOCAL_ACCESS,
        16: _F.WPA3_ENTERPRISE,
        20: _F.MLO_BH,
        21: _F.MLO_FH,
        22: _F.SMART_HOME_MASTER_UI,
    },
    5: {0: _F.LACP},
    6: {0: _F.GN_2G_1, 1: _F.GN_2G_2, 2: _F.GN_2G_3},
    7: {0: _F.GN_5G_1, 1: _F.GN_5G_2, 2: _F.GN_5G_3},
    8: {0: _F.GN_5GH_1, 1: _F.GN_5GH_2, 2: _F.GN_5GH_3},
    15: {0: _F.WANS_CAP_WAN},
    16: {0: _F.MANUAL_RECONN},
    17: {0: _F.MANUAL_FORCE_ROAMING},
    18: {
        0: _F.FRONTHAUL_AP_OPTION_OFF,
        1: _F.FRONTHAUL_AP_OPTION_AUTO,
        2: _F.FRONTHAUL_AP_OPTION_ON,
    },
    19: {0: _F.MANUAL_STA_BINDING},
    20: {0: _F.MANUAL_RESET_DEFAULT},
    22: {
        0: _F.WIFI_RADIO_0,
        1: _F.WIFI_RADIO_1,
        2: _F.WIFI_RADIO_2,
        3: _F.WIFI_RADIO_3,
        4: _F.WIFI_RADIO_4,
    },
    23: {0: _F.ETHERNET_BACKHAUL_MODE},
    24: {0: _F.GN_6G_1, 1: _F.GN_6G_2, 2: _F.GN_6G_3},
    34: {0: _F.GN_6GH_1, 1: _F.GN_6GH_2, 2: _F.GN_6GH_3},
}


def _warn_unknown_bits(index: int, value: int, known_mask: int) -> None:
    """Warn once per distinct unmapped bit of a known capability index."""

    unknown = value & ~known_mask
    if unknown == 0:
        return

    bits = {bit for bit in range(unknown.bit_length()) if unknown & (1 << bit)}
    acknowledged = _ACKNOWLEDGED_UNKNOWN.get(index, frozenset())
    with _unknown_caps_lock:
        seen = _reported_unknown_bits.setdefault(index, set())
        new_bits = sorted(bits - seen - acknowledged)
        if not new_bits:
            return
        seen.update(new_bits)
        _LOGGER.warning(
            "We found unknown bits `%s` in AiMesh capability `%s`. "
            "Please, report this raw value: `%s`",
            new_bits,
            index,
            value,
        )


def translate_features(capability: Any) -> frozenset[ARAiMeshFeature]:
    """Decode the supported AiMesh features from a capability dict."""

    if not isinstance(capability, dict):
        return frozenset()

    features: set[ARAiMeshFeature] = set()
    for index, bits in _CAPABILITY_MAP.items():
        value = raw_to_int(capability.get(str(index)))
        if value is None:
            continue
        known_mask = 0
        for bit, feature in bits.items():
            known_mask |= 1 << bit
            if value & (1 << bit):
                features.add(feature)
        _warn_unknown_bits(index, value, known_mask)

    return frozenset(features)


def is_fully_decoded(key: str, value: Any) -> bool:
    """Whether every set bit of a capability value is mapped.

    Such a value is fully represented by the decoded features and can be
    dropped from the raw passthrough; one with unmapped bits is kept.
    """

    index = raw_to_int(key)
    bits = _CAPABILITY_MAP.get(index) if index is not None else None
    if bits is None:
        return False

    number = raw_to_int(value)
    if number is None:
        return False

    known = 0
    for bit in bits:
        known |= 1 << bit
    return number & ~known == 0
