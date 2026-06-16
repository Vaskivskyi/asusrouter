"""Supported AiMesh."""

from __future__ import annotations

from asusrouter.modules.aimesh import ARAiMeshCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
    make_list_translator,
)

translate_aimesh = make_bool_translator(ARSupportValue.AIMESH.value)
translate_aimesh_capabilities = make_list_translator(
    {
        ARSupportValue.AIMESH_NEW_ONBOARDING.value: (
            ARAiMeshCapability.NEW_ONBOARDING
        ),
        ARSupportValue.AIMESH_NODE.value: ARAiMeshCapability.NODE,
        ARSupportValue.AIMESH_ROUTER.value: ARAiMeshCapability.ROUTER,
    }
)
translate_aimesh_generation = make_int_translator(ARSupportValue.AIMESH.value)
