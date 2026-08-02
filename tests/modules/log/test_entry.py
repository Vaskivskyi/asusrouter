"""Tests for the log entry model."""

from __future__ import annotations

import pytest

from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.tools.security.text import SensitiveText


def test_fields() -> None:
    """Fields are stored as given."""

    entry = ARLogEntry(
        timestamp_str="Jul 21 15:08:01", content=SensitiveText("up")
    )

    assert entry.timestamp_str == "Jul 21 15:08:01"
    assert entry.content.value == "up"


def test_program_name() -> None:
    """The raw syslog tag is exposed, and absent without a program."""

    tagged = ARLogEntry(
        timestamp_str="Jul 21 15:08:01",
        content=SensitiveText("up"),
        program=ARLogProgram(name="ntp"),
    )
    tagless = ARLogEntry(
        timestamp_str="Jul 21 15:08:01", content=SensitiveText("freeform")
    )

    assert tagged.program_name == "ntp"
    assert tagless.program_name is None


def test_message_is_not_stored_twice() -> None:
    """The message lives in `program` and `content`, not verbatim as well."""

    assert not hasattr(
        ARLogEntry(timestamp_str="Jul 21 15:08:01"), "message_str"
    )


def test_frozen() -> None:
    """Entries are immutable."""

    entry = ARLogEntry(
        timestamp_str="Jul 21 15:08:01", content=SensitiveText("up")
    )

    with pytest.raises(AttributeError):
        entry.content = "other"  # type: ignore[misc]
