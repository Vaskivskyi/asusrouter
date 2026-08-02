"""Tests for the support credentials module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.credentials.enums import ARCredentialsCapability
from asusrouter.modules.support.credentials import (
    translate_credentials_capabilities,
)
from asusrouter.modules.support.flag import ARSupportValue


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # Nothing advertised
        ({}, {}),
        # Modern firmware reporting the full set
        (
            {
                ARSupportValue.CHPASS.value: 1,
                ARSupportValue.SECURE_DEFAULT.value: 1,
                ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value: "32",
                ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: "16",
            },
            {
                ARCredentialsCapability.CHPASS: True,
                ARCredentialsCapability.SECURE_DEFAULT: True,
                ARCredentialsCapability.USERNAME_MAX_LENGTH: 32,
                ARCredentialsCapability.PASSWORD_MAX_LENGTH: 16,
            },
        ),
        # Flags reported as disabled are left out
        (
            {
                ARSupportValue.CHPASS.value: 0,
                ARSupportValue.SECURE_DEFAULT.value: 0,
            },
            {},
        ),
        # A zero length is unreported, not a limit of zero
        (
            {
                ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value: "0",
                ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: "0",
            },
            {},
        ),
        # Legacy firmware advertises the lengths but has no CHPASS
        (
            {ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value: "32"},
            {ARCredentialsCapability.PASSWORD_MAX_LENGTH: 32},
        ),
    ],
)
def test_translate_credentials_capabilities(
    data: Any, expected: dict[ARCredentialsCapability, bool | int]
) -> None:
    """Only advertised login capabilities are reported."""

    assert translate_credentials_capabilities(data) == expected
