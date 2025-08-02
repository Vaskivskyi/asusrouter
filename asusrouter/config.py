"""Configuration module for AsusRouter."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict

from asusrouter.tools.converters import safe_bool

CONFIG_DEFAULT_BOOL: bool = False


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
                converter = self._types.get(key, safe_bool)
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
