"""Supported AiMesh features."""

from __future__ import annotations

from asusrouter.modules.aimesh import ARAiMeshFeature
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.tools.converters import safe_bool_nn, safe_int_nn

TRANSLATION_TABLE_AIMESH: dict[ARSupportValue, ARAiMeshFeature] = {
    ARSupportValue.AIMESH_NEW_ONBOARDING: ARAiMeshFeature.NEW_ONBOARDING,
    ARSupportValue.AIMESH_NODE: ARAiMeshFeature.NODE,
    ARSupportValue.AIMESH_ROUTER: ARAiMeshFeature.ROUTER,
}


def translate_aimesh(data: dict[str, bool]) -> bool:
    """Translate AiMesh presence."""

    if isinstance(data, dict):
        return safe_bool_nn(data.get(ARSupportValue.AIMESH.value))

    return False  # type: ignore[unreachable]


def translate_aimesh_features(data: dict[str, bool]) -> list[ARAiMeshFeature]:
    """Translate AiMesh features."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    return [
        feature
        for (
            support_value,
            feature,
        ) in TRANSLATION_TABLE_AIMESH.items()
        if safe_bool_nn(data.get(support_value.value))
    ]


def translate_aimesh_generation(data: dict[str, bool]) -> int:
    """Translate AiMesh generation."""

    if not isinstance(data, dict):
        return 0  # type: ignore[unreachable]

    return safe_int_nn(data.get(ARSupportValue.AIMESH.value))
