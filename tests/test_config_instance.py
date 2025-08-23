"""Test for the configuration module / Instance."""

import pytest

from asusrouter.config import (
    CONFIG_DEFAULT,
    CONFIG_DEFAULT_BOOL,
    ARConfig,
    ARConfigKey as ARConfKey,
    ARInstanceConfig,
    safe_bool_config,
)

TEST_INSTANCE_DEFAULT_BOOL = not CONFIG_DEFAULT_BOOL
TEST_INSTANCE_DEFAULTS = {
    ARConfKey.OPTIMISTIC_TEMPERATURE: TEST_INSTANCE_DEFAULT_BOOL
}


@pytest.fixture(autouse=True)
def reset_global() -> None:
    """Reset the configuration before each test."""

    ARConfig.set(ARConfKey.OPTIMISTIC_DATA, CONFIG_DEFAULT_BOOL)
    ARConfig.set(ARConfKey.OPTIMISTIC_TEMPERATURE, CONFIG_DEFAULT_BOOL)
    ARConfig.set(ARConfKey.ROBUST_BOOTTIME, CONFIG_DEFAULT_BOOL)


class TestInstance:
    """Tests for the empty instance configuration."""

    def test_reset(self) -> None:
        """Test resetting the instance configuration."""

        inst = ARInstanceConfig(TEST_INSTANCE_DEFAULTS)

        # Instance value applied
        assert (
            inst.get(ARConfKey.OPTIMISTIC_TEMPERATURE)
            is TEST_INSTANCE_DEFAULT_BOOL
        )

        # Make sure that it did not change the global config
        assert ARConfig.get(
            ARConfKey.OPTIMISTIC_TEMPERATURE
        ) is CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)

    def test_get(self) -> None:
        """Test getting the instance configuration."""

        inst = ARInstanceConfig()

        # Global value is returned
        assert inst.get(
            ARConfKey.OPTIMISTIC_TEMPERATURE
        ) is CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)

    def test_remove(self) -> None:
        """Test removing the instance configuration."""

        inst = ARInstanceConfig(TEST_INSTANCE_DEFAULTS)

        # Remove instance configuration
        inst.remove(ARConfKey.OPTIMISTIC_TEMPERATURE)

        # Global value is returned
        assert inst.get(
            ARConfKey.OPTIMISTIC_TEMPERATURE
        ) is CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)

    def test_set_nonexistent(self) -> None:
        """Test setting a non-existent instance configuration."""

        inst = ARInstanceConfig()

        # Set a non-existent configuration
        with pytest.raises(KeyError, match="Register it before setting."):
            inst.set(ARConfKey.OPTIMISTIC_TEMPERATURE, True)

        # Global value is returned
        assert inst.get(
            ARConfKey.OPTIMISTIC_TEMPERATURE
        ) is CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)

    def test_register_and_set(self) -> None:
        """Test registering and setting an instance configuration."""

        inst = ARInstanceConfig()

        # Register a new configuration option
        inst.register(ARConfKey.OPTIMISTIC_TEMPERATURE, safe_bool_config)

        # Set the instance configuration
        inst.set(ARConfKey.OPTIMISTIC_TEMPERATURE, TEST_INSTANCE_DEFAULT_BOOL)

        # Instance value is returned
        assert (
            inst.get(ARConfKey.OPTIMISTIC_TEMPERATURE)
            is TEST_INSTANCE_DEFAULT_BOOL
        )

        # Global value is unchanged
        assert ARConfig.get(
            ARConfKey.OPTIMISTIC_TEMPERATURE
        ) is CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)

    def test_register_does_not_change_global(self) -> None:
        """Test registering a configuration does influence global config."""

        inst = ARInstanceConfig()
        key = ARConfKey.OPTIMISTIC_TEMPERATURE

        # Register a new configuration option
        inst.register(key, safe_bool_config)

        # Global value is returned
        assert inst.get(key) is CONFIG_DEFAULT.get(key)

    def test_global_dynamic(self) -> None:
        """Test that global dynamic changes are reflected."""

        inst = ARInstanceConfig()

        global_default = CONFIG_DEFAULT.get(ARConfKey.OPTIMISTIC_TEMPERATURE)
        global_not_default = not global_default

        # Global value is returned
        assert inst.get(ARConfKey.OPTIMISTIC_TEMPERATURE) is global_default

        # Change the global configuration
        ARConfig.set(ARConfKey.OPTIMISTIC_TEMPERATURE, global_not_default)

        # Instance reflects the global change
        assert inst.get(ARConfKey.OPTIMISTIC_TEMPERATURE) is global_not_default

    def test_instance_independence(self) -> None:
        """Test that instance configurations are independent."""

        inst1 = ARInstanceConfig(TEST_INSTANCE_DEFAULTS)
        inst2 = ARInstanceConfig(TEST_INSTANCE_DEFAULTS)

        # Change instance 1 configuration
        inst1.set(
            ARConfKey.OPTIMISTIC_TEMPERATURE, not TEST_INSTANCE_DEFAULT_BOOL
        )

        # Instance 1 reflects the change
        assert (
            inst1.get(ARConfKey.OPTIMISTIC_TEMPERATURE)
            is not TEST_INSTANCE_DEFAULT_BOOL
        )

        # Instance 2 is unaffected
        assert (
            inst2.get(ARConfKey.OPTIMISTIC_TEMPERATURE)
            is TEST_INSTANCE_DEFAULT_BOOL
        )
