"""Supported AiMesh."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.aimesh import ARAiMeshCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.converters.raw import raw_to_int
from asusrouter.tools.readers import is_true_in_dict

translate_aimesh = make_bool_translator(ARSupportValue.AIMESH.value)

_CAPABILITY_FLAGS = {
    ARSupportValue.AIMESH_NEW_ONBOARDING.value: (
        ARAiMeshCapability.NEW_ONBOARDING
    ),
    ARSupportValue.AIMESH_NODE.value: ARAiMeshCapability.NODE,
    ARSupportValue.AIMESH_ROUTER.value: ARAiMeshCapability.ROUTER,
}


def translate_aimesh_capabilities(
    data: dict[str, Any],
) -> dict[ARAiMeshCapability, bool | int]:
    """Map advertised AiMesh capabilities; GENERATION carries the version."""

    capabilities: dict[ARAiMeshCapability, bool | int] = {
        capability: True
        for key, capability in _CAPABILITY_FLAGS.items()
        if is_true_in_dict(key, data)
    }

    generation = raw_to_int(data.get(ARSupportValue.AIMESH.value))
    if generation:
        capabilities[ARAiMeshCapability.GENERATION] = generation

    return capabilities
