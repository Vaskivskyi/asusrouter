"""Tests for the support credentials module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.credentials import (
    translate_chpass,
    translate_http_password_max_length,
    translate_http_username_max_length,
    translate_secure_default,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value: "32"}, 32),
        ({ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_username_max_length(data: Any, expected: int) -> None:
    """The username-length translator reads the reported integer."""

    assert translate_http_username_max_length(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: "32"}, 32),
        ({ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_password_max_length(data: Any, expected: int) -> None:
    """The password-length translator reads the reported integer."""

    assert translate_http_password_max_length(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.SECURE_DEFAULT.value: 1}, True),
        ({ARSupportValue.SECURE_DEFAULT.value: 0}, False),
        ({}, False),
    ],
)
def test_translate_secure_default(data: Any, expected: bool) -> None:
    """The secure-default translator reports the boolean flag."""

    assert translate_secure_default(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.CHPASS.value: 1}, True),
        ({ARSupportValue.CHPASS.value: 0}, False),
        ({}, False),
    ],
)
def test_translate_chpass(data: Any, expected: bool) -> None:
    """The chpass translator reports whether chpass.cgi is available."""

    assert translate_chpass(data) is expected
