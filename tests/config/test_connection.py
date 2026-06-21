"""Tests for the configuration package — ARConnectionConfig."""

from __future__ import annotations

import pytest

from asusrouter.config import CONFIG_DEFAULT_BOOL, CONFIG_DEFAULT_INT
from asusrouter.config.connection import (
    CONNECTION_CONFIG_DEFAULT,
    ARConnectionConfig,
    ARConnectionConfigKey as ARCCKey,
)

KEYS_INT = [
    ARCCKey.PORT,
]


class TestConnectionDefaults:
    """Tests for ARConnectionConfig default values and reset."""

    def test_all_keys_present(self) -> None:
        """Every ARConnectionConfigKey is registered after init."""

        config = ARConnectionConfig()
        for key in ARCCKey:
            assert key in config

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            (ARCCKey.ALLOW_FALLBACK, CONFIG_DEFAULT_BOOL),
            (ARCCKey.ALLOW_MULTIPLE_FALLBACKS, CONFIG_DEFAULT_BOOL),
            (ARCCKey.ALLOW_UPGRADE_HTTP_TO_HTTPS, True),
            (ARCCKey.PORT, CONFIG_DEFAULT_INT),
            (ARCCKey.STRICT_SSL, CONFIG_DEFAULT_BOOL),
            (ARCCKey.USE_SSL, CONFIG_DEFAULT_BOOL),
            (ARCCKey.VERIFY_SSL, CONFIG_DEFAULT_BOOL),
        ],
    )
    def test_default_value(self, key: ARCCKey, expected: object) -> None:
        """Each key resolves to its documented default."""

        config = ARConnectionConfig()
        assert config.get(key) == expected

    def test_custom_defaults(self) -> None:
        """Custom defaults override the built-in connection defaults."""

        config = ARConnectionConfig({ARCCKey.USE_SSL: True})
        assert config.get(ARCCKey.USE_SSL) is True

    def test_defaults_match_constant(self) -> None:
        """Built-in defaults equal CONNECTION_CONFIG_DEFAULT."""

        config = ARConnectionConfig()
        for key, expected in CONNECTION_CONFIG_DEFAULT.items():
            assert config.get(key) == expected


class TestIntConfig:
    """Tests for integer configuration options."""

    @pytest.mark.parametrize("key", KEYS_INT)
    def test_default_int(self, key: ARCCKey) -> None:
        """Test the default value of an integer configuration key."""

        configs = ARConnectionConfig()
        assert configs.get(key) is CONFIG_DEFAULT_INT

    @pytest.mark.parametrize("key", KEYS_INT)
    @pytest.mark.parametrize("value", [1, 2, 3])
    def test_set_int(self, key: ARCCKey, value: int) -> None:
        """Test setting an integer configuration key."""

        configs = ARConnectionConfig()
        configs.set(key, value)
        assert configs.get(key) is value
