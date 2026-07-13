"""Firmware version representation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.firmware.enums import ARFirmwareType
from asusrouter.modules.firmware.translate import (
    translate_build,
    translate_major,
    translate_minor,
    translate_string,
    translate_type,
)


def _compare_revision(a: int | str | None, b: int | str | None) -> bool:
    """Return True if revision a is less than b."""

    if a is None:
        return True
    if b is None:
        return False
    if isinstance(a, int) and isinstance(b, int):
        return a < b
    return str(a) < str(b)


class ARFirmware:
    """Firmware class.

    This class represents the firmware information of the device.
    """

    def __init__(
        self,
        major: tuple[int, int, int, int] | None = None,
        minor: int | None = None,
        build: int | None = None,
        revision: int | str | None = None,
        rog: bool = False,
    ) -> None:
        """Initialize the firmware."""

        self._major: tuple[int, int, int, int] | None = major
        self._minor: int | None = minor
        self._build: int | None = build
        self._revision: int | str | None = revision
        self._rog: bool = rog
        self._firmware_type: ARFirmwareType = translate_type(
            major, minor, build, revision, rog
        )

    @property
    def build(self) -> int | None:
        """Get the build number."""

        return self._build

    @property
    def firmware_type(self) -> ARFirmwareType:
        """Get the firmware type."""

        return self._firmware_type

    @property
    def major(self) -> tuple[int, int, int, int] | None:
        """Get the major version as an int tuple."""

        return self._major

    @property
    def minor(self) -> int | None:
        """Get the minor version."""

        return self._minor

    @property
    def revision(self) -> int | str | None:
        """Get the revision."""

        return self._revision

    @property
    def rog(self) -> bool:
        """Get the ROG flag."""

        return self._rog

    @classmethod
    def from_nvram(
        cls,
        fw_major: Any,
        fw_minor: Any,
        fw_build: Any,
    ) -> ARFirmware:
        """Build from nvram values (FW_MAJOR, FW_MINOR, FW_BUILD)."""

        major = translate_major(fw_major)
        minor, minor_build = translate_minor(fw_minor)
        build, revision, rog = translate_build(
            str(fw_build) if fw_build is not None else None
        )
        # Older firmware carries the build in a dotted `buildno` and leaves
        # `extendno` empty - prefer it when present
        if minor_build is not None:
            build, revision = minor_build, None
        return cls(
            major=major, minor=minor, build=build, revision=revision, rog=rog
        )

    @classmethod
    def from_string(cls, fw_string: str | None) -> ARFirmware:
        """Build from a full firmware version string."""

        major, minor, build, revision, rog = translate_string(fw_string)
        return cls(
            major=major, minor=minor, build=build, revision=revision, rog=rog
        )

    def __str__(self) -> str:
        """Return firmware as version string."""

        major_str = (
            ".".join(str(x) for x in self._major) if self._major else "{}"
        )
        minor_str = str(self._minor) if self._minor is not None else "{}"
        build_str = str(self._build) if self._build is not None else "{}"
        revision_str = (
            str(self._revision) if self._revision is not None else "{}"
        )
        rog_str = "_rog" if self._rog else ""
        return f"{major_str}.{minor_str}.{build_str}_{revision_str}{rog_str}"

    def __repr__(self) -> str:
        """Return firmware as version string."""

        return self.__str__()

    def __hash__(self) -> int:
        """Return hash of the firmware."""

        return hash(
            (self._major, self._minor, self._build, self._revision, self._rog)
        )

    def __eq__(self, other: object) -> bool:
        """Check equality."""

        if not isinstance(other, ARFirmware):
            return NotImplemented
        return (
            self._major == other._major
            and self._minor == other._minor
            and self._build == other._build
            and self._revision == other._revision
            and self._rog == other._rog
        )

    def __lt__(self, other: object) -> bool:
        """Compare firmware versions.

        Comparison is only valid within the same firmware type.
        Major is compared by platform identity (skip first segment —
        the beta/normal prefix '3' or '9').
        """

        if not isinstance(other, ARFirmware):
            return NotImplemented
        if self._firmware_type != other._firmware_type:
            return False
        if self._major != other._major:
            return (self._major or ())[1:] < (other._major or ())[1:]
        if (self._minor, self._build) != (other._minor, other._build):
            return (self._minor or 0, self._build or 0) < (
                other._minor or 0,
                other._build or 0,
            )
        if self._revision != other._revision:
            return _compare_revision(self._revision, other._revision)
        return False

    def __gt__(self, other: object) -> bool:
        """Compare firmware versions."""

        if not isinstance(other, ARFirmware):
            return NotImplemented
        return other.__lt__(self)


AR_FW_388: ARFirmware = ARFirmware(major=(3, 0, 0, 4), minor=388, build=0)
