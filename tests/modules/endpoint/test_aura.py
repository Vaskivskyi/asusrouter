"""Tests for the Aura endpoint module."""

from unittest.mock import patch

from asusrouter.modules.endpoint.aura import read


@patch("asusrouter.modules.endpoint.aura.read_json_content")
def test_read(mock_read_json_content):
    """Test read function."""

    # Input data
    content = '{"key1": "value1", "key2": "value2"}'

    # Expected data
    expected_command = {"key1": "value1", "key2": "value2"}

    # Mock the read_json_content function
    mock_read_json_content.return_value = expected_command

    # Call the function
    result = read(content)

    # Check the result
    assert result == expected_command
    mock_read_json_content.assert_called_once_with(content)
