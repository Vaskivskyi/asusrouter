"""Firmware module."""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any, Optional

from asusrouter.tools.converters import clean_string, safe_int

_LOGGER = logging.getLogger(__name__)


class WebsError(Enum):
    """Webs Upgrade error status."""

    UNKNOWN = -999
    NONE = 0
    DOWNLOAD_ERROR = 1
    SPACE_ERROR = 2
    FW_ERROR = 3


class WebsFlag(Enum):
    """Webs flag status."""

    UNKNOWN = -999
    DONT = 0  # Don't do upgrade
    AVAILABLE = 1  # New FW available
    FORCE = 2  # Force upgrade


class WebsUpdate(Enum):
    """Webs Update status."""

    UNKNOWN = -999
    ACTIVE = 0
    INACTIVE = 1


class WebsUpgrade(Enum):
    """Webs Upgrade status."""

    UNKNOWN = -999
    INACTIVE = -1
    DOWNLOADING = 0
    FINISHED = 1
    ACTIVE = 2


class Firmware:
    """Firmware class.

    This class contains information about the firmware of a device."""

    def __init__(
        self,
        version: Optional[str] = None,
        major: Optional[str] = None,
        minor: Optional[int] = None,
        build: Optional[int | str] = None,
        revision: Optional[int | str] = None,
        rog: bool = False,
        beta: bool = False,
    ) -> None:
        """Initialize the firmware object."""

        self.major: Optional[str] = None
        self.minor: Optional[int] = None
        self.build: Optional[int | str] = None
        self.revision: Optional[int | str] = None
        self.rog: bool = False
        self.beta: bool = False

        if version:
            self.from_string(version)
        else:
            self.major = major
            self.minor = minor
            self.build = build
            self.revision = revision
            self.rog = rog
            self.beta = beta

        self._update_beta()

    def safe(self) -> Optional[Firmware]:
        """Return self if exists, otherwise None."""

        if self.major:
            return self
        return None

    def _update_beta(self) -> None:
        """Return the beta flag."""

        if self.major:
            self.beta = self.major[0] == "9"

    def from_string(self, fw_string: Optional[str] = None) -> None:
        """Read the firmware string."""

        fw_string = clean_string(fw_string)
        if not fw_string:
            return

        pattern = (
            r"^(?P<major>[39].?0.?0.?[46])?[_.]?"
            r"(?P<minor>[0-9]{3})[_.]?"
            r"(?P<build>[0-9]+)[_.-]?"
            r"(?P<revision>[a-zA-Z0-9-_]+?)(?=_rog|$)?"
            r"(?P<rog>_rog)?$"
        )

        re_match = re.match(pattern, fw_string)
        if not re_match:
            print(
                "Firmware version cannot be parsed. \
                    Please report this. The original FW string is: `%s`"
                % fw_string
            )
            return None

        # Major version
        major = re_match.group("major")
        major = (
            major[0] + "." + major[1] + "." + major[2] + "." + major[3]
            if major and "." not in major and len(major) == 4
            else major
        )
        beta = major[0] == "9"
        # Minor version
        minor = safe_int(re_match.group("minor"))
        # Build version
        build = re_match.group("build")
        build = safe_int(build) if build.isdigit() else build
        # Revision
        revision = re_match.group("revision")
        revision = safe_int(revision) if revision.isdigit() else revision
        # ROG flag (Merlin firmware)
        rog = re_match.group("rog") == "_rog"

        self.major = major
        self.minor = minor
        self.build = build
        self.revision = revision
        self.rog = rog
        self.beta = beta

    def __str__(self) -> str:
        """Return the firmware version as a string."""

        return (
            f"{self.major}.{self.minor}.{self.build}_{self.revision}"
            + f"{'_rog' if self.rog else ''}"
        )

    def __repr__(self) -> str:
        """Return the firmware version as a string."""

        return self.__str__()

    def __eq__(self, other: object) -> bool:
        """Compare two firmware versions."""

        if not isinstance(other, Firmware):
            return False

        # Check if the major, minor, build and revision are the same
        # ROG flag for Merlin firmware is ignored / beta is in major
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.build == other.build
            and self.revision == other.revision
        )

    def __lt__(self, other: object) -> bool:
        """Compare two firmware versions."""

        if not isinstance(other, Firmware):
            return False

        if self.beta != other.beta:
            _LOGGER.debug("Comparing beta and non-beta firmware")

        def compare_versions(v1: Any, v2: Any) -> bool:
            """Helper function to compare version parts."""

            if v1 is None or v2 is None:
                return False
            if isinstance(v1, int) and isinstance(v2, int):
                return v1 < v2
            if isinstance(v1, str) and isinstance(v2, str):
                return v1 < v2
            return False

        if self.major and other.major:
            major1 = [int(x) for x in self.major.split(".")[1:]]
            major2 = [int(x) for x in other.major.split(".")[1:]]
            if major1 != major2:
                return major1 < major2

            if compare_versions(self.minor, other.minor):
                return True

            if compare_versions(self.build, other.build):
                return True

            if compare_versions(self.revision, other.revision):
                return True

        return False

    def __gt__(self, other: object) -> bool:
        """Compare two firmware versions."""

        # Invert the statement of less-than
        return not self.__lt__(other) and self.__ne__(other)
