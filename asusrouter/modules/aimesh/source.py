"""AiMesh data source for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.aimesh.topology import (
    ARAiMeshTopology,
    translate_onboarding_status,
    translate_topology,
)
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.readers import read_js_section
from asusrouter.tools.types import ARCallbackType


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
    "ARAiMeshSource",
    "ARAiMeshSourceUniversal",
    "get_state",
    "translate_state",
]
