"""Source module."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import logging
from typing import Any, cast

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.types import ARCallableType, ARCallbackType

_LOGGER = logging.getLogger(__name__)


class ARDataSource:
    """AsusRouter data source.

    This is a universal class representing a data source
    within the AsusRouter ecosystem.

    Sources are equal by exact type and their `_key()`; router-global
    sources keep the empty default, subclasses with defining properties
    override `_key` only.
    """

    def __init__(self) -> None:
        """Initialize the data source."""

    def _key(self) -> tuple[Any, ...]:
        """Return the defining fields for equality and hashing."""

        return ()

    def __eq__(self, other: object) -> bool:
        """Equal by exact type and defining fields."""

        if type(other) is not type(self):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        """Hash by type and defining fields."""

        return hash((type(self), *self._key()))

    def __repr__(self) -> str:
        """Representation of the data source."""

        key = self._key()
        name = type(self).__name__
        return f"<{name} {key!r}>" if key else f"<{name}>"


# Empty abstract base - UNKNOWN lives in subclasses (an enum with
# members cannot be subclassed)
class ARDataType(FromStrMixin, StrEnum):
    """AsusRouter data type."""


class ARDataTypeGeneric(ARDataType):
    """AsusRouter generic data types."""

    UNKNOWN = UNKNOWN_MEMBER_STR


class ARDataCollection:
    """AsusRouter data collection class.

    This class is used to represent multiple data types
    or sources to be managed collectively.
    """

    def __init__(
        self,
        sources: Iterable[ARDataSource | ARDataType],
    ) -> None:
        """Initialize the data collection."""

        self._sources: list[ARDataSource | ARDataType] = list(sources)

    def __iter__(self) -> Iterator[ARDataSource | ARDataType]:
        """Iterate over the data sources."""

        return iter(self._sources)

    def __len__(self) -> int:
        """Get the number of data sources."""

        return len(self._sources)

    def __getitem__(
        self, index: int | slice
    ) -> ARDataSource | ARDataType | ARDataCollection:
        """Get a data source by index or slice."""

        if isinstance(index, slice):
            return self.__class__(self._sources[index])

        return self._sources[index]

    def __bool__(self) -> bool:
        """Check if the data collection has any sources."""

        return bool(self._sources)

    def __repr__(self) -> str:
        """Get the string representation of the data collection."""

        return f"{self.__class__.__name__}({self._sources!r})"

    @classmethod
    def from_value(cls, value: Any) -> ARDataCollection | None:
        """Create a data collection from a value."""

        if isinstance(value, ARDataSource | ARDataType):
            return cls([value])

        if isinstance(value, (str, bytes, bytearray)):
            return None

        if isinstance(value, Iterable):
            valid_sources: list[ARDataSource | ARDataType] = []
            invalid: list[Any] = []

            for item in value:
                if isinstance(item, (ARDataSource, ARDataType)):
                    valid_sources.append(item)
                else:
                    invalid.append(item)

            if invalid:
                _LOGGER.warning(
                    "Ignored invalid items for ARDataCollection: %s", invalid
                )

            if not valid_sources:
                return None

            return cls(valid_sources)

        return None


class ARDataState:
    """AsusRouter data state class.

    Instances of this class hold information on the data
    and time of the last update.
    """

    def __init__(self, source: ARDataSource | ARDataType) -> None:
        """Initialize the data state."""

        if not isinstance(source, ARDataSource | ARDataType):
            raise TypeError(
                "A valid `ARDataSource` or `ARDataType` is required "
                "to initialize an <ARDataState>. "
                f"Received: {type(source)}."
            )

        self._source: ARDataSource | ARDataType = source
        self._content: Any | None = None
        self._last_update: datetime | None = None
        self._callback: ARCallbackType | None = None
        self._state_caller: ARCallableType | None = None
        self._state_caller_multi: bool = False
        self._translate_caller: ARCallableType | None = None
        self._translate_caller_multi: bool = False
        # In-flight refresh marker - waiters await it instead of refetching
        self._refresh_event: asyncio.Event | None = None

    def update(self, content: Any) -> None:
        """Update the last update timestamp to the current time."""

        self._content = content
        self._last_update = datetime.now(UTC)

    def expire(self) -> None:
        """Mark the cached content stale so the next read refetches it."""

        self._last_update = None

    def is_fresh(self, threshold: timedelta) -> bool:
        """Check if the data is fresh based on the given threshold."""

        if not isinstance(threshold, timedelta):
            raise TypeError(
                "A valid `timedelta` is required to define if the data "
                "is fresh."
            )

        if self._last_update is None:
            return False

        return self._last_update + threshold > datetime.now(UTC)

    @property
    def refreshing(self) -> bool:
        """Whether a refresh is currently in flight."""

        return self._refresh_event is not None

    def begin_refresh(self) -> None:
        """Mark the state as being refreshed."""

        self._refresh_event = asyncio.Event()

    def end_refresh(self) -> None:
        """Mark the refresh as finished and wake any waiters."""

        event = self._refresh_event
        self._refresh_event = None
        if event is not None:
            event.set()

    async def async_wait_refresh(self) -> None:
        """Wait for an in-flight refresh to finish (no-op when idle)."""

        event = self._refresh_event
        if event is not None:
            await event.wait()

    @property
    def source(self) -> ARDataSource | ARDataType:
        """Get the data source or type."""

        return self._source

    @property
    def content(self) -> Any | None:
        """Get the content."""

        return self._content

    @property
    def last_update(self) -> datetime | None:
        """Get the last update timestamp."""

        return self._last_update

    @property
    def callback(self) -> ARCallbackType | None:
        """Get the callback function."""

        return self._callback

    @callback.setter
    def callback(self, value: ARCallbackType | None) -> None:
        """Set the callback function."""

        self._callback = value

    @property
    def state_caller(self) -> ARCallableType | None:
        """Get the state getter callable."""

        return self._state_caller

    @state_caller.setter
    def state_caller(self, value: ARCallableType | None) -> None:
        """Set the state getter callable."""

        self._state_caller = value

    @property
    def state_caller_multi(self) -> bool:
        """Whether the state getter is a multicaller."""

        return self._state_caller_multi

    @state_caller_multi.setter
    def state_caller_multi(self, value: bool) -> None:
        """Set the state getter multicaller flag."""

        self._state_caller_multi = bool(value)

    @property
    def translate_caller(self) -> ARCallableType | None:
        """Get the state translator callable."""

        return self._translate_caller

    @translate_caller.setter
    def translate_caller(self, value: ARCallableType | None) -> None:
        """Set the state translator callable."""

        self._translate_caller = value

    @property
    def translate_caller_multi(self) -> bool:
        """Whether the state translator is a batch translator."""

        return self._translate_caller_multi

    @translate_caller_multi.setter
    def translate_caller_multi(self, value: bool) -> None:
        """Set the state translator batch flag."""

        self._translate_caller_multi = bool(value)


class ARDataStateStatic(ARDataState):
    """AsusRouter static data state class.

    This class represents a static data, meaning it can be directly
    fetched without providing any additional context.
    """

    def __init__(self, source: ARDataType) -> None:
        """Initialize the static data state."""

        if not isinstance(source, ARDataType):
            raise TypeError(
                "A valid `ARDataType` is required to initialize an "
                f"<ARDataStateStatic>. Received: {type(source)}."
            )

        super().__init__(source)

    @property
    def source(self) -> ARDataType:
        """Get the static data source."""

        return cast(ARDataType, self._source)


class ARDataStateDynamic(ARDataState):
    """AsusRouter dynamic data state class.

    This class represents a dynamic data state that can change
    over time and requires context to be fetched.
    """

    def __init__(self, source: ARDataSource) -> None:
        """Initialize the dynamic data state."""

        if not isinstance(source, ARDataSource):
            raise TypeError(
                "A valid `ARDataSource` is required to initialize an "
                f"<ARDataStateDynamic>. Received: {type(source)}."
            )

        super().__init__(source)

    @property
    def source(self) -> ARDataSource:
        """Get the dynamic data source."""

        return cast(ARDataSource, self._source)
