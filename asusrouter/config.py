"""Configuration module for AsusRouter."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from asusrouter.tools.converters import safe_bool

CONFIG_DEFAULT_BOOL: bool = False


def safe_bool_config(value: Any) -> bool:
    """Convert a value to a boolean, defaulting to CONFIG_DEFAULT_BOOL."""

    config_value: Optional[bool] = safe_bool(value)

    if config_value is None:
        return CONFIG_DEFAULT_BOOL

    return config_value


class Config:
    """Configuration class for AsusRouter."""

    def __init__(self) -> None:
        """Initialize the configuration."""

        self._lock = threading.Lock()

        self._options: Dict[str, Any] = {
            "optimistic_data": CONFIG_DEFAULT_BOOL,
        }
        self._types: Dict[str, Callable[[Any], Any]] = {}

    def set(self, key: str, value: Any) -> None:
        """Set the configuration option."""

        with self._lock:
            if key in self._options:
                converter: Callable[[Any], Any] = self._types.get(
                    key, safe_bool_config
                )
                self._options[key] = converter(value)
            else:
                raise KeyError(f"Unknown configuration option: {key}")

    def get(self, key: str) -> Any:
        """Get the configuration option."""

        with self._lock:
            if key in self._options:
                return self._options[key]
            else:
                raise KeyError(f"Unknown configuration option: {key}")

    def keys(self) -> list[str]:
        """Get the list of configuration keys."""

        with self._lock:
            return list(self._options.keys())

    @property
    def optimistic_data(self) -> bool:
        """Get the optimistic data flag."""

        return bool(self.get("optimistic_data"))


ARConfig: Config = Config()
