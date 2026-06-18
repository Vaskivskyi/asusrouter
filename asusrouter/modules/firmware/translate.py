"""Translations for the firmware module."""

from __future__ import annotations

import logging
import re

from asusrouter.modules.firmware.flag import ARFirmwareType
from asusrouter.tools.converters_v2.raw import raw_to_str

_LOGGER = logging.getLogger(__name__)

_MAJOR_BETA_PREFIX = 9
_WARNED_FW_STRINGS: set[str] = set()

FW_MAJOR_PATTERN = re.compile(r"^([39]).?([0-9]).?([0-9]).?([0-9])$")
FW_BUILD_PATTERN = re.compile(
    r"^(?P<build>[0-9]+)[_.-]?"
    r"(?P<revision>[a-zA-Z0-9-_]+?)(?=_rog|$)?"
    r"(?P<rog>_rog)?$"
)
FW_PATTERN = re.compile(
    r"^(?P<major>[39].?0.?0.?[46])?[_.]?"
    r"(?P<minor>[0-9]{3})[_.]?"
    r"(?P<build>[0-9]+)[_.-]?"
    r"(?P<revision>[a-zA-Z0-9-_]+?)(?=_rog|$)?"
    r"(?P<rog>_rog)?$"
)


def _translate_revision(raw: str | None) -> int | str | None:
    """Translate revision string to int, str, or None."""

    if not raw:
        return None
    return int(raw) if raw.isdigit() else raw


def translate_major(raw: str | None) -> tuple[int, int, int, int] | None:
    """Translate major version string to an int tuple if possible."""

    raw = raw_to_str(raw)
    if not raw:
        return None
    match = FW_MAJOR_PATTERN.match(raw)
    if not match:
        return None
    a, b, c, d = match.groups()
    return int(a), int(b), int(c), int(d)


def translate_build(
    raw: str | None,
) -> tuple[int | None, int | str | None, bool]:
    """Translate build string to (build, revision, rog)."""

    raw = raw_to_str(raw)
    if not raw:
        return None, None, False

    match = FW_BUILD_PATTERN.match(raw)
    if not match:
        return None, None, False

    build = int(match.group("build"))
    revision = _translate_revision(match.group("revision"))
    rog = match.group("rog") is not None

    return build, revision, rog


def translate_type(
    major: tuple[int, int, int, int] | None,
    minor: int | None,
    build: int | None,
    revision: int | str | None,
    rog: bool,
) -> ARFirmwareType:
    """Determine firmware type from firmware components."""

    if major is None or minor is None or build is None:
        return ARFirmwareType.UNKNOWN
    if major[0] == _MAJOR_BETA_PREFIX:
        return ARFirmwareType.STOCK
    if isinstance(revision, str):
        if "gnuton" in revision:
            return ARFirmwareType.GNUTON
        if "alpha" in revision or "beta" in revision:
            return ARFirmwareType.MERLIN
    if rog:
        return ARFirmwareType.MERLIN
    return ARFirmwareType.STOCK


def translate_string(
    raw: str | None,
) -> tuple[
    tuple[int, int, int, int] | None,
    int | None,
    int | None,
    int | str | None,
    bool,
]:
    """Translate firmware version string to components."""

    raw = raw_to_str(raw)
    if not raw or raw in ("__", "___"):
        return None, None, None, None, False

    match = FW_PATTERN.match(raw)
    if not match:
        if raw not in _WARNED_FW_STRINGS:
            _WARNED_FW_STRINGS.add(raw)
            _LOGGER.warning(
                "Firmware string cannot be parsed. "
                "Please report this. Original string: `%s`",
                raw,
            )
        return None, None, None, None, False

    major_raw = match.group("major")
    major: tuple[int, int, int, int] | None = None
    if major_raw:
        a, b, c, d = (int(ch) for ch in major_raw if ch.isdigit())
        major = (a, b, c, d)
    elif raw not in _WARNED_FW_STRINGS:
        _WARNED_FW_STRINGS.add(raw)
        _LOGGER.warning(
            "Partial firmware string, major version missing. "
            "Please report this. Original string: `%s`",
            raw,
        )

    minor = int(match.group("minor"))
    build = int(match.group("build"))
    revision = _translate_revision(match.group("revision"))
    rog = match.group("rog") is not None

    return major, minor, build, revision, rog
