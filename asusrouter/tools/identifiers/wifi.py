"""WiFi interface tools."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

_SPLIT = re.compile(r"[. ]+")
_PARTS = 2


@dataclass(frozen=True)
class WiFiInterface:
    """A wireless interface: a radio `unit` and its virtual `subunit`."""

    unit: int
    subunit: int = 0

    @classmethod
    def from_value(cls, value: Any) -> WiFiInterface:
        """Create from a value."""

        if isinstance(value, cls):
            return value

        text = str(value).strip().removeprefix("wl")
        parts = _SPLIT.split(text)
        try:
            numbers = [int(part) for part in parts]
        except ValueError as ex:
            raise ValueError(f"Invalid WiFi interface: {value!r}") from ex

        if not numbers or len(numbers) > _PARTS:
            raise ValueError(f"Invalid WiFi interface: {value!r}")

        subunit = numbers[1] if len(numbers) == _PARTS else 0
        return cls(unit=numbers[0], subunit=subunit)

    @classmethod
    def from_value_safe(cls, value: Any) -> WiFiInterface | None:
        """Create from a value, or None when missing or unparseable."""

        if value is None:
            return None
        try:
            return cls.from_value(value)
        except (ValueError, TypeError):
            return None

    def __str__(self) -> str:
        """Return the standard `unit.subunit` form."""

        return f"{self.unit}.{self.subunit}"
