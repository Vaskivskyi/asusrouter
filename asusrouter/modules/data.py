"""Data module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from asusrouter.tools.converters_v2.raw import raw_to_bool


class AsusData(StrEnum):
    """AsusRouter data class."""

    PARENTAL_CONTROL = "parental_control"
    SYSTEM = "system"


@dataclass
class AsusDataState:
    """State of data."""

    data: Any | None = None
    timestamp: datetime = datetime.now(UTC)
    active: bool = False
    inactive_event: asyncio.Event = asyncio.Event()

    def start(self) -> None:
        """Set to active."""

        self.active = True
        self.inactive_event.clear()

    def stop(self) -> None:
        """Set to not-active."""

        self.active = False
        self.inactive_event.set()

    def update(self, data: Any) -> None:
        """Update the state."""

        self.data = data
        # Set timestamp to the current utc time
        self.timestamp = datetime.now(UTC)
        # Set to inactive
        self.stop()

    def update_state(self, state: Any, last_id: int | None = None) -> None:
        """Update a state variable in the data dict."""

        # Convert the state if needed
        state = convert_state(state)

        if last_id is not None:
            if not isinstance(self.data, dict):
                self.data = {}
            self.data.setdefault(last_id, {})["state"] = state
            return

        if isinstance(self.data, dict):
            self.data["state"] = state
            return

        self.data = {"state": state}

    def offset_time(self, offset: int | None) -> None:
        """Offset the timestamp."""

        if offset is None:
            self.timestamp = datetime.now(UTC)
            return

        self.timestamp = datetime.now(UTC) + timedelta(seconds=offset)


def convert_state(state: Any) -> bool:
    """Convert the state to a correct one."""

    # If the state is not boolean, convert it to boolean
    if not isinstance(state, bool):
        state = raw_to_bool(state)

    return bool(state)
