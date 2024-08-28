"""Firmware module."""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any, Optional

from asusrouter.tools.converters import clean_string, safe_int

_LOGGER = logging.getLogger(__name__)


class FirmwareType(Enum):
    """Type of firmware."""

    UNKNOWN = -999
    STOCK = 0
    MERLIN = 1
    GNUTON = 2


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
        build: Optional[int] = None,
        revision: Optional[int | str] = None,
    ) -> None:
        """Initialize the firmware object."""

        self.major: Optional[str] = None
        self.minor: Optional[int] = None
        self.build: Optional[int] = None
        self.revision: Optional[int | str] = None

        self.source: FirmwareType = FirmwareType.STOCK
        self.rog: bool = False
        self.beta: bool = False

        if version:
            self.from_string(version)
        else:
            self.major = major
            self.minor = minor
            self.build = build
            self.revision = revision
            self._update_rog()

        self._update_beta()
        self._update_source()

    def safe(self) -> Optional[Firmware]:
        """Return self if exists, otherwise None."""

        if self.major:
            return self
        return None

    def _update_beta(self) -> None:
        """Update the beta flag."""

        self.beta = False
        if self.major:
            self.beta = self.major[0] == "9"

    def _update_rog(self) -> None:
        """Update the ROG flag."""

        self.rog = False
        if isinstance(self.revision, str):
            self.rog = "_rog" in self.revision
            # Remove the _rog suffix
            if self.rog:
                self.revision = self.revision[:-4]

    def _update_source(self) -> None:
        """Update the source of the firmware."""

        if isinstance(self.revision, int):
            self.source = FirmwareType.MERLIN
            return

        if isinstance(self.revision, str):
            if "gnuton" in self.revision:
                self.source = FirmwareType.GNUTON
                return
            if "alpha" in self.revision or "beta" in self.revision:
                self.source = FirmwareType.MERLIN
                return

        self.source = FirmwareType.STOCK

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
            _LOGGER.warning(
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
        # Only if major version exists and has 0 member
        beta = major[0] == "9" if major and len(major) > 0 else False
        # Minor version
        minor = safe_int(re_match.group("minor"))
        # Build version
        build = safe_int(re_match.group("build"))
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
            _LOGGER.debug("Cannot compare Firmware with other object")
            return False

        if self.source != other.source:
            _LOGGER.debug("Cannot compare different firmware sources")
            return False

        if self.beta != other.beta:
            _LOGGER.debug("Comparing beta and non-beta firmware")

        if not self.major or not other.major:
            return False

        # Remove beta digit from the major version
        major_1 = [int(x) for x in self.major.split(".")[1:]]
        major_2 = [int(x) for x in other.major.split(".")[1:]]

        def get_prefix(v: str) -> str:
            """Get the prefix of the version."""

            if "alpha" in v:
                return clean_string(v.split("alpha")[0]) or "-1"
            if "beta" in v:
                return clean_string(v.split("beta")[0]) or "-1"
            # We should not reach this point ever if
            # attributes of Firmware were not manually overwritten
            _LOGGER.warning(
                "Code execution reached an unexpected point"
                + " in Firmware.__lt__.get_prefix()."
                + " Trying to compare %s and %s" % (self, other)
            )
            return v

        def lt_values(v1: Any, v2: Any) -> bool:
            """Check whether one value is less than the other."""

            if v2 is None:
                return False
            elif v1 is None:
                return True

            if isinstance(v1, int) and isinstance(v2, int):
                return v1 < v2
            if isinstance(v1, str) and isinstance(v2, str):
                return v1 < v2
            if isinstance(v1, list) and isinstance(v2, list):
                for i in range(min(len(v1), len(v2))):
                    if v1[i] < v2[i]:
                        return True
                    if v2[i] < v1[i]:
                        return False
            # Case of beta / alpha
            if isinstance(v1, int) and isinstance(v2, str):
                _prefix = get_prefix(v2)
                _v1 = str(v1)
                # This case will solve `1 vs 1beta1`
                if _v1 == _prefix:
                    return False
                # Everything else can be compared as strings
                return str(v1) < _prefix
            if isinstance(v1, str) and isinstance(v2, int):
                _prefix = get_prefix(v1)
                _v2 = str(v2)
                # This case will solve `1 vs 1beta1`
                if _v2 == _prefix:
                    return True
                # Everything else can be compared as strings
                return _prefix < str(v2)

            return False

        # Compare the major version
        if lt_values(major_1, major_2):
            return True
        if lt_values(major_2, major_1):
            return False

        # Compare the minor version
        if lt_values(self.minor, other.minor):
            return True
        if lt_values(other.minor, self.minor):
            return False

        # Compare the build version
        if lt_values(self.build, other.build):
            return True
        if lt_values(other.build, self.build):
            return False

        # Compare the revision version
        if lt_values(self.revision, other.revision):
            return True
        if lt_values(other.revision, self.revision):
            return False

        return False

    def __gt__(self, other: object) -> bool:
        """Compare two firmware versions."""

        # Invert the statement of less-than
        return not self.__lt__(other) and self.__ne__(other)
