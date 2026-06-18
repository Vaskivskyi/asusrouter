"""Integer converters for AsusRouter."""

from __future__ import annotations


def int_to_bits(value: int) -> frozenset[int]:
    """Return set of bit positions that are set in value."""

    if value <= 0:
        return frozenset()
    result = set()
    while value:
        lsb = value & -value
        result.add(lsb.bit_length() - 1)
        value &= value - 1
    return frozenset(result)
