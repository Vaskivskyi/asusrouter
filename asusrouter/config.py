"""Configuration module for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
import threading
from typing import Any

from asusrouter.tools.converters import safe_bool, safe_int
from asusrouter.tools.security import ARSecurityLevel


class ARConfigKeyBase(StrEnum):
    """Base configuration key class."""


class ARConfigKey(ARConfigKeyBase):
    """Configuration keys for AsusRouter."""

    # Debug payload
    DEBUG_PAYLOAD = "debug_payload"
    # Optimistic data
    OPTIMISTIC_DATA = "optimistic_data"
    # Optimistic temperature
    OPTIMISTIC_TEMPERATURE = "optimistic_temperature"
    NOTIFIED_OPTIMISTIC_TEMPERATURE = "notified_optimistic_temperature"
    # Robust boottime
    ROBUST_BOOTTIME = "robust_boottime"


CONFIG_DEFAULT_BOOL: bool = False
CONFIG_DEFAULT_INT: int = 0
CONFIG_DEFAULT_ALREADY_NOTIFIED: bool = False


def safe_bool_config(value: Any) -> bool:
    """Convert a value to a boolean, defaulting to CONFIG_DEFAULT_BOOL."""

    config_value: bool | None = safe_bool(value)

    if config_value is None:
        return CONFIG_DEFAULT_BOOL

    return config_value


def safe_int_config(value: Any) -> int:
    """Convert a value to an integer, defaulting to CONFIG_DEFAULT_INT."""

    config_value: int | None = safe_int(value)

    if config_value is None:
        return CONFIG_DEFAULT_INT

    return config_value


CONFIG_DEFAULT: dict[ARConfigKey, Any] = {
    # If set, payload sent to the router will be available
    # in the debug logs
    ARConfigKey.DEBUG_PAYLOAD: ARSecurityLevel.DEFAULT,
    ARConfigKey.OPTIMISTIC_DATA: CONFIG_DEFAULT_BOOL,
    # If set, the temperature will be automatically adjusted
    # to fit the expected range
    ARConfigKey.OPTIMISTIC_TEMPERATURE: CONFIG_DEFAULT_BOOL,
    ARConfigKey.NOTIFIED_OPTIMISTIC_TEMPERATURE: CONFIG_DEFAULT_ALREADY_NOTIFIED,  # noqa: E501
    # If set, the boottime will be processed with 2 seconds
    # precision to avoid +- 1 second uncertainty in the raw data.
    ARConfigKey.ROBUST_BOOTTIME: CONFIG_DEFAULT_BOOL,
}

TYPES_DEFAULT: dict[ARConfigKey, Callable[[Any], Any]] = {
    # Debug payload
    ARConfigKey.DEBUG_PAYLOAD: ARSecurityLevel.from_value,
    # Optimistic data
    ARConfigKey.OPTIMISTIC_DATA: safe_bool_config,
    # Optimistic temperature
    ARConfigKey.OPTIMISTIC_TEMPERATURE: safe_bool_config,
    ARConfigKey.NOTIFIED_OPTIMISTIC_TEMPERATURE: safe_bool_config,
    # Robust boottime
    ARConfigKey.ROBUST_BOOTTIME: safe_bool_config,
}


class ARConfigBase:
    """Base class for configuration options."""

    def __init__(self) -> None:
        """Initialize the base configuration."""

        self._lock = threading.Lock()
        self._options: dict[ARConfigKeyBase, Any] = {}
        self._types: dict[ARConfigKeyBase, Callable[[Any], Any]] = {}

    def set(self, key: ARConfigKeyBase, value: Any) -> None:
        """Set the configuration option."""

        with self._lock:
            if isinstance(key, ARConfigKeyBase) and key in self._options:
                converter: Callable[[Any], Any] = self._types.get(
                    key, safe_bool_config
                )
                self._options[key] = converter(value)
            else:
                raise KeyError(
                    f"Unknown configuration option: {key}. "
                    "Register it before setting."
                )

    def get(self, key: ARConfigKeyBase) -> Any:
        """Get the configuration option."""

        with self._lock:
            if isinstance(key, ARConfigKeyBase) and key in self._options:
                return self._options[key]
            raise KeyError(f"Unknown configuration option: {key}")

    def keys(self) -> list[ARConfigKeyBase]:
        """Get the list of configuration keys."""

        with self._lock:
            return list(self._options.keys())

    def list(self) -> list[tuple[ARConfigKeyBase, Any]]:
        """List all configuration options."""

        with self._lock:
            return list(self._options.items())

    def reset(self) -> None:
        """Reset all configuration options to their default values."""

        with self._lock:
            self._options = {}
            self._types = {}

    def register(
        self,
        key: ARConfigKeyBase,
        converter: Callable[[Any], Any] | None = None,
    ) -> None:
        """Register a custom converter for a config key."""

        if not isinstance(key, ARConfigKeyBase):
            raise KeyError(f"Unknown configuration key: {key}")

        if not converter:
            converter = safe_bool_config

        with self._lock:
            self._types[key] = converter
            self._options[key] = converter(None)

    def __contains__(self, key: ARConfigKeyBase) -> bool:
        """Check if a configuration key exists."""

        with self._lock:
            return key in self._options

    @property
    def types(self) -> dict[ARConfigKeyBase, Callable[[Any], Any]]:
        """Get the dictionary of configuration types."""

        with self._lock:
            return self._types.copy()


class ARGlobalConfig(ARConfigBase):
    """Configuration class for AsusRouter."""

    def __init__(
        self,
        defaults: dict[ARConfigKey, Any] | None = None,
    ) -> None:
        """Initialize the configuration."""

        super().__init__()
        self.reset(defaults)

    def reset(
        self,
        defaults: dict[ARConfigKey, Any] | None = None,
    ) -> None:
        """Reset all configuration options."""

        super().reset()

        with self._lock:
            defaults = defaults or CONFIG_DEFAULT
            for key in ARConfigKey:
                self._options[key] = defaults.get(key)
                self._types[key] = TYPES_DEFAULT.get(key, safe_bool_config)


ARConfig: ARGlobalConfig = ARGlobalConfig()


class ARInstanceConfig(ARConfigBase):
    """Configuration class for AsusRouter instances.

    These configurations are used to overwrite the global configuration.
    If the search key is present in the instance configuration, AR will
    use it when needed.
    """

    def __init__(self, defaults: dict[ARConfigKey, Any] | None = None) -> None:
        """Initialize the instance configuration."""

        super().__init__()
        self.reset(defaults)

    def reset(self, defaults: dict[ARConfigKey, Any] | None = None) -> None:
        """Reset all configuration options using the provided defaults.

        This method removes all the existing configuration options
        and converters. The new defaults will be checked to have a valid
        type converter. If a converter is found, the value will be written
        after the conversion.

        Any key with an unknown default converter will be considered a boolean.
        For any custom converter, it must be registered separately using
        the `register_type` method after initialization of the key.
        """

        super().reset()

        with self._lock:
            defaults = defaults or {}
            for key, value in defaults.items():
                # Make sure, this is a valid key
                if key in ARConfigKey:
                    # Check if a default converter is available
                    converter: Callable[[Any], Any] = TYPES_DEFAULT.get(
                        key, safe_bool_config
                    )

                    # Save the converter
                    self._types[key] = converter

                    # Safe apply the value
                    self._options[key] = converter(value)

    def get(self, key: ARConfigKeyBase) -> Any:
        """Get configuration option of the instance.

        This method falls back to global ARConfig if not present.
        """

        # Prefer instance option, otherwise consult global config
        with self._lock:
            if key in self._options:
                return self._options[key]

        # Defer to global configuration
        return ARConfig.get(key)

    def remove(self, key: ARConfigKeyBase) -> None:
        """Remove configuration option of the instance."""

        with self._lock:
            if key in self._options:
                self._options.pop(key, None)
                self._types.pop(key, None)
