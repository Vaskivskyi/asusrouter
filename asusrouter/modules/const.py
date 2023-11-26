"""Constants for modules."""

from __future__ import annotations

from typing import Any, Callable

# A converter type
MapConverterType = Callable[..., Any] | list[Callable[..., Any]]

# A map value type - this value should be found and converted
MapValueType = str | tuple[str] | tuple[str, MapConverterType]

# A map replace type - this value should be found, renamed and converted
MapReplaceType = str | tuple[str] | tuple[str, str] | tuple[str, str, MapConverterType]
