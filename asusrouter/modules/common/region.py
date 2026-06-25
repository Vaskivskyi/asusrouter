"""Region module for AsusRouter."""

from __future__ import annotations

from enum import StrEnum
import logging
import threading
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.converters_v2.raw import raw_to_int
from asusrouter.tools.enum import FromStrMixin

_LOGGER = logging.getLogger(__name__)

# Territory codes already reported as unknown, to warn only once each
_reported_unknown_regions: set[str] = set()
_unknown_regions_lock = threading.Lock()


class ARRegion(FromStrMixin, StrEnum):
    """Router region / territory code."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # ASUS territory / SKU codes (from `in_territory_code`)
    AA = "aa"
    CH = "ch"
    CN = "cn"
    CT = "ct"
    EU = "eu"
    GD = "gd"
    KR = "kr"
    OP = "op"
    RU = "ru"
    SG = "sg"
    TC = "tc"
    TW = "tw"
    UA = "ua"
    US = "us"


def _warn_unknown_region(tcode: str) -> None:
    """Warn once per distinct unknown territory code."""

    with _unknown_regions_lock:
        if tcode in _reported_unknown_regions:
            return
        _reported_unknown_regions.add(tcode)
        _LOGGER.warning(
            "We found an unknown region. Please, report this value: `%s`",
            tcode,
        )


def translate_region(tcode: Any) -> tuple[ARRegion, int | None]:
    """Translate a territory code like `US/01` into region and area."""

    if not isinstance(tcode, str) or not tcode:
        return ARRegion.UNKNOWN, None

    code, _, area = tcode.partition("/")
    region = ARRegion.from_value(code)
    if region is ARRegion.UNKNOWN:
        _warn_unknown_region(tcode)

    return region, raw_to_int(area)
