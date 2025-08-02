"""Tests for the configuration module."""

from __future__ import annotations

import pytest
from asusrouter.config import CONFIG_DEFAULT_BOOL, ARConfig

KEYS_BOOL = [
    "optimistic_data",
]


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset the configuration before each test."""

    ARConfig.set("optimistic_data", CONFIG_DEFAULT_BOOL)


class TestBoolConfig:
    """Tests for boolean configuration options."""

    def test_keys(self) -> None:
        """Test that we can get the full list of configuration keys."""

        keys = ARConfig.keys()
        assert isinstance(keys, list)
        assert len(keys) > 0
        assert all(isinstance(key, str) for key in keys)

    @pytest.mark.parametrize("key", KEYS_BOOL)
    def test_default_bool(self, key: str) -> None:
        """Test the default value of a boolean configuration key."""

        assert ARConfig.get(key) is CONFIG_DEFAULT_BOOL

    @pytest.mark.parametrize("key", KEYS_BOOL)
    @pytest.mark.parametrize("value", [True, False])
    def test_set_bool(self, key: str, value: bool) -> None:
        """Test setting a boolean configuration key."""

        ARConfig.set(key, value)
        assert ARConfig.get(key) is value

    def test_get_optimistic_data(self) -> None:
        """Test that we can get the value of optimistic_data."""

        assert ARConfig.optimistic_data is CONFIG_DEFAULT_BOOL

    def test_unknown_key(self) -> None:
        """Test that setting/getting an unknown key raises KeyError."""

        with pytest.raises(KeyError):
            ARConfig.set("unknown_option", True)

        with pytest.raises(KeyError):
            ARConfig.get("unknown_option")
