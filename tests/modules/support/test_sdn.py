"""Tests for the support SDN module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.network import ARSDNCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.sdn import (
    translate_sdn,
    translate_sdn_capabilities,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.SDN.value: 6}, True),
        ({ARSupportValue.SDN.value: "0"}, False),
        ({}, False),
    ],
)
def test_translate_sdn(data: Any, expected: bool) -> None:
    """Test translate_sdn reads the mtlancfg flag."""

    assert translate_sdn(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, {}),
        (
            {ARSupportValue.SDN_MAX_RULES.value: "19"},
            {ARSDNCapability.MAX_RULES: 19},
        ),
        # A zero-valued flag is dropped
        ({ARSupportValue.SDN_MWL.value: "0"}, {}),
        (
            {
                ARSupportValue.SDN_AWV.value: 1,
                ARSupportValue.SDN_MAINFH.value: 1,
                ARSupportValue.SDN_MAX_RULES.value: 19,
                ARSupportValue.SDN_MWL.value: 6,
                ARSupportValue.SDN_PRIORITY.value: 1,
            },
            {
                ARSDNCapability.AWV: 1,
                ARSDNCapability.MAIN_FRONTHAUL: 1,
                ARSDNCapability.MAX_RULES: 19,
                ARSDNCapability.MWL: 6,
                ARSDNCapability.PRIORITY: 1,
            },
        ),
    ],
)
def test_translate_sdn_capabilities(
    data: Any, expected: dict[ARSDNCapability, int]
) -> None:
    """Test translate_sdn_capabilities maps the SDN integer flags."""

    assert translate_sdn_capabilities(data) == expected
