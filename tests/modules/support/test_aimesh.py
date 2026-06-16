"""Tests for the support AiMesh module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aimesh import ARAiMeshCapability
from asusrouter.modules.support.aimesh import (
    translate_aimesh,
    translate_aimesh_capabilities,
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
        (
            {ARSupportValue.AIMESH_NEW_ONBOARDING.value: 1},
            [ARAiMeshCapability.NEW_ONBOARDING],
        ),
        ({ARSupportValue.AIMESH_NODE.value: 1}, [ARAiMeshCapability.NODE]),
        (
            {ARSupportValue.AIMESH_ROUTER.value: 1},
            [ARAiMeshCapability.ROUTER],
        ),
        ({}, []),
    ],
)
def test_translate_aimesh_capabilities(
    data: Any, expected: list[ARAiMeshCapability]
) -> None:
    """Test translate_aimesh_capabilities returns correct capability list."""

    assert translate_aimesh_capabilities(data) == expected


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
