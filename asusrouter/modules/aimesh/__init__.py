"""AiMesh module for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    UNKNOWN_MEMBER_STR,
)
from asusrouter.modules.aimesh.capability import ARAiMeshFeature
from asusrouter.modules.aimesh.topology import (
    ARAiMeshBackhaul,
    ARAiMeshDirection,
    ARAiMeshMedium,
    ARAiMeshNode,
    ARAiMeshOnboardingStatus,
    ARAiMeshPort,
    ARAiMeshRadio,
    ARAiMeshRole,
    ARAiMeshTopology,
    ARAiMeshVif,
    translate_onboarding_status,
    translate_topology,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import (
    ARCallableEntry,
    ARCallableRegistry as ARCallReg,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.readers_v2 import read_js_section
from asusrouter.tools.types import ARCallbackType


class ARAiMeshCapability(FromStrMixin, StrEnum):
    """AiMesh capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    NEW_ONBOARDING = "new_onboarding"
    NODE = "node"
    ROUTER = "router"


# TODO: Redo this legacy class
@dataclass
class AiMeshDevice:
    """AiMesh device class."""

    # Status
    status: bool = False

    alias: str | None = None
    model: str | None = None
    product_id: str | None = None
    ip: str | None = None

    fw: str | None = None
    fw_new: str | None = None

    mac: str | None = None

    # Access point: ap2g, ap5g, ap5g1, ap6g, apdwb
    ap: dict[str, Any] | None = None
    # Parent AiMesh: pap2g, rssi2g, pap2g_ssid, pap5g, rssi5g, pap5g_ssid,
    #                pap6g, rssi6g, pap6g_ssid
    parent: dict[str, Any] | None = None
    # Node state
    type: str | None = None
    level: int | None = None
    config: dict[str, Any] | None = None


class ARAiMeshSource(ARDataSource):
    """AiMesh topology data source."""

    def __eq__(self, other: object) -> bool:
        """Two AiMesh sources are equal."""

        if not isinstance(other, ARAiMeshSource):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        """Hash by type."""

        return hash(type(self))

    def __repr__(self) -> str:
        """Representation of the AiMesh source."""

        return "<ARAiMeshSource>"


# Universal instance - preferred
ARAiMeshSourceUniversal: ARAiMeshSource = ARAiMeshSource()


async def get_state(
    callback: ARCallbackType,
    source: ARAiMeshSource,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the raw onboarding data."""

    response: Any = await callback(endpoint=AREndpoint.FETCH_ONBOARDING)

    if not isinstance(response, dict):
        return {}

    return response


def translate_state(
    data: dict[str, Any],
    **kwargs: Any,
) -> ARAiMeshTopology:
    """Translate raw onboarding data into the AiMesh topology."""

    if not isinstance(data, dict) or not data:
        return ARAiMeshTopology()

    onboarding = read_js_section(data, "get_onboardinglist")
    return translate_topology(
        read_js_section(data, "get_cfg_clientlist"),
        status=translate_onboarding_status(
            read_js_section(data, "get_onboardingstatus")
        ),
        onboarding=onboarding if isinstance(onboarding, dict) else None,
    )


calls: dict[str, ARCallableEntry] = {
    AR_CALL_GET_STATE: get_state,
    AR_CALL_TRANSLATE_STATE: translate_state,
}

ARCallReg.register(ARAiMeshSource, **calls)


__all__ = [
    "ARAiMeshBackhaul",
    "ARAiMeshCapability",
    "ARAiMeshDirection",
    "ARAiMeshFeature",
    "ARAiMeshMedium",
    "ARAiMeshNode",
    "ARAiMeshOnboardingStatus",
    "ARAiMeshPort",
    "ARAiMeshRadio",
    "ARAiMeshRole",
    "ARAiMeshSource",
    "ARAiMeshSourceUniversal",
    "ARAiMeshTopology",
    "ARAiMeshVif",
    "AiMeshDevice",
    "get_state",
    "translate_onboarding_status",
    "translate_topology",
    "translate_state",
]
