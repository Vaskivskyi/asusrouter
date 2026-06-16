"""Tests for the support ai module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.ai import ARAICapability
from asusrouter.modules.support.ai import (
    translate_ai,
    translate_ai_capabilities,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.AI.value: 1}, True),
        ({ARSupportValue.AI.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_ai(data: Any, expected: bool) -> None:
    """Test translate_ai returns correct AI support value."""

    assert translate_ai(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.AI_SLM.value: 1}, [ARAICapability.SLM]),
        (
            {ARSupportValue.AI_UPGRADE_BETA.value: 1},
            [ARAICapability.UPGRADE_BETA],
        ),
        ({ARSupportValue.AI_RESET_BETA.value: 1}, [ARAICapability.RESET_BETA]),
        ({}, []),
    ],
)
def test_translate_ai_capabilities(
    data: Any, expected: list[ARAICapability]
) -> None:
    """Test translate_ai_capabilities returns correct capability list."""

    assert translate_ai_capabilities(data) == expected
