"""Tests for asusrouter.modules.common.status."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common.status import STATUS_CODE_KEY, ARStatusCode


class TestARStatusCode:
    """Tests for ARStatusCode."""

    def test_status_code_key(self) -> None:
        """The status code key matches the device response field."""

        assert STATUS_CODE_KEY == "statusCode"

    def test_success_value(self) -> None:
        """SUCCESS maps to its string value."""

        assert ARStatusCode.SUCCESS.value == "success"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("success", ARStatusCode.SUCCESS),
            ("error", ARStatusCode.UNKNOWN),
            (None, ARStatusCode.UNKNOWN),
        ],
    )
    def test_from_value(self, value: Any, expected: ARStatusCode) -> None:
        """from_value maps known strings, falls back to UNKNOWN."""

        assert ARStatusCode.from_value(value) == expected
