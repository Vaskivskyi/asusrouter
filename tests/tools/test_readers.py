"""Test AsusRouter readers tools."""

import pytest

from asusrouter.const import ContentType
from asusrouter.tools import readers


@pytest.mark.parametrize(
    "dict1, dict2, expected",
    [
        # Test non-nested dictionaries
        ({"a": 1, "b": 2}, {"b": 3, "c": 4}, {"a": 1, "b": 2, "c": 4}),
        # Test nested dictionaries
        (
            {"a": 1, "b": {"x": 2}},
            {"b": {"y": 3}, "c": 4},
            {"a": 1, "b": {"x": 2, "y": 3}, "c": 4},
        ),
        # Test with None values
        ({"a": None, "b": 2}, {"a": 1, "b": None}, {"a": 1, "b": 2}),
        ({"a": None}, {"a": {"b": 1}}, {"a": {"b": 1}}),
    ],
)
def test_merge_dicts(dict1, dict2, expected):
    """Test merge_dicts method."""

    assert readers.merge_dicts(dict1, dict2) == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        ("Test string", "test_string"),  # Upper case
        (
            "test with  special ^$@ characters",
            "test_with_special_characters",
        ),  # Special characters
        ("snake_case", "snake_case"),  # Already snake case
    ],
)
def test_read_as_snake_case(content, expected):
    """Test read_as_snake_case method."""

    assert readers.read_as_snake_case(content) == expected


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({"content-type": "application/json;charset=UTF-8"}, ContentType.JSON),
        ({"content-type": "application/xml"}, ContentType.XML),
        ({"content-type": "text/html"}, ContentType.HTML),
        ({"content-type": "text/plain"}, ContentType.TEXT),
        ({"content-type": "application/octet-stream"}, ContentType.BINARY),
        ({"content-type": "application/unknown"}, ContentType.UNKNOWN),
        ({}, ContentType.UNKNOWN),
    ],
)
def test_read_content_type(headers, expected):
    """Test read_content_type method."""

    assert readers.read_content_type(headers) == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        # JS from the active temperature sensors
        ('curr_coreTmp_wl0_raw = "44&deg;C";', {"curr_coreTmp_wl0_raw": "44&deg;C"}),
        # JS from the disabled temperature sensors
        (
            'curr_coreTmp_wl2_raw = "<i>disabled</i>";',
            {"curr_coreTmp_wl2_raw": "<i>disabled</i>"},
        ),
        # JS from the VPN
        ('vpn_client1_status = "None";', {"vpn_client1_status": "None"}),
    ],
)
def test_read_js_variables(content, expected):
    """Test read_js_variables method."""

    assert readers.read_js_variables(content) == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        # JSON from ethernet ports
        (
            '{ "portSpeed": { "WAN 0": "G", "LAN 1": "G", "LAN 2": "G", "LAN 3": "G",\
                "LAN 4": "X", "LAN 5": "X", "LAN 6": "X", "LAN 7": "X", "LAN 8": "G" },\
                "portCount": { "wanCount": 1, "lanCount": 8 } }',
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
            '{"wlc_0_arr":["11", "11", "11"],"wlc_1_arr":["2", "2", "2"],\
                "wlc_2_arr":["0", "0", "0"],"wlc_3_arr":["0", "0", "0"],\
                "conn_stats_arr":["394","56"],"mem_stats_arr":["882.34", "395.23",\
                "0.00", "52.64", "0.00", "0.00", "85343", "7.61 / 63.00 MB"],\
                "cpu_stats_arr":["2.18", "2.09", "2.03"]}',
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
    ],
)
def test_read_json_content(content, expected):
    """Test read_json_content method."""

    assert readers.read_json_content(content) == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        # Test valid MAC addresses
        ("01:23:45:67:89:AB", True),
        ("01-23-45-67-89-AB", True),
        # Test invalid MAC addresses
        ("01:23:45:67:89-87-65", False),
        ("01-23-45-67-89", False),
        ("01:23:45:67:89:ZZ", False),
        ("   ", False),
        # Test non-string input
        (1234567890, False),
        (None, False),
    ],
)
def test_readable_mac(content, expected):
    """Test readable_mac method."""

    assert readers.readable_mac(content) == expected
