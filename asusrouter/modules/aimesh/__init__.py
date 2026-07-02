"""AiMesh module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
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
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.readers_v2 import read_js_section
from asusrouter.tools.types import ARCallbackType


class ARAiMeshCapability(FromStrMixin, StrEnum):
    """AiMesh capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    NEW_ONBOARDING = "new_onboarding"
    NODE = "node"
    ROUTER = "router"


class ARAiMeshSource(ARDataSource):
    """AiMesh topology data source."""


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


ARCallReg.register_module(
    ARAiMeshSource, get_state=get_state, translate_state=translate_state
)


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
    "get_state",
    "translate_onboarding_status",
    "translate_topology",
    "translate_state",
]
