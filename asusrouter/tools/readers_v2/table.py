"""Translation table readers for AsusRouter."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar

from asusrouter.tools.converters_v2.raw import raw_convert

_K = TypeVar("_K")
_F = TypeVar("_F")


def read_table(
    data: Mapping[Any, Any],
    table: Iterable[tuple[_K, _F, Callable[[Any], Any]]],
    *,
    key: Callable[[_K], Any] | None = None,
) -> dict[_F, Any]:
    """Read a `(key, field, converter)` table into a field dict.

    `key` resolves a table key to its raw data key (e.g. an indexed nvram
    template); by default the key is used as-is. Fields whose raw value is
    absent or converts to no value are skipped.
    """

    fields: dict[_F, Any] = {}
    for kind, field, converter in table:
        raw_key = key(kind) if key is not None else kind
        value = raw_convert(data.get(raw_key), converter)
        if value is not None:
            fields[field] = value
    return fields
