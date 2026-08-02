"""Tests for the log enums."""

from __future__ import annotations

import pytest

from asusrouter.modules.log.enums import ARLogField, ARProgram


def test_field_values() -> None:
    """Field members carry their dict-key strings."""

    assert ARLogField.ENTRY_COUNT.value == "entry_count"
    assert ARLogField.ENTRY_LIST.value == "entry_list"
    assert ARLogField.LAST_ENTRY.value == "last_entry"
    assert ARLogField.PROGRAM_LIST.value == "program_list"


def test_field_unknown_fallback() -> None:
    """An unrecognised field value maps to UNKNOWN."""

    assert ARLogField.from_value("nope") is ARLogField.UNKNOWN


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("miniupnpd", ARProgram.MINIUPNP),
        ("kernel", ARProgram.KERNEL),
        ("dnsmasq-dhcp", ARProgram.DNSMASQ_DHCP),
        ("dhcp client", ARProgram.DHCP_CLIENT),
        ("hour_monitor", ARProgram.HOUR_MONITOR),
        ("disk_monitor", ARProgram.DISK_MONITOR),
        ("httpd", ARProgram.HTTP_DAEMON),
        ("roamast", ARProgram.ROAMING_ASSISTANT),
    ],
)
def test_program_known_values(value: str, expected: ARProgram) -> None:
    """Known raw program tokens resolve to their member."""

    assert ARProgram.from_value(value) is expected


@pytest.mark.parametrize("value", ["ARK", "nosuchd", ""])
def test_program_unknown_values(value: str) -> None:
    """Unrecognised program tokens fall back to UNKNOWN."""

    assert ARProgram.from_value(value) is ARProgram.UNKNOWN
