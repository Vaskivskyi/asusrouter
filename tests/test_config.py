"""Tests for the configuration module."""

from __future__ import annotations

import concurrent.futures
import random
from typing import Any

import pytest

from asusrouter.config import (
    CONFIG_DEFAULT_BOOL,
    CONFIG_DEFAULT_INT,
    TYPES_DEFAULT,
    ARConfig,
    ARConfigKey as ARConfKey,
    safe_bool_config,
    safe_int_config,
)
from asusrouter.connection_config import (
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)

KEYS_BOOL = [
    ARConfKey.OPTIMISTIC_DATA,
    ARConfKey.OPTIMISTIC_TEMPERATURE,
    ARConfKey.ROBUST_BOOTTIME,
]

KEYS_INT = [
    ARCCKey.PORT,
]


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset the configuration before each test."""

    ARConfig.set(ARConfKey.OPTIMISTIC_DATA, CONFIG_DEFAULT_BOOL)
    ARConfig.set(ARConfKey.OPTIMISTIC_TEMPERATURE, CONFIG_DEFAULT_BOOL)
    ARConfig.set(ARConfKey.ROBUST_BOOTTIME, CONFIG_DEFAULT_BOOL)


class TestConfig:
    """Tests for the ARConfig class."""

    def test_custom_defaults(self) -> None:
        """Test that custom defaults can be set and retrieved correctly."""

        custom = {ARConfKey.OPTIMISTIC_DATA: True}
        config = type(ARConfig)(custom)
        assert config.get(ARConfKey.OPTIMISTIC_DATA) is True

    @pytest.mark.parametrize(
        "wrong_key",
        [
            "unknown_option",
            12345,
            ["a", "b"],
            object(),
            None,
        ],
    )
    def test_wrong_key(self, wrong_key: Any) -> None:
        """Test that setting/getting an unknown key raises KeyError."""

        with pytest.raises(KeyError):
            ARConfig.set(wrong_key, True)

        with pytest.raises(KeyError):
            ARConfig.get(wrong_key)

    def test_contains(self) -> None:
        """Test the __contains__ method for ARConfig."""

        for key in KEYS_BOOL:
            assert key in ARConfig
        assert "not_a_key" not in ARConfig  # type: ignore[operator]

    def test_keys(self) -> None:
        """Test that we can get the full list of configuration keys."""

        keys = ARConfig.keys()
        assert isinstance(keys, list)
        assert len(keys) > 0
        assert all(isinstance(key, ARConfKey) for key in keys)

    def test_keys_immutable(self) -> None:
        """Test that the keys list is immutable."""

        keys = ARConfig.keys()
        keys.append("something")  # type: ignore[arg-type]
        assert all(isinstance(key, ARConfKey) for key in ARConfig.keys())  # noqa: SIM118

    def test_keys_returns_all_enum_members(self) -> None:
        """Test that ARConfig.keys() returns all members of ARConfKey."""

        keys = set(ARConfig.keys())
        enum_keys = set(ARConfKey)
        assert keys == enum_keys

    def test_list(self) -> None:
        """Test that we can get the full list of configuration options set."""

        options = ARConfig.list()
        assert isinstance(options, list)
        assert len(options) > 0
        assert all(
            isinstance(option, tuple) and len(option) == 2  # noqa: PLR2004
            for option in options
        )

    def test_types(self) -> None:
        """Test that we can get the types of configuration keys."""

        types = ARConfig.types
        assert isinstance(types, dict)
        assert len(types) > 0
        assert all(isinstance(key, ARConfKey) for key in types)
        assert all(callable(converter) for converter in types.values())


class TestRegister:
    """Tests for the register method of ARConfig."""

    def test_register(self) -> None:
        """Test that we can register a new type for a configuration key."""

        def int_to_bool(val: Any) -> bool:
            """Convert a string to an integer to a boolean."""

            if not val:
                return CONFIG_DEFAULT_BOOL

            return bool(int(val))

        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, int_to_bool)
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, 1)
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is True
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, 0)
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is False

        # Restore original converter for cleanliness
        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, safe_bool_config)

    def test_register_overwrites_existing(self) -> None:
        """Test that register overwrites an existing converter."""

        def always_true(val: Any) -> bool:
            return True

        def always_false(val: Any) -> bool:
            return False

        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, always_true)
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, "anything")
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is True

        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, always_false)
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, "anything")
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is False

        # Restore original converter
        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, safe_bool_config)

    def test_register_unknown_key(self) -> None:
        """Test that register raises KeyError for unknown keys."""

        class FakeKey:
            pass

        with pytest.raises(KeyError):
            ARConfig.register(FakeKey(), lambda x: x)  # type: ignore[arg-type]

    def test_register_no_converter(self) -> None:
        """Test that register with no converter uses boolean conversion."""

        ARConfig.register(ARConfKey.OPTIMISTIC_DATA, None)
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, 1)
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is True
        ARConfig.set(ARConfKey.OPTIMISTIC_DATA, 0)
        assert ARConfig.get(ARConfKey.OPTIMISTIC_DATA) is False


class TestReset:
    """Tests for the reset method of ARConfig."""

    def test_reset(self) -> None:
        """Test that reset restores all configuration options and types."""

        # Change all values
        for key in KEYS_BOOL:
            ARConfig.set(key, not CONFIG_DEFAULT_BOOL)
            assert ARConfig.get(key) is not CONFIG_DEFAULT_BOOL

        # Change a type
        for key in KEYS_BOOL:
            ARConfig.register(key, lambda x: not x)
            assert ARConfig.get(key) is not CONFIG_DEFAULT_BOOL

        # Reset to defaults
        ARConfig.reset()
        for key in KEYS_BOOL:
            assert ARConfig.get(key) is CONFIG_DEFAULT_BOOL
            assert ARConfig.types[key] is TYPES_DEFAULT[key]


class TestThreadSafety:
    """Tests for thread safety of ARConfig."""

    def test_set_and_get(self) -> None:
        """Test thread safety for set and get."""

        def set_and_get(key: ARConfKey, val: Any) -> Any:
            """Set a value and return it."""

            ARConfig.set(key, val)
            return key, ARConfig.get(key)

        # Prepare a list of (key, value) pairs
        tasks = [
            (random.choice(KEYS_BOOL), random.choice([True, False]))  # noqa: S311
            for _ in range(100)
        ]

        # Run many concurrent set/get operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda kv: set_and_get(*kv), tasks))

        # Check that all results are as expected
        for (key, expected_val), (result_key, result_val) in zip(
            tasks, results
        ):
            assert key == result_key
            assert result_val == expected_val

    def test_register(self) -> None:
        """Test thread safety for register."""

        def register() -> None:
            """Register a type."""
            ARConfig.register(ARConfKey.OPTIMISTIC_DATA, safe_bool_config)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register) for _ in range(20)]
            for f in futures:
                f.result()

    def test_reset(self) -> None:
        """Test thread safety for reset."""

        def reset_config() -> None:
            """Reset the configuration."""
            ARConfig.reset()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(reset_config) for _ in range(20)]
            for f in futures:
                f.result()


class TestConvert:
    """Tests for the configuration conversion functions."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            (1, True),
            (0, False),
            ("1", True),
            ("0", False),
            ("string", False),
            (None, False),
        ],
    )
    def test_safe_bool_config(self, value: Any, expected: bool) -> None:
        """Test that safe_bool_config converts values correctly."""

        assert safe_bool_config(value) is expected

    def test_safe_bool_config_default(self) -> None:
        """Test that safe_bool_config returns default when value is None."""

        assert safe_bool_config(None) is CONFIG_DEFAULT_BOOL

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (1, 1),
            (0, 0),
            ("1", 1),
            ("0", 0),
            ("string", 0),
            (None, 0),
        ],
    )
    def test_safe_int_config(self, value: Any, expected: int) -> None:
        """Test that safe_int_config converts values correctly."""

        assert safe_int_config(value) == expected

    def test_safe_int_config_default(self) -> None:
        """Test that safe_int_config returns default when value is None."""

        assert safe_int_config(None) == CONFIG_DEFAULT_INT


class TestBoolConfig:
    """Tests for boolean configuration options."""

    @pytest.mark.parametrize("key", KEYS_BOOL)
    def test_default_bool(self, key: ARConfKey) -> None:
        """Test the default value of a boolean configuration key."""

        assert ARConfig.get(key) is CONFIG_DEFAULT_BOOL

    @pytest.mark.parametrize("key", KEYS_BOOL)
    @pytest.mark.parametrize("value", [True, False])
    def test_set_bool(self, key: ARConfKey, value: bool) -> None:
        """Test setting a boolean configuration key."""

        ARConfig.set(key, value)
        assert ARConfig.get(key) is value


class TestIntConfig:
    """Tests for integer configuration options."""

    @pytest.mark.parametrize("key", KEYS_INT)
    def test_default_int(self, key: ARConfKey) -> None:
        """Test the default value of an integer configuration key."""

        configs = ARConnectionConfig()
        assert configs.get(key) is CONFIG_DEFAULT_INT

    @pytest.mark.parametrize("key", KEYS_INT)
    @pytest.mark.parametrize("value", [1, 2, 3])
    def test_set_int(self, key: ARConfKey, value: int) -> None:
        """Test setting an integer configuration key."""

        configs = ARConnectionConfig()
        configs.set(key, value)
        assert configs.get(key) is value
