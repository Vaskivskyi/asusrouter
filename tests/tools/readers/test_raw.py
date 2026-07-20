"""Tests for the raw readers."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.tools.readers.raw import is_true_in_dict, read_json_content


@pytest.mark.parametrize(
    ("value", "data", "result"),
    [
        # Value present and equal to 1
        ("key1", {"key1": 1}, True),
        ("key1", {"key1": "1"}, True),
        ("key1", {"key1": True}, True),
        # Value present but not equal to 1
        ("key1", {"key1": 0}, False),
        ("key1", {"key1": "0"}, False),
        ("key1", {"key1": False}, False),
        ("key1", {"key1": "some string"}, False),
        # Value not present
        ("key1", {"key2": 1}, False),
        ("key1", {}, False),
    ],
)
def test_is_true_in_dict(
    value: str, data: dict[str, Any], result: bool
) -> None:
    """Test is_true_in_dict."""

    assert is_true_in_dict(value, data) is result


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        # JSON from ethernet ports
        (
            (
                '{ "portSpeed": { "WAN 0": "G", "LAN 1": "G", "LAN 2": "G", '
                '"LAN 3": "G", "LAN 4": "X", "LAN 5": "X", "LAN 6": "X", '
                '"LAN 7": "X", "LAN 8": "G" }, "portCount": { "wanCount": 1, '
                '"lanCount": 8 } }'
            ),
            {
                "portSpeed": {
                    "WAN 0": "G",
                    "LAN 1": "G",
                    "LAN 2": "G",
                    "LAN 3": "G",
                    "LAN 4": "X",
                    "LAN 5": "X",
                    "LAN 6": "X",
                    "LAN 7": "X",
                    "LAN 8": "G",
                },
                "portCount": {"wanCount": 1, "lanCount": 8},
            },
        ),
        # JSON from sysinfo
        (
            (
                '{"wlc_0_arr":["11", "11", "11"],'
                '"wlc_1_arr":["2", "2", "2"],'
                '"wlc_2_arr":["0", "0", "0"],'
                '"wlc_3_arr":["0", "0", "0"],'
                '"conn_stats_arr":["394","56"],'
                '"mem_stats_arr":["882.34", "395.23",'
                '"0.00", "52.64", "0.00", "0.00", "85343", "7.61 / 63.00 MB"],'
                '"cpu_stats_arr":["2.18", "2.09", "2.03"]}'
            ),
            {
                "wlc_0_arr": ["11", "11", "11"],
                "wlc_1_arr": ["2", "2", "2"],
                "wlc_2_arr": ["0", "0", "0"],
                "wlc_3_arr": ["0", "0", "0"],
                "conn_stats_arr": ["394", "56"],
                "mem_stats_arr": [
                    "882.34",
                    "395.23",
                    "0.00",
                    "52.64",
                    "0.00",
                    "0.00",
                    "85343",
                    "7.61 / 63.00 MB",
                ],
                "cpu_stats_arr": ["2.18", "2.09", "2.03"],
            },
        ),
        # Test valid JSON content
        ('{"key": "value"}', {"key": "value"}),
        # Test empty content
        (None, {}),
        # Test invalid JSON content
        ("not a json", {}),
        # Test missing values
        (
            '{ , "key1": "value1", , "key2": "value2", }',
            {"key1": "value1", "key2": "value2"},
        ),
        # Test keys without values
        (
            '{"key1": "value1", "key2": , "key3": "value3", "key4": ,}',
            {"key1": "value1", "key2": None, "key3": "value3", "key4": None},
        ),
        # Legacy firmware emits get_clientlist without wrapping braces
        (
            '{\n"get_clientlist":"AA:BB":{"name":"x"},"maclist":["AA:BB"],\n'
            '"get_clientlist_from_json_database":""\n}',
            {
                "get_clientlist": {
                    "AA:BB": {"name": "x"},
                    "maclist": ["AA:BB"],
                },
                "get_clientlist_from_json_database": "",
            },
        ),
        # A properly wrapped get_clientlist is left untouched
        (
            '{"get_clientlist":{"AA:BB":{"name":"x"}},'
            '"get_clientlist_from_json_database":""}',
            {
                "get_clientlist": {"AA:BB": {"name": "x"}},
                "get_clientlist_from_json_database": "",
            },
        ),
    ],
)
def test_read_json_content(
    content: str | None, expected: dict[str, Any]
) -> None:
    """Test read_json_content."""

    assert read_json_content(content) == expected


def test_read_json_content_fail() -> None:
    """read_json_content returns empty on a non-dict json result."""

    with patch(
        "asusrouter.tools.readers.raw.json.loads", return_value="some value"
    ):
        assert read_json_content("invalid json") == {}
