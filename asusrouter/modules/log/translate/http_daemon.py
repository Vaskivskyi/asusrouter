"""HTTP daemon log event translation for AsusRouter."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Final

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.common.api import ARApiClient
from asusrouter.modules.common.status import ARStatusCode
from asusrouter.modules.connection import ARConnection
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.pattern import (
    ARLogPattern,
    ARLogPatternSet,
)
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import IpAddress

_DATE_PARTS: Final[int] = 3


class AREventHttpDaemon(FromStrMixin, StrEnum):
    """HTTP daemon event types (the logged operation)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CERTIFICATE_GENERATE = "certificate_generate"
    CERTIFICATE_INFO = "certificate_info"
    CERTIFICATE_INIT = "certificate_init"
    CERTIFICATE_RELOAD = "certificate_reload"
    CERTIFICATE_RESTORE = "certificate_restore"
    LOGIN = "login"


def _read_date(text: str) -> date | None:
    """Parse a `YYYY/M/D` certificate date, or None."""

    parts = text.split("/")
    if len(parts) != _DATE_PARTS:
        return None
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError:
        return None


def _read_status(word: str) -> ARStatusCode:
    """Map a firmware status word."""

    lowered = word.lower()
    if lowered.startswith("succe"):
        return ARStatusCode.SUCCESS
    if lowered.startswith("fail"):
        return ARStatusCode.FAIL
    return ARStatusCode.UNKNOWN


PATTERNS = ARLogPatternSet(
    AREventHttpDaemon.UNKNOWN,
    (
        # The SSL port trails a literal `...`
        ARLogPattern(
            AREventHttpDaemon.CERTIFICATE_GENERATE,
            r"Generating SSL certificate\.\.\.(?P<port>\d+)",
            convert={AREventKey.PORT: int},
            marker="Generating SSL certificate",
        ),
        # Subject and issuer name the device and its AiMesh root as
        # `<model>-<last 2 MAC octets>`, so the raw stays unclassified
        # TODO: decide whether part-MAC is sensitive
        ARLogPattern(
            AREventHttpDaemon.CERTIFICATE_INFO,
            r"S:(?P<subject>.+?) Server Certificate,\s*"
            r"I:(?P<issuer>.+?) Root Certificate\s+(?P<serial>\S+),\s*"
            r"(?P<valid_from>[\d/]+)\s*~\s*(?P<valid_to>[\d/]+)",
            convert={
                AREventKey.VALID_FROM: _read_date,
                AREventKey.VALID_TO: _read_date,
            },
            marker="Server Certificate",
        ),
        ARLogPattern(
            AREventHttpDaemon.CERTIFICATE_INIT,
            r"(?P<status>\w+) to init SSL certificate\.\.\.(?P<port>\d+)",
            convert={AREventKey.PORT: int, AREventKey.STATUS: _read_status},
            marker="to init SSL certificate",
        ),
        ARLogPattern(
            AREventHttpDaemon.CERTIFICATE_RELOAD,
            r"reload cert and clean all files",
            marker="reload cert and clean all files",
        ),
        ARLogPattern(
            AREventHttpDaemon.CERTIFICATE_RESTORE,
            r"Restore saved SSL certificate\.\.\.(?P<port>\d+)",
            convert={AREventKey.PORT: int},
            marker="Restore saved SSL certificate",
        ),
        ARLogPattern(
            AREventHttpDaemon.LOGIN,
            r"\[LOGIN\]\[(?P<connection>[A-Za-z]+)\]"
            r"\[(?P<api_client>[A-Za-z]+)\]"
            r"\s+(?P<status>[A-Za-z]+)\s+\((?P<client_ip>[\d.]+)\)",
            convert={
                AREventKey.API_CLIENT: ARApiClient.from_value,
                AREventKey.CLIENT_IP: IpAddress.from_value_safe,
                AREventKey.CONNECTION: ARConnection.from_value,
                AREventKey.STATUS: _read_status,
            },
            marker="[LOGIN]",
        ),
    ),
)
