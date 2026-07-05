"""Tests for the support SDN module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.sdn import (
    translate_sdn_awv,
    translate_sdn_mainfh,
    translate_sdn_max_rules,
    translate_sdn_mwl,
    translate_sdn_priority,
)


@pytest.mark.parametrize(
    ("translator", "token"),
    [
        (translate_sdn_awv, ARSupportValue.SDN_AWV.value),
        (translate_sdn_mainfh, ARSupportValue.SDN_MAINFH.value),
        (translate_sdn_max_rules, ARSupportValue.SDN_MAX_RULES.value),
        (translate_sdn_mwl, ARSupportValue.SDN_MWL.value),
        (translate_sdn_priority, ARSupportValue.SDN_PRIORITY.value),
    ],
)
def test_translate_sdn_int(
    translator: Callable[[dict[str, Any]], int], token: str
) -> None:
    """Each SDN flag is read as an integer from its token, 0 when absent."""

    assert translator({token: "19"}) == 19
    assert translator({token: 6}) == 6
    assert translator({}) == 0
