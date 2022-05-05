"""Test AsusRouter converters module"""

import pytest
from datetime import datetime, timedelta

from asusrouter.util import converters


def test_int_from_str():
    """Test string to integer convertion"""

    # base 10
    assert converters.int_from_str("17") == 17
    assert converters.int_from_str("-42") == -42
    assert converters.int_from_str("16", 16) == 22
    # base 16
    assert converters.int_from_str("ff", 16) == 255
    assert converters.int_from_str("0xaa", 16) == 170
    # Empty string
    assert converters.int_from_str(" ", 16) == 0

    # Not a string
    with pytest.raises(ValueError):
        converters.int_from_str(10)
    with pytest.raises(ValueError):
        converters.int_from_str(94.256)
    # Not an integer string
    with pytest.raises(ValueError):
        converters.int_from_str("4.5")


def test_float_from_str():
    """Test string to float convertion"""

    # Floats, ints and spaces
    assert converters.float_from_str("17.69") == 17.69
    assert converters.float_from_str("-91.4  ") == -91.4
    assert converters.float_from_str("  1") == 1.0
    # Empty string
    assert converters.float_from_str("   ") == 0.0

    # Not a string
    with pytest.raises(ValueError):
        converters.float_from_str(4.5)


def test_bool_from_any():
    """Test any to bool convertion"""

    # Numbers
    assert converters.bool_from_any(0) == False
    assert converters.bool_from_any(13) == True
    assert converters.bool_from_any(-97.5) == True
    # Strings
    assert converters.bool_from_any("FaLsE") == False
    assert converters.bool_from_any("trUE") == True
    assert converters.bool_from_any("   0") == False
    assert converters.bool_from_any(" 1 ") == True

    # Unknown strings
    with pytest.raises(ValueError):
        converters.bool_from_any("00")
    with pytest.raises(ValueError):
        converters.bool_from_any("fake_string")
    # Unknown types
    with pytest.raises(ValueError):
        converters.bool_from_any(datetime.utcnow())


def test_none_or_str():
    """None or string convertion"""

    # Empty strings
    assert converters.none_or_str("") == None
    assert converters.none_or_str("     ") == None
    # Usual strings
    assert converters.none_or_str("The Machine") == "The Machine"
    assert converters.none_or_str("  You are being watched  ") == "You are being watched"

    # Not strings
    with pytest.raises(ValueError):
        converters.none_or_str(-12.4)
    with pytest.raises(ValueError):
        converters.none_or_str(5356295141)
    with pytest.raises(ValueError):
        converters.none_or_str(datetime.utcnow())


def test_timedelta_long():
    """Test long timedelta convertion"""

    # Normal strings
    assert converters.timedelta_long("32:15:07") == timedelta(hours = 32, minutes = 15, seconds = 7)
    # Strings with spaces
    assert converters.timedelta_long("  6:32:13 ") == timedelta(hours = 6, minutes = 32, seconds = 13)

    # Not strings
    with pytest.raises(ValueError):
        converters.timedelta_long(10)



