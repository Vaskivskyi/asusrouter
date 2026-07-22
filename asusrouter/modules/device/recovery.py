"""Recover identity values missing from the raw device data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.wifi import (
    ARWiFiCapability,
    ARWiFiGeneration,
    ARWiFiMultiBand,
)

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

# Model marker -> WiFi generation
_MODEL_WIFI_GENERATION: tuple[tuple[str, ARWiFiGeneration], ...] = (
    ("be", ARWiFiGeneration.WIFI_7),
    ("axe", ARWiFiGeneration.WIFI_6),
    ("ax", ARWiFiGeneration.WIFI_6),
    ("ac", ARWiFiGeneration.WIFI_5),
)


def _wifi_generation_from_model(model: str | None) -> ARWiFiGeneration:
    """Guess the WiFi generation from the model name marker."""

    if not model:
        return ARWiFiGeneration.UNKNOWN
    lowered = model.lower()
    for marker, generation in _MODEL_WIFI_GENERATION:
        if marker in lowered:
            return generation
    return ARWiFiGeneration.UNKNOWN


def recover_support(identity: ARDeviceIdentity) -> None:
    """Recover unknown values from the complimentary data."""

    support = identity.support
    capabilities = support.get(ARSupportType.WIFI_CAPABILITIES, {})

    recovered: dict[ARWiFiCapability, ARWiFiGeneration | ARWiFiMultiBand] = {}

    if ARWiFiCapability.GENERATION not in capabilities:
        generation = _wifi_generation_from_model(identity.model)
        if generation is not ARWiFiGeneration.UNKNOWN:
            recovered[ARWiFiCapability.GENERATION] = generation

    if ARWiFiCapability.MULTIBAND not in capabilities:
        multiband = ARWiFiMultiBand.from_value(len(identity.wifi))
        if multiband is not ARWiFiMultiBand.UNKNOWN:
            recovered[ARWiFiCapability.MULTIBAND] = multiband

    if recovered:
        support.setdefault(ARSupportType.WIFI_CAPABILITIES, {}).update(
            recovered
        )
