"""Tests for the support ftp module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.ftp import ARFTPCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.ftp import (
    translate_ftp,
    translate_ftp_capabilities,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.FTP.value: 1}, False),
        ({ARSupportValue.FTP.value: "0"}, True),
        ({}, True),
    ],
)
def test_translate_ftp(data: Any, expected: bool) -> None:
    """Test translate_ftp returns correct FTP support value."""

    assert translate_ftp(data) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({}, []),
        (
            {ARSupportValue.FTP_SSL.value: 1},
            [ARFTPCapability.SSL],
        ),
        (
            {ARSupportValue.FTP_SSL.value: "0"},
            [],
        ),
        # Not a dict
        ("not_a_dict", []),
        (None, []),
    ],
)
def test_translate_ftp_capabilities(
    data: Any, expected: list[ARFTPCapability]
) -> None:
    """Test translate_ftp_capabilities returns correct capability list."""

    assert translate_ftp_capabilities(data) == expected
