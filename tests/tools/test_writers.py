"""Test AsusRouter writers tools."""

from collections.abc import Mapping
from typing import Any

import pytest

from asusrouter.const import RequestType
from asusrouter.tools import writers
from asusrouter.tools.identifiers import MacAddress


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
