"""Log entry model for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from asusrouter.modules.log.enums import ARProgram
from asusrouter.tools.security.text import SensitiveText

# Nothing was written, so there is nothing to protect or to expose
EMPTY_CONTENT: SensitiveText = SensitiveText("")


@dataclass(frozen=True, slots=True)
class ARLogProgram:
    """The program that emitted a log entry."""

    name: str
    pid: int | None = None


@dataclass(frozen=True, slots=True)
class ARLogProgramGroup:
    """A program name with every pid it ran under."""

    name: str  # raw syslog token
    program: ARProgram = ARProgram.UNKNOWN
    # instance index for indexed programs (`vpnclient5` -> 5)
    index: int | None = None
    pids: tuple[int, ...] = ()
    pidless: bool = False
    count: int = 0  # total for this program (all pids)


# A log holds tens of thousands of entries, so the slots save the per-entry
# `__dict__`
@dataclass(frozen=True, slots=True)
class ARLogEntry:
    """A single parsed syslog entry."""

    # Raw values
    timestamp_str: str

    # Parsed values
    timestamp: datetime | None = None
    program: ARLogProgram | None = None
    content: SensitiveText = EMPTY_CONTENT

    @property
    def program_name(self) -> str | None:
        """The raw syslog tag, absent on a tag-less entry."""

        return self.program.name if self.program is not None else None
