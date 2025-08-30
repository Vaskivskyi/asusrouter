"""Source module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.types import ARCallbackType


class ARDataSource:
    """AsusRouter data source.

    This is a universal class representing a data source
    within the AsusRouter ecosystem.
    """

    def __init__(self) -> None:
        """Initialize the data source."""


class ARDataType(FromStrMixin, StrEnum):
    """AsusRouter static data types."""

    UNKNOWN = UNKNOWN_MEMBER_STR


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

    def update(self, content: Any) -> None:
        """Update the last update timestamp to the current time."""

        self._content = content
        self._last_update = datetime.now(UTC)

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


class ARDataStateStatic(ARDataState):
    """AsusRouter static data state class.

    This class represents a static data, meaning it can be directly
    fetched without providing any additional context.
    """

    def __init__(self, source: ARDataType) -> None:
        """Initialize the static data state."""

        super().__init__(source)

    @property
    def source(self) -> ARDataType:
        """Get the static data source."""

        return ARDataType.from_value(self._source)


class ARDataStateDynamic(ARDataState):
    """AsusRouter dynamic data state class.

    This class represents a dynamic data state that can change
    over time and requires context to be fetched.
    """

    def __init__(self, source: ARDataSource) -> None:
        """Initialize the dynamic data state."""

        super().__init__(source)

    @property
    def source(self) -> ARDataSource:
        """Get the dynamic data source."""

        return (
            self._source
            if isinstance(self._source, ARDataSource)
            else ARDataSource()
        )
