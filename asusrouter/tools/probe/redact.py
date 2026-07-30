"""Free-text scrubbing for AsusRouter probe reports."""

from __future__ import annotations

import re
from typing import Final

# Placeholders left where an identifier was removed
REDACTED_MAC: Final[str] = "-=MAC=-"
REDACTED_IP: Final[str] = "-=IP=-"

_MAC = re.compile(r"\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
# Four groups minimum, so a `HH:MM:SS` timestamp is never taken for an
# address; the compressed `::` form is only caught when it is this long
_IPV6 = re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){3,}\b")


def scrub_text(text: str) -> str:
    """Replace the identifiers a log message can carry in free text."""

    text = _MAC.sub(REDACTED_MAC, text)
    text = _IPV6.sub(REDACTED_IP, text)

    return _IPV4.sub(REDACTED_IP, text)


__all__ = [
    "REDACTED_IP",
    "REDACTED_MAC",
    "scrub_text",
]
