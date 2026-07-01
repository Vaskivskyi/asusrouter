"""Tests for the common vendor module."""

from __future__ import annotations

import pytest

from asusrouter.modules.common.vendor import format_vendor


@pytest.mark.parametrize(
    ("vendor", "result"),
    [
        # Prefix-coded values
        ("android-dhcp-13", "Android 13"),
        ("android-dhcp-", "Android "),
        # Exact aliases
        ("MSFT 5.0", "Microsoft Corporation"),
        # Passthrough
        ("Apple, Inc.", "Apple, Inc."),
        # Empty and None
        ("", ""),
        (None, None),
    ],
)
def test_format_vendor(vendor: str | None, result: str | None) -> None:
    """Test format_vendor."""

    assert format_vendor(vendor) == result
