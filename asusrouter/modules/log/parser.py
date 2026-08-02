"""Log parser for AsusRouter."""

from __future__ import annotations

from functools import lru_cache
import re

from asusrouter.modules.log.entry import ARLogEntry, ARLogProgram
from asusrouter.modules.log.enums import ARProgram
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.security.text import SensitiveText

# The reply is a broken-JSON object whose value is the raw, unquoted,
# multi-line syslog text: {"nvram_dump-syslog.log":<log>}
_ENVELOPE_KEY = '"nvram_dump-syslog.log":'

# Split log by BusyBox syslog timestamp
_RECORD_HEAD = re.compile(r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+")

# Firmware colours some kernel messages, clean it
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# A log is written by a small number of daemons
_PROGRAM_CACHE_SIZE = 512

# How much log text is kept to continue the next read from
ANCHOR_LENGTH = 16384

# How many whole records an overlap must span to be believed
ANCHOR_RECORDS_MIN = 3

# A program token with `[pid]`
_PID = re.compile(r"^(?P<name>.*?)\[(?P<pid>\d+)\]$")

# An indexed program token
_INDEXED = re.compile(r"^(?P<base>.*?)(?P<index>\d+)$")

# Raw tokens that resolve to a different program than their own name
_ALIASES: dict[str, ARProgram] = {
    # AiMesh lib firing rc_service commands
    # The most of there are already reported by rc_service
    "amas_lib": ARProgram.RC_SERVICE,
    # Case mismatch
    "HTTPD": ARProgram.HTTP_DAEMON,
}

# Freeform lifecycle lines carry no `tag:` prefix
_FREEFORM: tuple[ARProgram, ...] = (ARProgram.SYSLOG,)

# A message whose tag is empty (`: fwver: ...`) still names its writer
# by how it starts - other firmware writes the same line as `init: ...`
_UNTAGGED: tuple[tuple[str, ARProgram], ...] = (("fwver:", ARProgram.INIT),)

# Trailing space avoids matching a real `tag:` prefix
_FREEFORM_PREFIXES: tuple[tuple[str, ARLogProgram], ...] = tuple(
    (f"{program.value} ", ARLogProgram(name=program.value))
    for program in _FREEFORM
)


def _untagged_program(content: str) -> ARLogProgram | None:
    """Recover the program of a message the device left untagged."""

    for prefix, program in _UNTAGGED:
        if content.startswith(prefix):
            return _program(program.value, None)

    return None


def _freeform_program(message: str) -> ARLogProgram | None:
    """Map a freeform lifecycle line to its program."""

    for prefix, program in _FREEFORM_PREFIXES:
        if message.startswith(prefix):
            return program

    return None


# The emitter is immutable and repeats on nearly every entry
@lru_cache(maxsize=_PROGRAM_CACHE_SIZE)
def _program(name: str, pid: int | None) -> ARLogProgram:
    """Return the shared emitter for a program token."""

    return ARLogProgram(name=name, pid=pid)


# A log holds few distinct program tokens
@lru_cache(maxsize=256)
def parse_program(name: str) -> tuple[ARProgram, int | None]:
    """Resolve a raw program token into a kind and optional index."""

    alias = _ALIASES.get(name)
    if alias is not None:
        return alias, None

    match = _INDEXED.match(name)
    if match is not None:
        base = ARProgram.from_value(match.group("base"))
        if base is not ARProgram.UNKNOWN:
            return base, int(match.group("index"))

    return ARProgram.from_value(name), None


def _split_message(message: str) -> tuple[ARLogProgram | None, str]:
    """Split a message into its program and content."""

    freeform = _freeform_program(message)
    if freeform is not None:
        return freeform, message

    head, separator, tail = message.partition(":")
    if not separator:
        return None, message

    # The record head consumed the space after the stamp, so a message
    # never starts on whitespace and only its tail needs trimming
    name = head.rstrip()
    pid: int | None = None
    # only a `[pid]` suffix can make the token match, and most never do
    if name.endswith("]"):
        match = _PID.match(name)
        if match is not None:
            name = match.group("name")
            pid = int(match.group("pid"))

    if not name:
        content = tail.lstrip()
        return _untagged_program(content), content

    return _program(name, pid), tail.lstrip()


def strip_envelope(content: str | None) -> str:
    """Strip the reply wrapper and colour escapes from a log reply."""

    text = raw_to_str(content) or ""

    index = text.find(_ENVELOPE_KEY)
    if index != -1:
        text = text[index + len(_ENVELOPE_KEY) :].rstrip()
        if text.endswith("}"):
            text = text[:-1]

    if "\x1b" in text:
        text = _ANSI.sub("", text)

    return text.rstrip()


def anchor_of(text: str) -> str:
    """Return the tail of a log text, to continue from on the next read."""

    return text[-ANCHOR_LENGTH:]


def find_continuation(text: str, anchor: str) -> int | None:
    """Locate where the records new since `anchor` begin."""

    if not anchor:
        return None

    # A device drops the oldest records, never the newest, so the tail
    # anchored on usually survives whole
    found = text.rfind(anchor)
    if found != -1:
        return found + len(anchor)

    # It dropped into the anchor itself
    low, high, best = 1, len(anchor) - 1, 0
    while low <= high:
        middle = (low + high) // 2
        if text.rfind(anchor[-middle:]) != -1:
            best, low = middle, middle + 1
        else:
            high = middle - 1

    if best == 0:
        return None

    tail = anchor[-best:]
    # Matching a few characters is chance
    if len(_RECORD_HEAD.findall(tail)) < ANCHOR_RECORDS_MIN:
        return None

    return text.rfind(tail) + best


def parse_log(
    content: str | None, *, after: str | None = None
) -> list[ARLogEntry]:
    """Parse a raw log reply into ordered entries."""

    return parse_text(strip_envelope(content), after=after)


def parse_text(text: str, *, after: str | None = None) -> list[ARLogEntry]:
    """Parse stripped log text into ordered entries."""

    if after is not None:
        offset = find_continuation(text, after)
        if offset is not None:
            text = text[offset:]

    # The split cuts the whole text in one C-level pass and yields
    # `[prefix, stamp, message, stamp, message, ...]`
    parts = _RECORD_HEAD.split(text)
    entries: list[ARLogEntry] = []
    append = entries.append
    for index in range(1, len(parts) - 1, 2):
        # The split already dropped the whitespace ahead of the message
        message = parts[index + 1].rstrip()
        program, content = _split_message(message)
        append(
            ARLogEntry(
                timestamp_str=parts[index],
                program=program,
                content=SensitiveText(content),
            )
        )

    return entries
