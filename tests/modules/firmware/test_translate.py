"""Tests for the firmware translate module."""

from __future__ import annotations

import logging

import pytest

import asusrouter.modules.firmware.translate as translate_module
from asusrouter.modules.firmware.translate import (
    _translate_revision,
    translate_build,
    translate_major,
    translate_string,
    translate_type,
)
from asusrouter.modules.firmware.types import ARFirmwareType


class TestTranslateRevision:
    """Test _translate_revision."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, None),
            ("", None),
            ("2", 2),
            ("120", 120),
            ("g8178ee0", "g8178ee0"),
            ("g0d793c1_386-g45e48", "g0d793c1_386-g45e48"),
        ],
    )
    def test_translate_revision(
        self, raw: str | None, expected: int | str | None
    ) -> None:
        """Test _translate_revision."""

        assert _translate_revision(raw) == expected


class TestTranslateMajor:
    """Test translate_major."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, None),
            ("", None),
            ("   ", None),
            ("invalid", None),
            ("1.2.3", None),
            ("3.0.0.4", (3, 0, 0, 4)),
            ("3.0.0.6", (3, 0, 0, 6)),
            ("9.0.0.4", (9, 0, 0, 4)),
            ("9.0.0.6", (9, 0, 0, 6)),
            ("3004", (3, 0, 0, 4)),
            ("3006", (3, 0, 0, 6)),
            ("9006", (9, 0, 0, 6)),
            ("  3.0.0.4  ", (3, 0, 0, 4)),
        ],
    )
    def test_translate_major(
        self,
        raw: str | None,
        expected: tuple[int, int, int, int] | None,
    ) -> None:
        """Test translate_major."""

        assert translate_major(raw) == expected


class TestTranslateBuild:
    """Test translate_build."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, (None, None, False)),
            ("", (None, None, False)),
            ("   ", (None, None, False)),
            ("not_a_build", (None, None, False)),
            # Merlin: numeric revision
            ("8_2", (8, 2, False)),
            ("7_120", (7, 120, False)),
            # Stock: string revision
            ("40456_g8178ee0", (40456, "g8178ee0", False)),
            (
                "34713_g0d793c1_386-g45e48",
                (34713, "g0d793c1_386-g45e48", False),
            ),
            # ROG
            ("8_2_rog", (8, 2, True)),
        ],
    )
    def test_translate_build(
        self,
        raw: str | None,
        expected: tuple[int | None, int | str | None, bool],
    ) -> None:
        """Test translate_build."""

        assert translate_build(raw) == expected


class TestTranslateType:
    """Test translate_type."""

    @pytest.mark.parametrize(
        ("major", "minor", "build", "revision", "rog", "expected"),
        [
            # Unknown: missing major, minor, or build
            (None, 388, 8, None, False, ARFirmwareType.UNKNOWN),
            ((3, 0, 0, 6), None, 8, None, False, ARFirmwareType.UNKNOWN),
            ((3, 0, 0, 6), 388, None, None, False, ARFirmwareType.UNKNOWN),
            # Beta major → STOCK regardless of other fields
            ((9, 0, 0, 6), 102, 8, None, False, ARFirmwareType.STOCK),
            ((9, 0, 0, 6), 102, 8, "gnuton1", False, ARFirmwareType.STOCK),
            ((9, 0, 0, 6), 102, 8, "alpha1", False, ARFirmwareType.STOCK),
            ((9, 0, 0, 6), 102, 8, None, True, ARFirmwareType.STOCK),
            # Gnuton (must be checked before Merlin)
            ((3, 0, 0, 6), 388, 8, "gnuton1", False, ARFirmwareType.GNUTON),
            (
                (3, 0, 0, 6),
                388,
                8,
                "1-gnuton0_beta2",
                False,
                ARFirmwareType.GNUTON,
            ),
            # Merlin: alpha or beta string in revision
            ((3, 0, 0, 6), 388, 8, "alpha1", False, ARFirmwareType.MERLIN),
            ((3, 0, 0, 6), 388, 8, "beta2", False, ARFirmwareType.MERLIN),
            ((3, 0, 0, 6), 388, 8, "2beta1", False, ARFirmwareType.MERLIN),
            # Merlin: rog flag
            ((3, 0, 0, 6), 388, 8, None, True, ARFirmwareType.MERLIN),
            ((3, 0, 0, 6), 388, 8, "g8178ee0", True, ARFirmwareType.MERLIN),
            # Stock: string revision with no known markers
            ((3, 0, 0, 6), 388, 8, "g8178ee0", False, ARFirmwareType.STOCK),
            # Stock: int revision (not a Merlin marker in this function)
            ((3, 0, 0, 6), 388, 8, 2, False, ARFirmwareType.STOCK),
        ],
    )
    def test_translate_type(
        self,
        major: tuple[int, int, int, int] | None,
        minor: int | None,
        build: int | None,
        revision: int | str | None,
        rog: bool,
        expected: ARFirmwareType,
    ) -> None:
        """Test translate_type."""

        assert translate_type(major, minor, build, revision, rog) == expected


class TestTranslateString:
    """Test translate_string."""

    @pytest.fixture(autouse=True)
    def clear_warned_strings(self) -> None:
        """Clear warned strings set before each test."""

        translate_module._WARNED_FW_STRINGS.clear()

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # None / empty / sentinels
            (None, (None, None, None, None, False)),
            ("", (None, None, None, None, False)),
            ("__", (None, None, None, None, False)),
            ("___", (None, None, None, None, False)),
            ("  __  ", (None, None, None, None, False)),
            # Standard Merlin
            (
                "3.0.0.4.388.8_2",
                ((3, 0, 0, 4), 388, 8, 2, False),
            ),
            # ROG
            (
                "3.0.0.4.388.7_0_rog",
                ((3, 0, 0, 4), 388, 7, 0, True),
            ),
            # Undotted major
            (
                "3004.388.7_120",
                ((3, 0, 0, 4), 388, 7, 120, False),
            ),
            # Beta major
            (
                "9006_102_4856-g8178ee0",
                ((9, 0, 0, 6), 102, 4856, "g8178ee0", False),
            ),
            # Long stock revision
            (
                "3.0.0.6.102.34713_g0d793c1_386-g45e48",
                ((3, 0, 0, 6), 102, 34713, "g0d793c1_386-g45e48", False),
            ),
            # No major (partial)
            (".386.7_120", (None, 386, 7, 120, False)),
            # Whitespace trimmed
            (
                "  9006_102_4856-g8178ee0  ",
                ((9, 0, 0, 6), 102, 4856, "g8178ee0", False),
            ),
        ],
    )
    def test_translate_string(
        self,
        raw: str | None,
        expected: tuple[
            tuple[int, int, int, int] | None,
            int | None,
            int | None,
            int | str | None,
            bool,
        ],
    ) -> None:
        """Test translate_string."""

        assert translate_string(raw) == expected

    def test_translate_string_warns_once(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that an unparseable string warns only once."""

        invalid = "this_is_not_a_firmware_string"
        with caplog.at_level(logging.WARNING):
            translate_string(invalid)
            translate_string(invalid)

        assert caplog.text.count(invalid) == 1

    def test_translate_string_warns_per_unique(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that each unique invalid string warns once."""

        with caplog.at_level(logging.WARNING):
            translate_string("fw_unparseable_aaa")
            translate_string("fw_unparseable_bbb")

        assert "fw_unparseable_aaa" in caplog.text
        assert "fw_unparseable_bbb" in caplog.text

    def test_translate_string_partial_warns_once(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a partial string (missing major) warns only once."""

        partial = ".388.8_2"
        with caplog.at_level(logging.WARNING):
            translate_string(partial)
            translate_string(partial)

        assert caplog.text.count(partial) == 1
