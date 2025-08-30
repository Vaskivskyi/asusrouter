"""Test AsusRouter readers tools."""

from typing import Any
from unittest.mock import patch

import pytest

from asusrouter.const import ContentType
from asusrouter.tools import readers
from asusrouter.tools.units import (
    DataRateUnitConverter,
    UnitConverterBase,
    UnitOfDataRate,
)


class MockConverter(UnitConverterBase):
    """Mock converter for testing."""


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Any float-compatible value should pass if not
        # smaller than zero
        (1.0, True),
        ("0", True),
        (123132, True),
        # Negatives should fail
        (-1.0, False),
        ("-1", False),
        # Non-comparable types should pass, since not negative
        (None, True),
        (object(), True),
        ({}, True),
    ],
)
def test_is_non_negative(value: Any, result: bool) -> None:
    """Test is_non_negative method."""

    assert readers.is_non_negative(value) is result


@pytest.mark.parametrize(
    ("dict1", "dict2", "expected"),
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
def test_merge_dicts(
    dict1: dict[str, Any], dict2: dict[str, Any], expected: dict[str, Any]
) -> None:
    """Test merge_dicts method."""

    assert readers.merge_dicts(dict1, dict2) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Test string", "test_string"),  # Upper case
        (
            "test with  special ^$@ characters",
            "test_with_special_characters",
        ),  # Special characters
        ("snake_case", "snake_case"),  # Already snake case
    ],
)
def test_read_as_snake_case(content: str, expected: str) -> None:
    """Test read_as_snake_case method."""

    assert readers.read_as_snake_case(content) == expected


@pytest.mark.parametrize(
    ("headers", "expected"),
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
def test_read_content_type(
    headers: dict[str, str], expected: ContentType
) -> None:
    """Test read_content_type method."""

    assert readers.read_content_type(headers) == expected


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


@pytest.mark.parametrize(
    ("content", "expected"),
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
def test_readable_mac(content: str | None, expected: bool) -> None:
    """Test readable_mac method."""

    assert readers.readable_mac(content) == expected


def test_read_units_as_base_wrong_converter() -> None:
    """Test read_units_as_base with a wrong converter."""

    with pytest.raises(TypeError, match="Converter must be"):
        readers.read_units_as_base("not a converter", "some_units")  # type: ignore[arg-type]


@pytest.mark.parametrize("mode", ["none", "single", "list"])
def test_read_units_as_base_checks_pass(mode: str) -> None:
    """Reader should call converter.convert_to_base when checks pass."""

    check_calls: Any

    with patch.object(
        MockConverter, "convert_to_base", return_value=1
    ) as mock_convert_to_base:
        if mode == "none":
            check_calls = None
        elif mode == "single":

            def is_positive(v: float) -> bool:
                return v > 0

            check_calls = is_positive
        else:

            def is_positive(v: float) -> bool:
                return v > 0

            def less_than_1(v: float) -> bool:
                return v < 1

            check_calls = [is_positive, less_than_1]

        reader = readers.read_units_as_base(
            MockConverter, "u", check_calls=check_calls, fallback_value=0.0
        )

        result = reader(0.5)
        mock_convert_to_base.assert_called_once_with(0.5, "u")
        assert result == 1


def test_read_units_as_base_checks_fail() -> None:
    """Reader should return fallback value when checks fail."""

    fallback_value = 0.0

    with patch.object(
        MockConverter, "convert_to_base", return_value=1
    ) as mock_convert_to_base:
        check_calls = [lambda v: v > 0, lambda v: v < 1]

        reader = readers.read_units_as_base(
            MockConverter,
            "u",
            check_calls=check_calls,
            fallback_value=fallback_value,
        )

        result = reader(1.5)
        mock_convert_to_base.assert_not_called()
        assert result == fallback_value


def test_read_units_data_rate() -> None:
    """Test read_units_data_rate method."""

    input_value = 42.0

    def return_function(x: Any) -> Any:
        """Return the input value."""

        return x

    with patch(
        "asusrouter.tools.readers.read_units_as_base",
        return_value=return_function,
    ) as mock_read_units_as_base:
        result = readers.read_units_data_rate(
            UnitOfDataRate.MEBIBIT_PER_SECOND
        )

        assert input_value == result(input_value)
        mock_read_units_as_base.assert_called_once_with(
            DataRateUnitConverter,
            UnitOfDataRate.MEBIBIT_PER_SECOND,
            readers.is_non_negative,
            0.0,
        )
