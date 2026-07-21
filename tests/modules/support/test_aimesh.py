"""Tests for the support AiMesh module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.aimesh import ARAiMeshCapability
from asusrouter.modules.support.aimesh import (
    translate_aimesh,
    translate_aimesh_capabilities,
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
        ({}, {}),
        (
            {ARSupportValue.AIMESH_NEW_ONBOARDING.value: 1},
            {ARAiMeshCapability.NEW_ONBOARDING: True},
        ),
        (
            {ARSupportValue.AIMESH_NODE.value: 1},
            {ARAiMeshCapability.NODE: True},
        ),
        # GENERATION carries the amas version, present only when > 0
        (
            {ARSupportValue.AIMESH.value: 2},
            {ARAiMeshCapability.GENERATION: 2},
        ),
        ({ARSupportValue.AIMESH.value: "0"}, {}),
        (
            {
                ARSupportValue.AIMESH.value: 3,
                ARSupportValue.AIMESH_NODE.value: 1,
                ARSupportValue.AIMESH_ROUTER.value: 1,
                ARSupportValue.AIMESH_NEW_ONBOARDING.value: 1,
            },
            {
                ARAiMeshCapability.NEW_ONBOARDING: True,
                ARAiMeshCapability.NODE: True,
                ARAiMeshCapability.ROUTER: True,
                ARAiMeshCapability.GENERATION: 3,
            },
        ),
    ],
)
def test_translate_aimesh_capabilities(
    data: Any, expected: dict[ARAiMeshCapability, bool | int]
) -> None:
    """Test translate_aimesh_capabilities maps AiMesh capabilities."""

    assert translate_aimesh_capabilities(data) == expected
