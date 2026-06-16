"""Tests for the support AiMesh module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aimesh import ARAiMeshFeature
from asusrouter.modules.support.aimesh import (
    translate_aimesh,
    translate_aimesh_features,
    translate_aimesh_generation,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.AIMESH.value: 1}, True),
        ({ARSupportValue.AIMESH.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_aimesh(data: Any, expected: bool) -> None:
    """Test translate_aimesh returns correct presence flag."""

    assert translate_aimesh(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        (
            {ARSupportValue.AIMESH_NEW_ONBOARDING.value: 1},
            [ARAiMeshFeature.NEW_ONBOARDING],
        ),
        ({ARSupportValue.AIMESH_NODE.value: 1}, [ARAiMeshFeature.NODE]),
        ({ARSupportValue.AIMESH_ROUTER.value: 1}, [ARAiMeshFeature.ROUTER]),
        (
            {
                ARSupportValue.AIMESH_NEW_ONBOARDING.value: 1,
                ARSupportValue.AIMESH_NODE.value: 1,
            },
            [ARAiMeshFeature.NEW_ONBOARDING, ARAiMeshFeature.NODE],
        ),
        ("not_a_dict", []),
    ],
)
def test_translate_aimesh_features(
    data: Any, expected: list[ARAiMeshFeature]
) -> None:
    """Test translate_aimesh_features returns the enabled features."""

    assert translate_aimesh_features(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.AIMESH.value: 2}, 2),
        ({ARSupportValue.AIMESH.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_aimesh_generation(data: Any, expected: int) -> None:
    """Test translate_aimesh_generation returns the generation value."""

    assert translate_aimesh_generation(data) == expected
