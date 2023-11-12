"""Firmware module."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from asusrouter.tools.converters import clean_string

_LOGGER = logging.getLogger(__name__)


@dataclass
class Firmware:
    """Firmware class.

    This class contains information about the firmware of a device."""

    major: str = "3.0.0.4"
    minor: Optional[int] = None
    build: Optional[int] = None
    revision: Optional[int | str] = None

    def __str__(self) -> str:
        """Return the firmware version as a string."""

        return f"{self.major}.{self.minor}.{self.build}_{self.revision}"

    def __lt__(self, other: Firmware | None) -> bool:
        """Compare two firmware versions."""

        if other:
            if self.major is not None and other.major is not None:
                # Check if the first character of either major version is the same
                if self.major[0] == other.major[0]:
                    # Split the major versions into lists of integers
                    major1 = [int(x) for x in self.major.split(".")]
                    major2 = [int(x) for x in other.major.split(".")]
                    # Compare the major versions
                    if major1 < major2:
                        return True
                    # Proceed only if major is the same for both
                    if major1 == major2:
                        # Compare the minor versions
                        if (
                            self.minor is not None
                            and other.minor is not None
                            and self.minor < other.minor
                        ):
                            return True
                        # Compare the build versions
                        if (
                            self.build is not None
                            and other.build is not None
                            and self.build < other.build
                        ):
                            return True
                        # Compare the revision versions
                        if (
                            isinstance(self.revision, int)
                            and isinstance(other.revision, int)
                            and self.revision < other.revision
                        ):
                            return True

        return False

    # Define more-than
    def __gt__(self, other: Firmware | None) -> bool:
        """Compare two firmware versions."""

        # Invert the statement of less-than
        return not self.__lt__(other)


def read_fw_string(content: Optional[str]) -> Optional[Firmware]:
    """Firmware string parser"""

    # Clean and check the string
    content = clean_string(content)
    if not content:
        return None

    # Search pattern
    pattern = (
        r"^(?P<major>[39].?0.?0.?[46])?[_.]?"
        r"(?P<minor>[0-9]{3})[_.]?"
        r"(?P<build>[0-9]+)[_.-]?"
        r"(?P<revision>[a-zA-Z0-9-_]+)?$"
    )
    match = re.match(pattern, content)
    if not match:
        _LOGGER.warning(
            "Firmware version cannot be parsed. Please report this. The original FW string is: %s",
            content,
        )
        return Firmware()

    major = match.group("major") or "3.0.0.4"
    major = (
        major[0] + "." + major[1] + "." + major[2] + "." + major[3]
        if major and not "." in major and len(major) == 4
        else major
    )

    minor = int(match.group("minor"))

    build = int(match.group("build"))

    revision = match.group("revision")
    revision = (
        int(revision)
        if revision and revision.isdigit()
        else revision
        if revision
        else 0
    )

    firmwawe = Firmware(
        major=major,
        minor=minor,
        build=build,
        revision=revision,
    )

    return firmwawe
