"""Aura device-support helpers for AsusRouter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from asusrouter.modules.aura.enums import ARAuraCapability
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.modules.support.helpers import (
    support_available_in,
    support_value,
)

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity


def aura_supported(identity: ARDeviceIdentity | None) -> bool:
    """Check whether the device exposes Aura."""

    return identity is not None and bool(
        support_value(identity.support, ARSupportType.AURA)
    )


def night_mode_supported(identity: ARDeviceIdentity | None) -> bool:
    """Check whether the device exposes Aura night mode."""

    return identity is not None and support_available_in(
        identity.support,
        ARSupportType.AURA_CAPABILITIES,
        ARAuraCapability.NIGHT_MODE,
    )


__all__ = [
    "aura_supported",
    "night_mode_supported",
]
