"""Tests for asusrouter module-level functions."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from asusrouter.asusrouter import _get_call_matrix
from asusrouter.modules.source import ARDataSource, ARDataState
from tests.helpers import MakeStateFactory


class TestGetCallMatrix:
    """Tests for _get_call_matrix."""

    @pytest.mark.parametrize(
        ("caller_keys", "expected_groups"),
        [
            ([], {}),
            ([None, None], {}),
            (["a"], {"a": 1}),
            (["a", "a"], {"a": 2}),
            (["a", "b"], {"a": 1, "b": 1}),
            (["a", None, "a"], {"a": 2}),
        ],
        ids=[
            "empty",
            "all_none_callers",
            "single_state",
            "same_caller",
            "different_callers",
            "mixed",
        ],
    )
    def test_groups_by_caller(
        self,
        make_state: MakeStateFactory,
        caller_keys: list[str | None],
        expected_groups: dict[str, int],
    ) -> None:
        """Groups states by caller; skips states with None caller."""

        callers: dict[str, Mock] = {k: Mock() for k in expected_groups}
        states: list[ARDataState] = [
            make_state(ARDataSource(), caller=callers.get(k) if k else None)
            for k in caller_keys
        ]

        matrix = _get_call_matrix(states)

        assert len(matrix) == len(expected_groups)
        for key, count in expected_groups.items():
            assert len(matrix[callers[key]]) == count
