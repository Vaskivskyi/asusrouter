"""Tests for asusrouter.tools.converters_v2.int."""

from __future__ import annotations

import pytest

from asusrouter.tools.converters_v2.int import int_to_bits


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Zero and negative -> early return
        (0, frozenset()),
        (-1, frozenset()),
        (-999, frozenset()),
        # Single bit at various positions
        (1, frozenset({0})),
        (2, frozenset({1})),
        (4, frozenset({2})),
        (1 << 10, frozenset({10})),
        (1 << 30, frozenset({30})),
        # Multiple consecutive bits
        (3, frozenset({0, 1})),
        (7, frozenset({0, 1, 2})),
        (15, frozenset({0, 1, 2, 3})),
        # Multiple non-consecutive bits
        (5, frozenset({0, 2})),
        (9, frozenset({0, 3})),
        # Real-world capability bitmask: WAN(0) + LAN(1) + DUALWAN_PRIMARY(30)
        ((1 << 0) | (1 << 1) | (1 << 30), frozenset({0, 1, 30})),
    ],
)
def test_int_to_bits(value: int, expected: frozenset[int]) -> None:
    """Test int_to_bits returns correct set of set bit positions."""

    result = int_to_bits(value)
    assert result == expected
    assert isinstance(result, frozenset)
