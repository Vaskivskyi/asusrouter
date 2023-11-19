"""Test AsusRouter command endpoint module."""

from unittest.mock import patch

from asusrouter.modules.endpoint import command


def test_read():
    """Test read function."""

    # Test data
    content = '{"key1": "value1", "key2": "value2"}'
    expected_command = {"key1": "value1", "key2": "value2"}

    # Mock the read_json_content function
    with patch(
        "asusrouter.modules.endpoint.command.read_json_content",
        return_value=expected_command,
    ) as mock_read_json_content:
        # Call the function
        result = command.read(content)

        # Check the result
        assert result == expected_command

        # Check that read_json_content was called with the correct argument
        mock_read_json_content.assert_called_once_with(content)
