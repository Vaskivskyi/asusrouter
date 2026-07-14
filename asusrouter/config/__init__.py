"""Configuration module for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
import threading
from typing import Any

from asusrouter.tools.converters import safe_datetime
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.security import ARSecurityLevel

# Sentinel for distinguishing "missing" from a stored None value.
_MISSING = object()


class ARConfigKeyBase(StrEnum):
    """Base configuration key class."""


class ARConfigKey(ARConfigKeyBase):
    """Configuration keys for AsusRouter."""

    # Optimistic data
    OPTIMISTIC_DATA = "optimistic_data"
    # Optimistic temperature
    OPTIMISTIC_TEMPERATURE = "optimistic_temperature"
    NOTIFIED_OPTIMISTIC_TEMPERATURE = "notified_optimistic_temperature"
    # Seed boot time; when set it anchors stabilization instead of fetching
    BOOTTIME = "boottime"
    # Robust boottime
    ROBUST_BOOTTIME = "robust_boottime"
    # Security level applied to logged data
    SECURITY_LEVEL_LOG = "security_level_log"
    # Security level applied to data exposed to consumers
    SECURITY_LEVEL_DATA = "security_level_data"


CONFIG_DEFAULT_BOOL: bool = False
CONFIG_DEFAULT_INT: int = 0
CONFIG_DEFAULT_ALREADY_NOTIFIED: bool = False


def safe_bool_config(value: Any) -> bool:
    """Convert a value to a boolean, defaulting to CONFIG_DEFAULT_BOOL."""

    config_value: bool | None = raw_to_bool(value)

    if config_value is None:
        return CONFIG_DEFAULT_BOOL

    return config_value


def safe_int_config(value: Any) -> int:
    """Convert a value to an integer, defaulting to CONFIG_DEFAULT_INT."""

    config_value: int | None = raw_to_int(value)

    if config_value is None:
        return CONFIG_DEFAULT_INT

    return config_value


def safe_datetime_config(value: Any) -> datetime | None:
    """Convert a value to a datetime (or parse a string), else None."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return safe_datetime(value)
    return None


CONFIG_DEFAULT: dict[ARConfigKey, Any] = {
    ARConfigKey.OPTIMISTIC_DATA: CONFIG_DEFAULT_BOOL,
    # If set, the temperature will be automatically adjusted
    # to fit the expected range
    ARConfigKey.OPTIMISTIC_TEMPERATURE: CONFIG_DEFAULT_BOOL,
    ARConfigKey.NOTIFIED_OPTIMISTIC_TEMPERATURE: CONFIG_DEFAULT_ALREADY_NOTIFIED,  # noqa: E501
    # If set, this boot time is used as the stabilization anchor instead
    # of fetching it on connect
    ARConfigKey.BOOTTIME: None,
    # If set, the boottime will be processed with 2 seconds
    # precision to avoid +- 1 second uncertainty in the raw data
    ARConfigKey.ROBUST_BOOTTIME: CONFIG_DEFAULT_BOOL,
    # Logs sanitize sensitive data by default
    ARConfigKey.SECURITY_LEVEL_LOG: ARSecurityLevel.SANITIZED,
    # Data exposes reasonably-sensitive values (MAC, IP) but not secrets
    ARConfigKey.SECURITY_LEVEL_DATA: ARSecurityLevel.REASONABLE,
}

TYPES_DEFAULT: dict[ARConfigKey, Callable[[Any], Any]] = {
    # Optimistic data
    ARConfigKey.OPTIMISTIC_DATA: safe_bool_config,
    # Optimistic temperature
    ARConfigKey.OPTIMISTIC_TEMPERATURE: safe_bool_config,
    ARConfigKey.NOTIFIED_OPTIMISTIC_TEMPERATURE: safe_bool_config,
    # Seed boot time
    ARConfigKey.BOOTTIME: safe_datetime_config,
    # Robust boottime
    ARConfigKey.ROBUST_BOOTTIME: safe_bool_config,
    # Security levels
    ARConfigKey.SECURITY_LEVEL_LOG: ARSecurityLevel.from_value,
    ARConfigKey.SECURITY_LEVEL_DATA: ARSecurityLevel.from_value,
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

        if not isinstance(key, ARConfigKeyBase):
            raise KeyError(
                f"Unknown configuration option: {key}. "
                "Register it before setting."
            )
        with self._lock:
            if key not in self._options:
                raise KeyError(
                    f"Unknown configuration option: {key}. "
                    "Register it before setting."
                )
            converter: Callable[[Any], Any] = self._types.get(
                key, safe_bool_config
            )
            self._options[key] = converter(value)

    def get(self, key: ARConfigKeyBase) -> Any:
        """Get the configuration option."""

        if not isinstance(key, ARConfigKeyBase):
            raise KeyError(f"Unknown configuration option: {key}")
        with self._lock:
            try:
                return self._options[key]
            except KeyError:
                raise KeyError(
                    f"Unknown configuration option: {key}"
                ) from None

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

    def ensure_notification_flag(self, key: ARConfigKeyBase) -> None:
        """Register a notification-flag key with its default if absent."""

        if key not in self:
            self.register(key)
            self.set(key, CONFIG_DEFAULT_ALREADY_NOTIFIED)

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

        # Prefer instance option, otherwise consult global config.
        # Single lookup via sentinel — a stored None must not fall through.
        with self._lock:
            value = self._options.get(key, _MISSING)

        if value is not _MISSING:
            return value

        # Defer to global configuration
        return ARConfig.get(key)

    def remove(self, key: ARConfigKeyBase) -> None:
        """Remove configuration option of the instance."""

        with self._lock:
            if key in self._options:
                self._options.pop(key, None)
                self._types.pop(key, None)
