"""Test AsusRouter calculators module"""

import pytest

from asusrouter.const import DATA_TOTAL, DATA_USAGE, DATA_USED
from asusrouter.util import calculators

TEST_USAGE_IN_DICT = {
    DATA_TOTAL: 54,
    DATA_USED: 2,
}
TEST_USAGE_IN_DICT_RESULT = {DATA_TOTAL: 54, DATA_USED: 2, DATA_USAGE: 3.70}
TEST_USAGE_IN_DICT_2 = {
    DATA_TOTAL: 77,
    DATA_USED: 5,
}
TEST_USAGE_IN_DICT_RESULT_2 = {DATA_TOTAL: 77, DATA_USED: 5, DATA_USAGE: 6.49}
TEST_USAGE_IN_DICT_RESULT_3 = {DATA_TOTAL: 77, DATA_USED: 5, DATA_USAGE: 13.04}


def test_usage():
    """Test usage calculator"""

    # Nothing used -> no usage
    assert calculators.usage(0, 0, 0, 0) == 0
    # Normal usage
    assert calculators.usage(19, 117, 15, 102) == 26.67
    # Usage without prervious values
    assert calculators.usage(42, 53) == 79.25

    # Negative usage test
    with pytest.raises(ValueError):
        calculators.usage(10, 20, 11, 15)
    with pytest.raises(ValueError):
        calculators.usage(13, 20, 11, 21)
    # Above 100% usage test
    with pytest.raises(ValueError):
        calculators.usage(2, 1)
    # Zero division
    with pytest.raises(ZeroDivisionError):
        calculators.usage(5, 20, 1, 20) == 0


def test_usage_in_dict():
    """Test usage_in_dict calculator"""

    # Tests with absolute moment data
    assert calculators.usage_in_dict(TEST_USAGE_IN_DICT) == TEST_USAGE_IN_DICT_RESULT
    assert (
        calculators.usage_in_dict(TEST_USAGE_IN_DICT_2) == TEST_USAGE_IN_DICT_RESULT_2
    )

    # Tests with relative data
    assert (
        calculators.usage_in_dict(TEST_USAGE_IN_DICT_2, TEST_USAGE_IN_DICT)
        == TEST_USAGE_IN_DICT_RESULT_3
    )


def test_speed():
    """Test speed calculator"""

    # Normal case
    assert calculators.speed(13, 5, 2) == 4
    # No time_delta
    assert calculators.speed(86, 49) == 0
    # Overflow test
    assert calculators.speed(6, 14, 2, 16) == 4
    assert calculators.speed(19, 2, 17, 32) == 1

    # Zero time_delta
    with pytest.raises(ZeroDivisionError):
        calculators.speed(174, 162, 0)
