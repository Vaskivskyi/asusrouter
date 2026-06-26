"""Test AsusRouter devicemap endpoint module."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from asusrouter.modules.data import AsusData
from asusrouter.modules.endpoint import devicemap


def generate_xml_content(groups: dict[str, Any]) -> str:
    """Generate XML content based on input parameters."""

    content = "<devicemap>\n"
    for group, keys in groups.items():
        content += f"    <{group}>\n"
        for key, value in keys.items():
            content += f"        <{key}>{value}</{key}>\n"
        content += f"    </{group}>\n"
    content += "</devicemap>\n"
    return content


@pytest.mark.parametrize(
    "content",
    [
        "<devicemap></devicemap>",  # Empty devicemap
        "non-xml",  # Invalid XML
    ],
)
def test_read_invalid(content: str) -> None:
    """Test read function with empty devicemap."""

    assert devicemap.read(content) == {}


@pytest.fixture
def common_group() -> dict[str, dict[str, str]]:
    """Return the common test data intermediate."""

    return {
        "group1": {"key1": "value1"},
        "group2": {"key2": "value2"},
        "group3": {"key3": "value3_test"},
    }


@pytest.fixture
def common_test_data_result() -> dict[str, dict[str, str]]:
    """Return the common test data result."""

    return {
        "group1": {"key1": "value1"},
        "group2": {"key2": "value2"},
        "group3": {"key3": "value3"},
    }


@pytest.fixture
def mock_functions() -> Generator[dict[str, MagicMock | Any], None, None]:
    """Return the mock functions."""

    with (
        patch(
            "asusrouter.modules.endpoint.devicemap.read_index",
            return_value={
                "group1": {"key1": "value1"},
                "group3": {"key3": "value3_test"},
            },
        ) as mock_read_index,
        patch(
            "asusrouter.modules.endpoint.devicemap.read_key",
            return_value={"group2": {"key2": "value2"}},
        ) as mock_read_key,
        patch(
            "asusrouter.modules.endpoint.devicemap.merge_dicts",
            side_effect=lambda x, y: {**x, **y},
        ) as mock_merge_dicts,
        patch(
            "asusrouter.modules.endpoint.devicemap.clean_dict",
            side_effect=lambda x: x,
        ) as mock_clean_dict,
        patch(
            "asusrouter.modules.endpoint.devicemap.clean_dict_key_prefix",
            side_effect=lambda x, _: x,
        ) as mock_clean_dict_key_prefix,
        patch(
            "asusrouter.modules.endpoint.devicemap.DEVICEMAP_CLEAR",
            new={
                "group3": {"key3": "_test", "key4": "_test"},
                "group4": {"key5": "_test"},
            },
        ) as mock_devicemap_clear,
    ):
        yield {
            "read_index": mock_read_index,
            "read_key": mock_read_key,
            "merge_dicts": mock_merge_dicts,
            "clean_dict": mock_clean_dict,
            "clean_dict_key_prefix": mock_clean_dict_key_prefix,
            "devicemap_clear": mock_devicemap_clear,
        }


def test_read_with_data(
    mock_functions: dict[str, MagicMock | Any],  # pylint: disable=redefined-outer-name
    common_test_data_result: dict[str, dict[str, str]],  # pylint: disable=redefined-outer-name
    common_group: dict[str, dict[str, str]],  # pylint: disable=redefined-outer-name
) -> None:
    """Test read function."""

    # Test data
    content = generate_xml_content(common_group)
    expected_devicemap = common_test_data_result

    # Call the function
    result = devicemap.read(content)

    # Check the result
    assert result == expected_devicemap

    # Check the calls to the mocked functions
    mock_functions["read_index"].assert_called_with(common_group)
    mock_functions["read_key"].assert_called_with(common_group)
    assert mock_functions["merge_dicts"].call_count == 2
    mock_functions["clean_dict"].assert_called_with(expected_devicemap)
    assert mock_functions["clean_dict_key_prefix"].call_count == 3


@pytest.fixture
def const_devicemap() -> list[tuple[str, str, list[str]]]:
    """Return the const devicemap."""

    return [
        ("output_group1", "group1", ["input_value1"]),
        ("output_group2", "group2", ["input_value3", "input_value4"]),
        ("output_group3", "group3", ["input_value5"]),
        ("output_group4", "group4", ["input_value6"]),
        ("output_group5", "group5", ["input_value2"]),
        ("output_group6", "group6", ["input_value7"]),
    ]


@pytest.fixture
def const_devicemap_result() -> dict[str, dict[str, str]]:
    """Return the const devicemap result."""

    return {
        "output_group1": {"input_value1": "value1"},
        "output_group2": {"input_value3": "value3", "input_value4": "value4"},
        "output_group3": {"input_value5": "value5"},
        "output_group4": {"input_value6": "value6"},
        "output_group5": {},
        "output_group6": {},
    }


@pytest.fixture
def input_data() -> dict[str, list[str]]:
    """Return the input data for the tests."""

    return {
        "group1": ["value1"],
        "group2": ["value3", "value4"],
        "group3": ["value5"],
        "group4": ["value6"],
        # "group5": [],
        "group6": [],
    }


@pytest.fixture
def input_data_key() -> dict[str, Any]:
    """Return the input data for the read_key test."""

    return {
        "group1": ["input_value1=value1"],
        "group2": ["input_value3=value3", "input_value4=value4"],
        "group3": "input_value5=value5",
        "group4": "input_value6=value6",
        "group5": None,
        "group6": [],
    }


def test_read_index(
    const_devicemap: list[tuple[str, str, list[str]]],  # pylint: disable=redefined-outer-name
    const_devicemap_result: dict[str, dict[str, str]],  # pylint: disable=redefined-outer-name
    input_data: dict[str, list[str]],  # pylint: disable=redefined-outer-name
) -> None:
    """Test read_index function."""

    with patch.object(devicemap, "DEVICEMAP_BY_INDEX", new=const_devicemap):
        # Call the function
        result = devicemap.read_index(input_data)

        # Check the result
        assert result == const_devicemap_result


def test_read_key(
    const_devicemap: list[tuple[str, str, list[str]]],  # pylint: disable=redefined-outer-name
    const_devicemap_result: dict[str, dict[str, str]],  # pylint: disable=redefined-outer-name
    input_data_key: dict[str, Any],  # pylint: disable=redefined-outer-name
) -> None:
    """Test read_key function."""

    with patch.object(devicemap, "DEVICEMAP_BY_KEY", new=const_devicemap):
        # Call the function
        result = devicemap.read_key(input_data_key)

        # Check the result
        assert result == const_devicemap_result


@patch("asusrouter.modules.endpoint.devicemap.process_ovpn")
def test_process(mock_process_ovpn: MagicMock) -> None:
    """Process returns the devicemap blob and the OpenVPN data."""

    mock_process_ovpn.return_value = "openvpn"
    data = {"sys": {"x": 1}}

    result = devicemap.process(data)

    assert result == {
        AsusData.DEVICEMAP: data,
        AsusData.OPENVPN: "openvpn",
    }
    mock_process_ovpn.assert_called_once_with(data)


@patch("asusrouter.modules.endpoint.devicemap.AsusOVPNClient")
@patch("asusrouter.modules.endpoint.devicemap.AsusOVPNServer")
@patch("asusrouter.modules.endpoint.devicemap.raw_to_int")
def test_process_ovpn(
    mock_raw_to_int: MagicMock,
    mock_asusovpnserver: MagicMock,
    mock_asusovnclient: MagicMock,
) -> None:
    """Test process_ovpn function."""

    # Prepare the mock functions
    mock_asusovnclient.return_value = MagicMock()
    mock_asusovpnserver.return_value = MagicMock()
    mock_raw_to_int.return_value = 0

    # Prepare the test data
    devicemap_data = {
        "vpn": {
            "client1_state": "state",
            "client1_errno": "errno",
            "server1_state": "state",
        }
    }

    # Call the function with the test data
    result = devicemap.process_ovpn(devicemap_data)

    # Check the result
    expected_result = {
        "client": {
            1: {
                "state": mock_asusovnclient.return_value,
                "errno": 0,
            }
        },
        "server": {
            1: {
                "state": mock_asusovpnserver.return_value,
            }
        },
    }
    assert result == expected_result

    # Check that the mock functions were called with the correct arguments
    mock_asusovnclient.assert_called_once_with(0)
    mock_asusovpnserver.assert_called_once_with(0)
    mock_raw_to_int.assert_any_call("state")
    mock_raw_to_int.assert_any_call("errno")
