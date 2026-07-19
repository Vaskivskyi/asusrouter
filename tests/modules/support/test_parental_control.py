"""Tests for the support parental control module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.parental_control import (
    translate_parental_control_max_entries,
    translate_parental_control_max_rules,
    translate_parental_control_sched_version,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: "16"}, 16),
        ({ARSupportValue.PARENTAL_CONTROL_MAX_RULES.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_max_rules(data: Any, expected: int) -> None:
    """The max-rules translator reads the reported integer."""

    assert translate_parental_control_max_rules(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.PARENTAL_CONTROL_MAX_ENTRIES.value: "128"}, 128),
        ({ARSupportValue.PARENTAL_CONTROL_MAX_ENTRIES.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_max_entries(data: Any, expected: int) -> None:
    """The max-entries translator reads the reported integer."""

    assert translate_parental_control_max_entries(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ARSupportValue.PARENTAL_CONTROL_SCHED_VERSION.value: "3"}, 3),
        ({ARSupportValue.PARENTAL_CONTROL_SCHED_VERSION.value: "0"}, 0),
        ({}, 0),
    ],
)
def test_translate_sched_version(data: Any, expected: int) -> None:
    """The schedule-version translator reads the reported integer."""

    assert translate_parental_control_sched_version(data) == expected
