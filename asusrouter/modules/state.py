"""State module."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
import importlib
import logging
from types import ModuleType
from typing import Any

from asusrouter.modules.common.connection import ARConnectionState
from asusrouter.modules.data import AsusData, AsusDataState
from asusrouter.tools.converters import get_enum_key_by_value

_LOGGER = logging.getLogger(__name__)


class AsusStateNone(int, Enum):
    """Asus state none."""

    NONE = 0


class AsusState(Enum):
    """Asus state."""

    NONE = AsusStateNone
    CONNECTION = ARConnectionState


AsusStateMap: dict[AsusState, AsusData | None] = {
    AsusState.NONE: None,
    AsusState.CONNECTION: None,
}


def get_datatype(state: Any | None) -> AsusData | None:
    """Get the datatype."""

    asus_state = get_enum_key_by_value(
        AsusState, type(state), default=AsusState.NONE
    )

    return AsusStateMap.get(asus_state)


def _get_module_name(state: AsusState) -> str | None:
    """Get the module name."""

    module_class = get_datatype(state)
    if module_class:
        return module_class.value

    return None


def _get_module(state: AsusState) -> ModuleType | None:
    """Get the module."""

    # Module name
    module_name = _get_module_name(state)
    if not module_name:
        return None

    # Module path
    module_path = f"asusrouter.modules.{module_name}"

    try:
        # Import and return the module
        return importlib.import_module(module_path)
    except ModuleNotFoundError:
        _LOGGER.debug("No module found for state %s", state)
        return None


def _has_method(module: ModuleType, method: str) -> bool:
    """Check if the module has the method."""

    return hasattr(module, method) and callable(getattr(module, method))


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusState,
    **kwargs: Any,
) -> bool:
    """Set the state."""

    # Get the module
    submodule = _get_module(state)

    # Process the data if module found
    if submodule and _has_method(submodule, "set_state"):
        # Determine the extra parameter
        if getattr(submodule, "REQUIRE_STATE", False):
            kwargs["extra_param"] = kwargs.get("router_state")
        if getattr(submodule, "REQUIRE_IDENTITY", False):
            kwargs["extra_param"] = kwargs.get("identity")

        # Call the function with the determined parameters
        return await submodule.set_state(
            callback=callback,
            state=state,
            **kwargs,
        )

    if submodule is None:
        # Log the enum class and member name if possible
        if isinstance(state, Enum):
            _LOGGER.debug(
                "No module found for state %s.%s",
                type(state).__name__,
                state.name,
            )
        else:
            _LOGGER.debug("No module found for state %r", state)

    return False


def save_state(
    state: AsusState,
    library: dict[AsusData, AsusDataState],
    needed_time: int | None = None,
    last_id: int | None = None,
) -> None:
    """Save the state."""

    # Get the correct data key
    datatype = get_datatype(state)
    if datatype is None or datatype not in library:
        return

    # Save the state
    library[datatype].update_state(state, last_id)
    library[datatype].offset_time(needed_time)
