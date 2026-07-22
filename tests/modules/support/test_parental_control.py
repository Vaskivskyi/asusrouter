"""Tests for the support parental control module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.parental_control import ARParentalControlCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.parental_control import (
    translate_parental_control,
    translate_parental_control_capabilities,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.PARENTAL_CONTROL.value: 1}, True),
        ({ARSupportValue.PARENTAL_CONTROL.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_parental_control(data: Any, expected: bool) -> None:
    """Test translate_parental_control reads the PARENTAL2 flag."""

    assert translate_parental_control(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, {}),
        (
            {ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: "16"},
            {ARParentalControlCapability.MAX_RULES: 16},
        ),
        # A zero-valued limit is dropped
        ({ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: "0"}, {}),
        (
            {
                ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: "64",
                ARSupportValue.PARENTAL_CONTROL_MAX_ENTRIES.value: "256",
                ARSupportValue.PARENTAL_CONTROL_SCHED_VERSION.value: "3",
            },
            {
                ARParentalControlCapability.MAX_ENTRIES: 256,
                ARParentalControlCapability.MAX_RULES: 64,
                ARParentalControlCapability.SCHED_VERSION: 3,
            },
        ),
    ],
)
def test_translate_parental_control_capabilities(
    data: Any, expected: dict[ARParentalControlCapability, int]
) -> None:
    """Test translate_parental_control_capabilities maps the int limits."""

    assert translate_parental_control_capabilities(data) == expected
