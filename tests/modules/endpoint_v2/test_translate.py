"""Tests for asusrouter.modules.endpoint_v2.translate."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.endpoint_v2.translate import read_wan_lan_status


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            'get_wan_lan_status = {"portSpeed": {"WAN 0": "G"}};',
            {"portSpeed": {"WAN 0": "G"}},
        ),
        ("get_wan_lan_status = {};", {}),
        ("", {}),
    ],
    ids=["with_data", "empty_object", "blank"],
)
def test_read_wan_lan_status(content: str, expected: dict[str, Any]) -> None:
    """read_wan_lan_status strips the JS prefix and parses the JSON."""

    assert read_wan_lan_status(content) == expected
