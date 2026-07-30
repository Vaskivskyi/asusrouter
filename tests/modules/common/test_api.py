"""Tests for the common API enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.common.api import ARApiClient


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("app", ARApiClient.APP),
        ("web", ARApiClient.WEB),
        ("APP", ARApiClient.APP),
        ("Web", ARApiClient.WEB),
        ("other", ARApiClient.UNKNOWN),
    ],
)
def test_from_value(value: str, expected: ARApiClient) -> None:
    """Raw tokens (any case) resolve to their member, else UNKNOWN."""

    assert ARApiClient.from_value(value) is expected
