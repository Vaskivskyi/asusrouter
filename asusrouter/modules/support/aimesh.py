"""Supported AiMesh features."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.aimesh import ARAiMeshFeature
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
)
from asusrouter.tools.readers import is_true_in_dict

TRANSLATION_TABLE_AIMESH: dict[ARSupportValue, ARAiMeshFeature] = {
    ARSupportValue.AIMESH_NEW_ONBOARDING: ARAiMeshFeature.NEW_ONBOARDING,
    ARSupportValue.AIMESH_NODE: ARAiMeshFeature.NODE,
    ARSupportValue.AIMESH_ROUTER: ARAiMeshFeature.ROUTER,
}


translate_aimesh = make_bool_translator(ARSupportValue.AIMESH.value)


def translate_aimesh_features(data: dict[str, Any]) -> list[ARAiMeshFeature]:
    """Translate AiMesh features."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    return [
        feature
        for (
            support_value,
            feature,
        ) in TRANSLATION_TABLE_AIMESH.items()
        if is_true_in_dict(support_value.value, data)
    ]


translate_aimesh_generation = make_int_translator(ARSupportValue.AIMESH.value)
