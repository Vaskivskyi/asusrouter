"""Block-all-devices data source for AsusRouter."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.nvram import ARNvramType, async_fetch_values
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters_v2.raw import raw_to_bool
from asusrouter.tools.types import ARCallbackType

# `MULTIFILTER_BLOCK_ALL` cuts internet for every device at once
KEY_BLOCK_ALL = ARNvramType.PARENTAL_CONTROL_BLOCK_ALL


class ARBlockAllSource(ARDataSource):
    """AsusRouter block-all-devices data source."""


# Universal instance - preferred
ARBlockAllSourceUniversal: ARBlockAllSource = ARBlockAllSource()


async def get_state(
    callback: ARCallbackType,
    source: ARBlockAllSource,
    *,
    get_data_callback: ARCallbackType | None = None,
    **kwargs: Any,
) -> dict[Any, Any]:
    """Fetch the block-all switch through the NVRAM module."""

    return await async_fetch_values(get_data_callback, KEY_BLOCK_ALL)


def translate_state(data: Any, **kwargs: Any) -> bool:
    """Translate the raw block-all nvram into a boolean."""

    if not isinstance(data, dict):
        return False
    return raw_to_bool(data.get(KEY_BLOCK_ALL)) or False


ARCallReg.register_module(
    ARBlockAllSource,
    get_state=get_state,
    translate_state=translate_state,
)


__all__ = [
    "ARBlockAllSource",
    "ARBlockAllSourceUniversal",
    "get_state",
    "translate_state",
]
