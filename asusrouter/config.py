"""Configuration module for AsusRouter."""

from __future__ import annotations

import threading
from enum import StrEnum
from typing import Any, Callable, Dict, Optional

from asusrouter.tools.converters import safe_bool


class ARConfigKey(StrEnum):
    """Configuration keys for AsusRouter."""

    OPTIMISTIC_DATA = "optimistic_data"
    OPTIMISTIC_TEMPERATURE = "optimistic_temperature"
    ROBUST_BOOTTIME = "robust_boottime"


CONFIG_DEFAULT_BOOL: bool = False


def safe_bool_config(value: Any) -> bool:
    """Convert a value to a boolean, defaulting to CONFIG_DEFAULT_BOOL."""

    config_value: Optional[bool] = safe_bool(value)

    if config_value is None:
        return CONFIG_DEFAULT_BOOL

    return config_value


CONFIG_DEFAULT: Dict[ARConfigKey, Any] = {
    ARConfigKey.OPTIMISTIC_DATA: CONFIG_DEFAULT_BOOL,
    ARConfigKey.OPTIMISTIC_TEMPERATURE: CONFIG_DEFAULT_BOOL,
    # If set, the boottime will be processed with 2 seconds
    # precision to avoid +- 1 second uncertainty in the raw data.
    ARConfigKey.ROBUST_BOOTTIME: CONFIG_DEFAULT_BOOL,
}

TYPES_DEFAULT: Dict[ARConfigKey, Callable[[Any], Any]] = {
    ARConfigKey.OPTIMISTIC_DATA: safe_bool_config,
    ARConfigKey.OPTIMISTIC_TEMPERATURE: safe_bool_config,
    ARConfigKey.ROBUST_BOOTTIME: safe_bool_config,
}


class Config:
    """Configuration class for AsusRouter."""

    def __init__(
        self, defaults: Optional[Dict[ARConfigKey, Any]] = None
    ) -> None:
        """Initialize the configuration."""

        self._lock = threading.Lock()

        defaults = defaults or CONFIG_DEFAULT
        self._options: Dict[ARConfigKey, Any] = {
            key: defaults.get(key, None) for key in ARConfigKey
        }
        self._types: Dict[ARConfigKey, Callable[[Any], Any]] = {
            key: TYPES_DEFAULT.get(key, safe_bool_config)
            for key in ARConfigKey
        }

    def set(self, key: ARConfigKey, value: Any) -> None:
        """Set the configuration option."""

        with self._lock:
            if isinstance(key, ARConfigKey) and key in self._options:
                converter: Callable[[Any], Any] = self._types.get(
                    key, safe_bool_config
                )
                self._options[key] = converter(value)
            else:
                raise KeyError(f"Unknown configuration option: {key}")

    def get(self, key: ARConfigKey) -> Any:
        """Get the configuration option."""

        with self._lock:
            if isinstance(key, ARConfigKey) and key in self._options:
                return self._options[key]
            else:
                raise KeyError(f"Unknown configuration option: {key}")

    def keys(self) -> list[ARConfigKey]:
        """Get the list of configuration keys."""

        with self._lock:
            return list(self._options.keys())

    def reset(self) -> None:
        """Reset all configuration options to their default values."""

        with self._lock:
            for key in ARConfigKey:
                self._options[key] = CONFIG_DEFAULT.get(key, None)
                self._types[key] = TYPES_DEFAULT.get(key, safe_bool_config)

    def register_type(
        self, key: ARConfigKey, converter: Callable[[Any], Any]
    ) -> None:
        """Register a custom converter for a config key."""

        if not isinstance(key, ARConfigKey):
            raise KeyError(f"Unknown configuration key: {key}")

        with self._lock:
            self._types[key] = converter

    def __contains__(self, key: ARConfigKey) -> bool:
        """Check if a configuration key exists."""

        return key in self._options

    @property
    def types(self) -> Dict[ARConfigKey, Callable[[Any], Any]]:
        """Get the dictionary of configuration types."""

        with self._lock:
            return self._types.copy()


ARConfig: Config = Config()
