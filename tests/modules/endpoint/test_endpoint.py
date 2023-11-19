"""Test for the main endpoint module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asusrouter.error import AsusRouter404Error
from asusrouter.modules.endpoint import (
    Endpoint,
    _get_module,
    check_available,
    data_get,
    data_set,
    process,
    read,
)


def test_get_module():
    """Test _get_module method."""

    # Test valid endpoint
    with patch("importlib.import_module") as mock_import:
        mock_import.return_value = "mocked_module"
        result = _get_module(Endpoint.RGB)
        assert result == "mocked_module"
        mock_import.assert_called_once_with("asusrouter.modules.endpoint.rgb")

    # Test invalid endpoint
    with patch("importlib.import_module") as mock_import:
        mock_import.side_effect = ModuleNotFoundError
        result = _get_module(Endpoint.FIRMWARE)
        assert result is None
        mock_import.assert_called_once_with("asusrouter.modules.endpoint.firmware")


def test_read():
    """Test read method."""

    # Mock the module and its read method
    mock_module = MagicMock()
    mock_module.read.return_value = {"mocked": "data"}

    # Test valid endpoint
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ) as mock_get_module:
        result = read(Endpoint.FIRMWARE, "content")
        assert result == {"mocked": "data"}
        mock_get_module.assert_called_once_with(Endpoint.FIRMWARE)
        mock_module.read.assert_called_once_with("content")

    # Test invalid endpoint
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=None
    ) as mock_get_module:
        result = read(Endpoint.RGB, "content")
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.RGB)


@pytest.mark.parametrize(
    "require_history,require_firmware,require_wlan,call_count",
    [
        (True, False, False, 1),
        (False, True, False, 1),
        (False, False, True, 1),
        (False, False, False, 0),
        (True, True, True, 3),
    ],
)
def test_process(require_history, require_firmware, require_wlan, call_count):
    """Test process method."""

    # Mock the module and its process method
    mock_module = MagicMock()
    mock_module.process.return_value = {"mocked": "data"}

    # Mock the data_set function
    mock_data_set = MagicMock()

    # Define a side effect function for getattr
    def getattr_side_effect(_, attr, default=None):
        if attr == "REQUIRE_HISTORY":
            return require_history
        if attr == "REQUIRE_FIRMWARE":
            return require_firmware
        if attr == "REQUIRE_WLAN":
            return require_wlan
        return default

    # Test valid endpoint
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ), patch("asusrouter.modules.endpoint.data_set", mock_data_set), patch(
        "asusrouter.modules.endpoint.getattr", side_effect=getattr_side_effect
    ):
        result = process(Endpoint.DEVICEMAP, {"key": "value"})
        assert result == {"mocked": "data"}
        mock_module.process.assert_called_once_with({"key": "value"})
        assert mock_data_set.call_count == call_count


def test_process_no_module():
    """Test process method when no module is found."""

    # Mock the _get_module function to return None
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=None
    ) as mock_get_module:
        result = process(Endpoint.RGB, {"key": "value"})
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.RGB)


def test_data_set():
    """Test data_set function."""

    # Test data
    data = {"key1": "value1"}
    kwargs = {"key2": "value2", "key3": "value3"}

    # Call the function
    result = data_set(data, **kwargs)

    # Check the result
    assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}


@pytest.mark.parametrize(
    "data, key, expected, data_left",
    [
        # Key exists
        ({"key1": "value1", "key2": "value2"}, "key1", "value1", {"key2": "value2"}),
        # Key does not exist
        (
            {"key1": "value1", "key2": "value2"},
            "key3",
            None,
            {"key1": "value1", "key2": "value2"},
        ),
        # Empty data
        ({}, "key1", None, {}),
    ],
)
def test_data_get(data, key, expected, data_left):
    """Test data_get function."""

    # Call the function
    result = data_get(data, key)

    # Check the result
    assert result == expected
    assert data == data_left


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "api_query_return, expected_result",
    [
        # Test case: status 200
        ((200, None, None), True),
        # Test case: status not 200
        ((403, None, None), False),
        # Test case: AsusRouter404Error is raised
        (AsusRouter404Error(), False),
    ],
)
async def test_check_available(api_query_return, expected_result):
    """Test check_available function."""

    # Mock the api_query function
    api_query = AsyncMock()
    if isinstance(api_query_return, Exception):
        api_query.side_effect = api_query_return
    else:
        api_query.return_value = api_query_return

    # Call the function
    result = await check_available(Endpoint.DEVICEMAP, api_query)

    # Check the result
    assert result == expected_result
