"""Test AsusRouter writers tools."""

from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock, patch

import pytest

from asusrouter.config import (
    CONFIG_DEFAULT_ALREADY_NOTIFIED,
    ARConfigBase,
    ARConfigKeyBase,
)
from asusrouter.const import RequestType
from asusrouter.tools import writers
from asusrouter.tools.identifiers import MacAddress


class MockKey(ARConfigKeyBase):
    """Test keys."""

    EXISTING = "existing"
    ANY = "any"
    SOME = "some"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("test", "nvram_get(test);"),
        (["test1", "test2"], "nvram_get(test1);nvram_get(test2);"),
        (None, None),
    ],
)
def test_nvram(content: str | list[str] | None, expected: str | None) -> None:
    """Test nvram method."""

    assert writers.nvram(content) == expected


@pytest.mark.parametrize(
    ("data", "request_type", "expected"),
    [
        ({"key": "value"}, RequestType.POST, "'key':'value'"),
        ({"key": "value"}, RequestType.GET, "key=value"),
        (
            {"key1": "value1", "key2": "value2"},
            RequestType.POST,
            "'key1':'value1';'key2':'value2'",
        ),
        (
            {"key1": "value1", "key2": "value2"},
            RequestType.GET,
            "key1=value1&key2=value2",
        ),
        ({}, RequestType.POST, ""),
        ({}, RequestType.GET, ""),
        (
            {"mac": MacAddress("aa:bb:cc:dd:ee:ff")},
            RequestType.POST,
            "'mac':'AA:BB:CC:DD:EE:FF'",
        ),
        (
            {"key1": True, "key2": False},
            RequestType.POST,
            "'key1':'1';'key2':'0'",
        ),
        # edge cases
        ({"a b": "c d"}, RequestType.GET, "a+b=c+d"),
        ({"sym": "&=+?"}, RequestType.GET, "sym=%26%3D%2B%3F"),
        ({"flag": True}, RequestType.GET, "flag=1"),
        ({"k'": "v'"}, RequestType.POST, "'k\\'':'v\\''"),
    ],
    ids=[
        "post-simple-single",
        "get-simple-single",
        "post-simple-multiple",
        "get-simple-multiple",
        "empty-post",
        "empty-get",
        "MacAddress",
        "bool-post",
        "get-quoting-spaces",
        "get-quoting-special-chars",
        "get-bool",
        "post-escape-single-quotes",
    ],
)
def test_dict_to_request(
    data: Mapping[str, Any], request_type: RequestType, expected: str | None
) -> None:
    """Test dict_to_request method."""

    assert writers.dict_to_request(data, request_type) == expected


@pytest.mark.parametrize(
    ("key", "called"),
    [
        (MockKey.EXISTING, False),
        (MockKey.ANY, True),
        (MockKey.SOME, True),
    ],
)
def test_ensure_notification_flag(key: ARConfigKeyBase, called: bool) -> None:
    """Test ensure_notification_flag method."""

    # Create a base config and register the key
    config = ARConfigBase()
    config.register(MockKey.EXISTING)

    with (
        patch.object(config, "set", return_value=None) as mock_set,
        patch.object(config, "register", return_value=None) as mock_register,
    ):
        writers.ensure_notification_flag(config, key)

        if called:
            mock_register.assert_called_once_with(key)
            mock_set.assert_called_once_with(
                key, CONFIG_DEFAULT_ALREADY_NOTIFIED
            )
        else:
            mock_register.assert_not_called()
            mock_set.assert_not_called()


def test_ensure_notification_flag_order() -> None:
    """Test ensure_notification_flag does the correct sequencing."""

    calls: list[tuple[Any, ...]] = []

    def rec_contains(k: Any) -> bool:
        """Check if a key is registered."""

        calls.append(("contains", k))
        return False

    def rec_register(k: Any) -> None:
        """Register a key."""

        calls.append(("register", k))

    def rec_set(k: Any, v: Any) -> None:
        """Set a key-value pair."""

        calls.append(("set", k, v))

    config = Mock(spec=ARConfigBase)
    config.register = Mock(side_effect=rec_register)
    config.set = Mock(side_effect=rec_set)
    config.__contains__ = Mock(side_effect=rec_contains)

    writers.ensure_notification_flag(config, MockKey.SOME)

    # Verify the calls made in the correct order
    assert calls == [
        ("contains", MockKey.SOME),
        ("register", MockKey.SOME),
        ("set", MockKey.SOME, CONFIG_DEFAULT_ALREADY_NOTIFIED),
    ]
