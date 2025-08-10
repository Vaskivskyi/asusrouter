"""Test AsusRouter cleaners tools."""

from asusrouter.tools import cleaners


def test_clean_content():
    """Test clean_content method."""

    # Test with BOM
    content = "\ufefftest"
    assert cleaners.clean_content(content) == "test"

    # Test without BOM
    content = "test"
    assert cleaners.clean_content(content) == "test"


def test_clean_dict():
    """Test clean_dict method."""

    # Test with empty dict
    data = {}
    assert cleaners.clean_dict(data) == {}  # pylint: disable=C1803

    # Test with empty string
    data = {"test": ""}
    assert cleaners.clean_dict(data) == {"test": None}

    # Test with nested dicts
    data = {"test": {"test": ""}}
    assert cleaners.clean_dict(data) == {"test": {"test": None}}


def test_clean_dict_key_prefix():
    """Test clean_dict_key_prefix method."""

    # Test with empty dict
    data = {}
    assert cleaners.clean_dict_key_prefix(data, "prefix") == {}  # pylint: disable=C1803

    # Test with empty string
    data = {"prefix_test": "", "test2": ""}
    assert cleaners.clean_dict_key_prefix(data, "prefix") == {
        "test": "",
        "test2": "",
    }

    # Test with nested dicts
    data = {"prefix_test": {"prefix_test": ""}}
    assert cleaners.clean_dict_key_prefix(data, "prefix") == {
        "test": {"prefix_test": ""}
    }


def test_clean_dict_key():
    """Test clean_dict_key method."""

    # Test with empty dict
    data = {}
    assert cleaners.clean_dict_key(data, "test") == {}  # pylint: disable=C1803

    # Test with empty string
    data = {"test": "", "test2": ""}
    assert cleaners.clean_dict_key(data, "test") == {"test2": ""}

    # Test with nested dicts
    data = {"test": {"test": ""}, "test2": {"test": ""}}
    assert cleaners.clean_dict_key(data, "test") == {"test2": {}}
