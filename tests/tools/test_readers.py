"""Test AsusRouter readers tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.tools import readers


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
    """Test is_true_in_dict method."""

    assert readers.is_true_in_dict(value, data) is result


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        # JS from the active temperature sensors
        (
            'curr_coreTmp_wl0_raw = "44&deg;C";',
            {"curr_coreTmp_wl0_raw": "44&deg;C"},
        ),
        # JS from the disabled temperature sensors
        (
            'curr_coreTmp_wl2_raw = "<i>disabled</i>";',
            {"curr_coreTmp_wl2_raw": "<i>disabled</i>"},
        ),
        # JS from the VPN
        ('vpn_client1_status = "None";', {"vpn_client1_status": "None"}),
        # JSON variables
        (
            "get_onboardinglist = [{}][0];",
            {"get_onboardinglist": [{}]},
        ),
        # Value with array index, fallback to string
        ("arr = value[0];", {"arr": "value"}),
        # Quoted string, not valid JSON or Python literal
        ("foo = 'bar';", {"foo": "bar"}),
        ('baz = "qux";', {"baz": "qux"}),
        # Unquoted string, not valid JSON or Python literal
        ("plain = not_json;", {"plain": "not_json"}),
        # Extra quotes
        ('extra = ""quoted"";', {"extra": '"quoted"'}),
        # Multi-line variable
        (
            (
                "multi_line = {\n"
                '    "key1": "value1",\n'
                "    \n"
                '    "key2": "value2"\n'
                "};"
            ),
            {
                "multi_line": {
                    "key1": "value1",
                    "key2": "value2",
                }
            },
        ),
        (
            ('if (true) {\n    conditional = "value";\n};'),
            {"conditional": "value"},
        ),
        # Weird formatting
        (("something var=42;"), {"var": 42}),
        (("something var='4;2';"), {"var": "4;2"}),
        (('var="val42";'), {"var": "val42"}),
        (('var="val;42";'), {"var": "val;42"}),
        (('if(True){var="val42";}'), {"var": "val42"}),
        ('if(True){ var="value;amp"; }', {"var": "value;amp"}),
        (
            ('if(True){var="val;42";}'),
            {"var": "val;42"},
        ),
        # Other cases
        ('var="val\\"42";', {"var": 'val"42'}),
        ("var=42; // comment", {"var": 42}),
        ('var="foo"; /* block comment */', {"var": "foo"}),
        ("a=1; b=2;", {"a": 1, "b": 2}),
        ('   var =   "foo"   ;   ', {"var": "foo"}),
        ("var=;", {"var": ""}),
        # Non-string values
        ("num=123;", {"num": 123}),
        ("flag=true;", {"flag": True}),
    ],
)
def test_read_js_variables(content: str, expected: dict[str, Any]) -> None:
    """Test read_js_variables method."""

    assert readers.read_js_variables(content) == expected


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
    ],
)
def test_read_json_content(
    content: str | None, expected: dict[str, Any]
) -> None:
    """Test read_json_content method."""

    assert readers.read_json_content(content) == expected


def test_read_json_content_fail() -> None:
    """Test read_json_content method with invalid JSON response."""

    with patch(
        "asusrouter.tools.readers.json.loads", return_value="some value"
    ):
        assert readers.read_json_content("invalid json") == {}
