"""Test AusRouter converters tools."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from unittest.mock import patch

import pytest

from asusrouter.tools import converters


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (None, None),  # Not a string
        (12, None),  # Not a string
        ("", None),  # Empty string
        ("  ", None),  # Empty string
        ("test", "test"),  # Normal string
        ("  test  ", "test"),  # Normal string
    ],
)
def test_clean_string(content, result):
    """Test clean_string method."""

    assert converters.clean_string(content) == result


def test_flatten_dict():
    """Test flatten_dict method."""

    nested_dict = {"a": {"b": {"c": 1}}, "d": {"e": 2}}
    expected_output = {"a_b_c": 1, "d_e": 2}
    assert converters.flatten_dict(nested_dict) == expected_output

    # Test with None input
    assert converters.flatten_dict(None) is None

    # Test with non-dict input
    assert converters.flatten_dict("not a dict") == {}  # type: ignore

    # Test with exclude parameter
    nested_dict = {"a": {"b": {"c": 1}}, "d": 2}
    expected_output = {"a_b": {"c": 1}, "d": 2}
    assert converters.flatten_dict(nested_dict, exclude="b") == expected_output


class EnumForTest(Enum):
    """Enum class."""

    A = 1
    B = 2


@pytest.mark.parametrize(
    "args, kwargs, expected_result",
    [
        # Single string - should return single value
        ("vpnc_unit", {"vpnc_unit": 1}, 1),
        ("vpnc_unit", {"arguments": {"vpnc_unit": 1}}, 1),
        # Tuple with single string - should return single value
        (("vpnc_unit",), {"vpnc_unit": 1}, 1),
        (("vpnc_unit",), {"arguments": {"vpnc_unit": 1}}, 1),
        # Tuple with multiple strings and all are found
        # - should return tuple with values
        (
            ("vpnc_unit", "vpnc_clientlist"),
            {"vpnc_unit": 1, "vpnc_clientlist": "list"},
            (1, "list"),
        ),
        # Tuple with multiple strings and not all are found
        # - should return tuple with values, missing values should be None
        (("vpnc_unit", "vpnc_clientlist"), {"vpnc_unit": 1}, (1, None)),
        # Args issues - should return None
        (None, {"vpnc_unit": 1}, None),
        (1, {"vpnc_unit": 1}, None),
    ],
)
def test_get_arguments(args, kwargs, expected_result):
    """Test _get_arguments."""

    # Get the result
    result = converters.get_arguments(args, **kwargs)

    # Check the result
    assert result == expected_result


def test_get_enum_key_by_value():
    """Test get_enum_key_by_value method."""

    assert (
        converters.get_enum_key_by_value(EnumForTest, 1, EnumForTest.B) == EnumForTest.A
    )
    assert (
        converters.get_enum_key_by_value(EnumForTest, 2, EnumForTest.A) == EnumForTest.B
    )
    assert (
        converters.get_enum_key_by_value(EnumForTest, 3, EnumForTest.A) == EnumForTest.A
    )
    with pytest.raises(ValueError):
        converters.get_enum_key_by_value(EnumForTest, 3)


def test_is_enum():
    """Test is_enum method."""

    class TestEnum(Enum):
        """Enum class."""

        A = 1
        B = 2

    class NotEnum:  # pylint: disable=too-few-public-methods
        """Not enum class."""

    assert converters.is_enum(TestEnum) is True
    assert converters.is_enum(NotEnum) is False

    # Test with non-class input
    assert converters.is_enum("not a class") is False
    assert converters.is_enum(None) is False


def test_list_from_dict():
    """Test list_from_dict method."""

    # Test with empty dict
    assert converters.list_from_dict({}) == []

    # Test with non-empty dict
    assert converters.list_from_dict({"a": 1, "b": 2}) == ["a", "b"]

    # Test with a list
    assert converters.list_from_dict(["a", "b"]) == ["a", "b"]

    # Test with non-dict input
    assert converters.list_from_dict("not a dict") == []  # type: ignore
    assert converters.list_from_dict(None) == []  # type: ignore


def test_nvram_get():
    """Test nvram_get method."""

    # Test with empty input
    assert converters.nvram_get(None) is None

    # Test with string input
    assert converters.nvram_get("test") == [("nvram_get", "test")]

    # Test with list input
    assert converters.nvram_get(["test1", "test2"]) == [
        ("nvram_get", "test1"),
        ("nvram_get", "test2"),
    ]

    # Test with other input
    assert converters.nvram_get(123) == [("nvram_get", "123")]  # type: ignore


def test_run_method():
    """Test run_method method."""

    # Test with empty input
    assert converters.run_method(None, None) is None

    # Test with non-list input
    assert converters.run_method("TEST", str.lower) == "test"

    # Test with list input
    assert converters.run_method("TEST", [str.lower, str.upper]) == "TEST"

    # Test with enum input
    class TestEnum(Enum):
        """Enum class."""

        A = 1
        B = 2

    assert converters.run_method(1, TestEnum) == TestEnum.A
    assert converters.run_method(2, TestEnum) == TestEnum.B
    assert converters.run_method(3, TestEnum) is None

    # Test with enum input with UNKNOWN
    class TestEnumWithUnknown(Enum):
        """Enum class."""

        UNKNOWN = -999
        A = 1
        B = 2

    assert converters.run_method(3, TestEnumWithUnknown) == TestEnumWithUnknown.UNKNOWN


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (None, None),  # Non-booleans
        ("", None),
        ("  ", None),
        ("unknown", None),
        ("test", None),
        ("  test  ", None),
        (False, False),  # False booleans
        (0, False),
        ("0", False),
        ("false", False),
        ("off", False),
        ("disabled", False),
        (True, True),  # True booleans
        (1, True),
        ("1", True),
        ("true", True),
        ("on", True),
        ("enabled", True),
    ],
)
def test_safe_bool(content, result):
    """Test safe_bool method."""

    assert converters.safe_bool(content) == result


@pytest.mark.parametrize(
    ("content", "result"),
    [
        ("2021-01-01   ", datetime(2021, 1, 1)),  # Date content
        ("2021-01-01 00:00:00", datetime(2021, 1, 1)),
        (None, None),  # None content
        ("", None),
        ("  ", None),
        ("unknown", None),  # Non-datetime content
        ("test", None),
        ("  test  ", None),
    ],
)
def test_safe_datetime(content, result):
    """Test safe_datetime method."""

    assert converters.safe_datetime(content) == result


def test_safe_exists():
    """Test safe_exists method."""

    assert converters.safe_exists("") is False
    assert converters.safe_exists("test") is True


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (1, 1.0),  # Number content
        (1.0, 1.0),
        ("1", 1.0),
        ("1.0", 1.0),
        (None, None),  # None content
        ("", None),
        ("  ", None),
        ("unknown", None),  # Non-number content
        ("test", None),
        ("  test  ", None),
    ],
)
def test_safe_float(content, result):
    """Test safe_float method."""

    assert converters.safe_float(content) == result


@pytest.mark.parametrize(
    ("content", "base", "result"),
    [
        (1, 10, 1),  # Integer content
        ("1", 10, 1),
        (1.0, 10, 1),  # Float content
        ("1.0", 10, 1),
        ("1.1", 10, 1),  # Float content with decimal
        ("1.9", 10, 1),
        (None, 10, None),  # None content
        ("", 10, None),
        ("  ", 10, None),
        ("unknown", 10, None),  # Non-number content
        ("test", 10, None),
        ("  test  ", 10, None),
        ("0x1", 16, 1),  # Hex content
        ("0xA", 16, 10),
        ("0xFF", 16, 255),
        ("0x100", 16, 256),
        ("0xabc", 16, 2748),
        ("0xABC", 16, 2748),
        ("0x2692247c7", 16, 10353788871),
        ("0x123456789ABCDEF", 16, 81985529216486895),
    ],
)
def test_safe_int(content, base, result):
    """Test safe_int method."""

    assert converters.safe_int(content, base=base) == result


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (None, []),  # None content
        ("test", ["test"]),  # Single value content
        (1, [1]),
        (1.0, [1.0]),
        (True, [True]),
        (False, [False]),
        ([], []),  # List content
        ([1, 2, 3], [1, 2, 3]),
    ],
)
def test_safe_list(content, result):
    """Test safe_list method."""

    assert converters.safe_list(content) == result


def test_safe_list_csv():
    """Test safe_list_csv method."""

    assert converters.safe_list_csv("test") == ["test"]
    assert converters.safe_list_csv("test1,test2") == ["test1", "test2"]


@pytest.mark.parametrize(
    ("content", "delimiter", "result"),
    [
        (None, None, []),  # Not a string
        (1, None, []),
        ({1: 2}, None, []),
        ("test", None, ["test"]),  # String
        ("test1 test2", None, ["test1", "test2"]),
        ("test1 test2", ";", ["test1 test2"]),  # Wrong delimiter
    ],
)
def test_safe_list_from_string(content, delimiter, result):
    """Test safe_list_from_string method."""

    assert converters.safe_list_from_string(content, delimiter) == result


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (None, None),  # None content
        (1, 1),  # Integer content
        (5.0, 5.0),  # Float content
        ([1, 2, 3], [1, 2, 3]),  # List content
        ({"a": 1}, {"a": 1}),  # Dictionary content
        ("test", "test"),  # String content
        ("   test   ", "test"),
        ("   ", None),  # Empty string content
        ("", None),
    ],
)
def test_safe_return(content, result):
    """Test safe_return method."""

    assert converters.safe_return(content) == result


@pytest.mark.parametrize(
    ("current", "previous", "time_delta", "result"),
    [
        (None, None, None, 0.0),
        (1, None, None, 0.0),
        (1, 1, None, 0.0),
        (1, 1, 0, 0.0),
        (1, 1, 1, 0.0),
        (1, 1, 2, 0.0),
        (1, 2, 1, 0.0),
        (2, 1, 1, 1.0),
        (4, 2, 2, 1.0),
    ],
)
def test_safe_speed(current, previous, time_delta, result):
    """Test safe_speed method."""

    assert converters.safe_speed(current, previous, time_delta) == result


@patch("asusrouter.tools.converters.datetime")
def test_safe_time_from_delta(mock_datetime):
    """Test safe_time_from_delta method."""

    # Set up the mock to return a specific datetime when now() is called
    mock_datetime.now.return_value = datetime(2023, 8, 15, tzinfo=timezone.utc)

    result = converters.safe_time_from_delta("48:00:15")  # 48 hours, 15 seconds
    expected = datetime(2023, 8, 12, 23, 59, 45, tzinfo=timezone.utc)
    assert result == expected


def test_safe_timedelta_long():
    """Test safe_timedelta_long method."""

    # Test with valid string
    assert converters.safe_timedelta_long("01:30:15   ") == timedelta(
        hours=1, minutes=30, seconds=15
    )
    assert converters.safe_timedelta_long("   30:15:27") == timedelta(
        hours=30, minutes=15, seconds=27
    )

    # Test with invalid string
    assert converters.safe_timedelta_long("invalid") == timedelta()

    # Test with None
    assert converters.safe_timedelta_long(None) == timedelta()


def test_safe_unpack_key():
    """Test safe_unpack_key method."""

    def test_method(content):
        """Test method."""

        return {"content": content}

    # Test with a key only
    result = converters.safe_unpack_key("key")
    assert result[0] == "key" and result[1] is None

    # Test with a key and a method
    result = converters.safe_unpack_key(("key", test_method))
    if result[1] is not None and not isinstance(result[1], list):
        assert result[0] == "key" and result[1](10) == test_method(10)
    elif result[1] is not None:
        assert result[0] == "key" and result[1][0](10) == test_method(10)
    else:
        assert result[0] == "key" and result[1] is None

    # Test with a key and a list of methods
    result = converters.safe_unpack_key(("key", [test_method, test_method]))
    if isinstance(result[1], list):
        assert (
            result[0] == "key"
            and result[1][0](10) == test_method(10)
            and result[1][1](10) == test_method(10)
        )

    # Test with a key and a non-method at index 1
    result = converters.safe_unpack_key(("key", 123))  # type: ignore
    assert result[0] == "key" and result[1] is None

    # Test with a tuple of one element
    result = converters.safe_unpack_key(("key",))
    assert result[0] == "key" and result[1] is None


def test_safe_unpack_keys():
    """Test safe_unpack_keys method."""

    def test_method(content):
        """Test method."""

        return {"content": content}

    # Test with a key, key_to_use and a method
    result = converters.safe_unpack_keys(("key", "key_to_use", test_method))
    assert (
        result[0] == "key"
        and result[1] == "key_to_use"
        and result[2](10) == test_method(10)
    )

    # Test with a key, key_to_use and a list of methods
    result = converters.safe_unpack_keys(
        ("key", "key_to_use", [test_method, test_method])
    )
    assert (
        result[0] == "key"
        and result[1] == "key_to_use"
        and result[2][0](10) == test_method(10)
        and result[2][1](10) == test_method(10)
    )

    # Test with a key and key_to_use only
    result = converters.safe_unpack_keys(("key", "key_to_use"))
    assert result[0] == "key" and result[1] == "key_to_use" and result[2] is None

    # Test with a key only
    result = converters.safe_unpack_keys("key")
    assert result[0] == "key" and result[1] == "key" and result[2] is None


@pytest.mark.parametrize(
    ("used", "total", "result"),
    [
        (5, 10, 50.0),  # normal usage
        (10, 10, 100.0),  # normal usage
        (3, 9, 33.33),  # round to 2 decimals
        (-1, 2, 0.0),  # negative usage not allowed
        (1, -2, 0.0),  # negative usage not allowed
        (-1, -1, 100.0),  # both negative values result in positive usage
        (1, 0, 0.0),  # zero total usage not allowed
        (0, 0, 0.0),  # zero total usage not allowed
    ],
)
def test_safe_usage(used, total, result):
    """Test safe_usage method."""

    assert converters.safe_usage(used, total) == result


@pytest.mark.parametrize(
    ("used", "total", "prev_used", "prev_total", "result"),
    [
        (10, 20, 5, 10, 50.0),  # normal usage
        (10, 20, 10, 20, 0.0),  # no usage
        (6, 18, 3, 9, 33.33),  # round to 2 decimals
        (5, 20, 10, 10, 0.0),  # invalid case when current used is less than previous
        (10, 20, 5, 25, 0.0),  # invalid case when current total is less than previous
        (5, 10, 10, 20, 0.0),  # invalid case when current values are less than previous
    ],
)
def test_safe_usage_historic(used, total, prev_used, prev_total, result):
    """Test safe_usage_historic method."""

    assert converters.safe_usage_historic(used, total, prev_used, prev_total) == result


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Actual timestamp in milliseconds
        (1700515143689, datetime(2023, 11, 20, 21, 19, 3, 689000, tzinfo=timezone.utc)),
        # None
        (None, None),
        # The beginning of the epoch
        (0, datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        # Random string
        ("test", None),
    ],
)
def test_safe_timestamp_to_utc(value, result):
    """Test safe_timestamp_to_utc method."""

    assert converters.safe_timestamp_to_utc(value) == result


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Actual datetime
        (
            datetime(2023, 11, 20, 21, 19, 3, 689000, tzinfo=timezone.utc),
            1700515143.689,
        ),
        # None
        (None, None),
        # The beginning of the epoch
        (datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 0),
        # Random string
        ("test", None),
    ],
)
def test_safe_utc_to_timestamp(value, result):
    """Test safe_utc_to_timestamp method."""

    assert converters.safe_utc_to_timestamp(value) == result


@pytest.mark.parametrize(
    ("value", "result"),
    [
        # Actual datetime
        (datetime(2023, 11, 20, 21, 19, 3, 689000, tzinfo=timezone.utc), 1700515143689),
        # None
        (None, None),
        # The beginning of the epoch
        (datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc), 0),
        # Random string
        ("test", None),
    ],
)
def test_safe_utc_to_timestamp_milli(value, result):
    """Test safe_utc_to_timestamp_milli method."""

    assert converters.safe_utc_to_timestamp_milli(value) == result
