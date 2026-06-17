"""Tests for the ARFirmware class."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.firmware import ARFirmware, _compare_revision
from asusrouter.modules.firmware.flag import ARFirmwareType

# Canonical instances reused across comparison / equality test cases
_UNKNOWN_FW = ARFirmware()
_STOCK_BASE = ARFirmware((3, 0, 0, 4), 388, 8, "gA")
_STOCK_COPY = ARFirmware((3, 0, 0, 4), 388, 8, "gA")
_STOCK_BIG_MAJOR = ARFirmware((3, 0, 0, 6), 388, 8, "gA")
_STOCK_BIG_MINOR = ARFirmware((3, 0, 0, 4), 390, 8, "gA")
_STOCK_BIG_BUILD = ARFirmware((3, 0, 0, 4), 388, 10, "gA")
_STOCK_ALT_REV = ARFirmware((3, 0, 0, 4), 388, 8, "gB")
_STOCK_NO_REV = ARFirmware((3, 0, 0, 4), 388, 8)
_MERLIN_BASE = ARFirmware((3, 0, 0, 4), 388, 8, 2, True)
_MERLIN_BIG_REV = ARFirmware((3, 0, 0, 4), 388, 8, 7, True)
_MERLIN_NO_ROG = ARFirmware((3, 0, 0, 4), 388, 8, 2, False)


class TestCompareRevision:
    """Test _compare_revision helper."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (None, "abc", True),
            (None, 5, True),
            ("abc", None, False),
            (5, None, False),
            (2, 5, True),
            (5, 2, False),
            (2, 2, False),
            ("abc", "abd", True),
            ("abd", "abc", False),
            ("abc", "abc", False),
            (2, "abc", True),
            ("abc", 2, False),
        ],
    )
    def test_compare_revision(
        self, a: int | str | None, b: int | str | None, expected: bool
    ) -> None:
        """Test _compare_revision."""

        assert _compare_revision(a, b) == expected


class TestARFirmwareInit:
    """Test ARFirmware initialization and properties."""

    @pytest.mark.parametrize(
        (
            "kwargs",
            "expected_major",
            "expected_minor",
            "expected_build",
            "expected_revision",
            "expected_rog",
            "expected_type",
        ),
        [
            (
                {},
                None,
                None,
                None,
                None,
                False,
                ARFirmwareType.UNKNOWN,
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": "g8178ee0",
                },
                (3, 0, 0, 4),
                388,
                8,
                "g8178ee0",
                False,
                ARFirmwareType.STOCK,
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                    "rog": True,
                },
                (3, 0, 0, 4),
                388,
                8,
                2,
                True,
                ARFirmwareType.MERLIN,
            ),
            (
                {
                    "major": (9, 0, 0, 6),
                    "minor": 102,
                    "build": 4856,
                    "revision": "g8178ee0",
                },
                (9, 0, 0, 6),
                102,
                4856,
                "g8178ee0",
                False,
                ARFirmwareType.STOCK,
            ),
            (
                {
                    "major": (3, 0, 0, 6),
                    "minor": 388,
                    "build": 8,
                    "revision": "gnuton1",
                },
                (3, 0, 0, 6),
                388,
                8,
                "gnuton1",
                False,
                ARFirmwareType.GNUTON,
            ),
        ],
    )
    def test_init(
        self,
        kwargs: dict[str, Any],
        expected_major: tuple[int, int, int, int] | None,
        expected_minor: int | None,
        expected_build: int | None,
        expected_revision: int | str | None,
        expected_rog: bool,
        expected_type: ARFirmwareType,
    ) -> None:
        """Test initialization stores all fields and derives firmware_type."""

        fw = ARFirmware(**kwargs)
        assert fw.major == expected_major
        assert fw.minor == expected_minor
        assert fw.build == expected_build
        assert fw.revision == expected_revision
        assert fw.rog == expected_rog
        assert fw.firmware_type == expected_type


class TestARFirmwareFromNvram:
    """Test ARFirmware.from_nvram."""

    @pytest.mark.parametrize(
        ("fw_major", "fw_minor", "fw_build", "expected_attrs"),
        [
            (
                "3.0.0.4",
                388,
                "40456_g8178ee0",
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 40456,
                    "revision": "g8178ee0",
                    "rog": False,
                    "firmware_type": ARFirmwareType.STOCK,
                },
            ),
            (
                "3.0.0.4",
                388,
                "8_2_rog",
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                    "rog": True,
                    "firmware_type": ARFirmwareType.MERLIN,
                },
            ),
            (
                "9.0.0.6",
                "102",
                "4856_g8178ee0",
                {
                    "major": (9, 0, 0, 6),
                    "minor": 102,
                    "build": 4856,
                    "revision": "g8178ee0",
                    "rog": False,
                    "firmware_type": ARFirmwareType.STOCK,
                },
            ),
            (
                None,
                None,
                None,
                {
                    "major": None,
                    "minor": None,
                    "build": None,
                    "revision": None,
                    "rog": False,
                    "firmware_type": ARFirmwareType.UNKNOWN,
                },
            ),
        ],
    )
    def test_from_nvram(
        self,
        fw_major: Any,
        fw_minor: Any,
        fw_build: Any,
        expected_attrs: dict[str, Any],
    ) -> None:
        """Test from_nvram builds correct ARFirmware."""

        fw = ARFirmware.from_nvram(fw_major, fw_minor, fw_build)
        for attr, value in expected_attrs.items():
            assert getattr(fw, attr) == value


class TestARFirmwareFromString:
    """Test ARFirmware.from_string."""

    @pytest.mark.parametrize(
        ("fw_string", "expected_attrs"),
        [
            (
                "3.0.0.4.388.40456_g8178ee0",
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 40456,
                    "revision": "g8178ee0",
                    "rog": False,
                    "firmware_type": ARFirmwareType.STOCK,
                },
            ),
            (
                "3.0.0.4.388.8_2_rog",
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                    "rog": True,
                    "firmware_type": ARFirmwareType.MERLIN,
                },
            ),
            (
                "9006_102_4856-g8178ee0",
                {
                    "major": (9, 0, 0, 6),
                    "minor": 102,
                    "build": 4856,
                    "revision": "g8178ee0",
                    "rog": False,
                    "firmware_type": ARFirmwareType.STOCK,
                },
            ),
            (
                None,
                {
                    "major": None,
                    "minor": None,
                    "build": None,
                    "revision": None,
                    "rog": False,
                    "firmware_type": ARFirmwareType.UNKNOWN,
                },
            ),
            (
                "",
                {
                    "major": None,
                    "minor": None,
                    "build": None,
                    "revision": None,
                    "rog": False,
                    "firmware_type": ARFirmwareType.UNKNOWN,
                },
            ),
        ],
    )
    def test_from_string(
        self,
        fw_string: str | None,
        expected_attrs: dict[str, Any],
    ) -> None:
        """Test from_string builds correct ARFirmware."""

        fw = ARFirmware.from_string(fw_string)
        for attr, value in expected_attrs.items():
            assert getattr(fw, attr) == value


class TestARFirmwareStr:
    """Test ARFirmware.__str__ and __repr__."""

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 40456,
                    "revision": "g8178ee0",
                },
                "3.0.0.4.388.40456_g8178ee0",
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                    "rog": True,
                },
                "3.0.0.4.388.8_2_rog",
            ),
            (
                {"minor": 388, "build": 8, "revision": "g8178ee0"},
                "{}.388.8_g8178ee0",
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "build": 8,
                    "revision": "g8178ee0",
                },
                "3.0.0.4.{}.8_g8178ee0",
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "revision": "g8178ee0",
                },
                "3.0.0.4.388.{}_g8178ee0",
            ),
            (
                {"major": (3, 0, 0, 4), "minor": 388, "build": 8},
                "3.0.0.4.388.8_{}",
            ),
            (
                {},
                "{}.{}.{}_{}",
            ),
            (
                {
                    "major": (3, 0, 0, 4),
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                },
                "3.0.0.4.388.8_2",
            ),
        ],
    )
    def test_str(self, kwargs: dict[str, Any], expected: str) -> None:
        """Test __str__."""

        assert str(ARFirmware(**kwargs)) == expected

    def test_repr_equals_str(self) -> None:
        """Test __repr__ delegates to __str__."""

        fw = ARFirmware((3, 0, 0, 4), 388, 8, "g8178ee0")
        assert repr(fw) == str(fw)


class TestARFirmwareHash:
    """Test ARFirmware.__hash__."""

    def test_equal_objects_same_hash(self) -> None:
        """Equal objects must produce the same hash."""

        assert hash(_STOCK_BASE) == hash(_STOCK_COPY)

    def test_rog_flag_changes_hash(self) -> None:
        """Different rog flag must produce a different hash."""

        assert hash(_MERLIN_BASE) != hash(_MERLIN_NO_ROG)

    def test_different_revision_changes_hash(self) -> None:
        """Different revision must produce a different hash."""

        assert hash(_STOCK_BASE) != hash(_STOCK_ALT_REV)

    def test_hash_stability(self) -> None:
        """Same object must hash consistently."""

        assert hash(_STOCK_BASE) == hash(_STOCK_BASE)


class TestARFirmwareEq:
    """Test ARFirmware.__eq__."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (_STOCK_BASE, _STOCK_COPY, True),
            (_STOCK_BASE, _STOCK_BIG_MAJOR, False),
            (_STOCK_BASE, _STOCK_BIG_MINOR, False),
            (_STOCK_BASE, _STOCK_BIG_BUILD, False),
            (_STOCK_BASE, _STOCK_ALT_REV, False),
            (_MERLIN_BASE, _MERLIN_NO_ROG, False),
            (_UNKNOWN_FW, _UNKNOWN_FW, True),
        ],
    )
    def test_eq(
        self,
        a: ARFirmware,
        b: ARFirmware,
        expected: bool,
    ) -> None:
        """Test __eq__."""

        assert (a == b) == expected

    def test_eq_not_implemented_for_non_firmware(self) -> None:
        """Test __eq__ returns NotImplemented for non-ARFirmware objects."""

        assert _STOCK_BASE.__eq__("not_a_firmware") is NotImplemented


class TestARFirmwareLt:
    """Test ARFirmware.__lt__."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            # Different firmware types → False both ways
            (_STOCK_BASE, _MERLIN_BASE, False),
            (_MERLIN_BASE, _STOCK_BASE, False),
            # Same UNKNOWN type, all equal → False
            (_UNKNOWN_FW, _UNKNOWN_FW, False),
            # Different major (compared by [1:])
            (_STOCK_BASE, _STOCK_BIG_MAJOR, True),
            (_STOCK_BIG_MAJOR, _STOCK_BASE, False),
            # Different minor
            (_STOCK_BIG_MINOR, _STOCK_BASE, False),
            (_STOCK_BASE, _STOCK_BIG_MINOR, True),
            # Different build
            (_STOCK_BASE, _STOCK_BIG_BUILD, True),
            (_STOCK_BIG_BUILD, _STOCK_BASE, False),
            # Different revision (int, Merlin)
            (_MERLIN_BASE, _MERLIN_BIG_REV, True),
            (_MERLIN_BIG_REV, _MERLIN_BASE, False),
            # Different revision (str, Stock)
            (_STOCK_BASE, _STOCK_ALT_REV, True),
            # Revision None vs non-None (None is less)
            (_STOCK_NO_REV, _STOCK_BASE, True),
            (_STOCK_BASE, _STOCK_NO_REV, False),
            # Equal → False
            (_STOCK_BASE, _STOCK_COPY, False),
        ],
    )
    def test_lt(
        self,
        a: ARFirmware,
        b: ARFirmware,
        expected: bool,
    ) -> None:
        """Test __lt__."""

        assert (a < b) == expected

    def test_lt_not_implemented_for_non_firmware(self) -> None:
        """Test __lt__ returns NotImplemented for non-ARFirmware objects."""

        assert _STOCK_BASE.__lt__("not_a_firmware") is NotImplemented


class TestARFirmwareGt:
    """Test ARFirmware.__gt__."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (_STOCK_BIG_MAJOR, _STOCK_BASE, True),
            (_STOCK_BASE, _STOCK_BIG_MAJOR, False),
            (_STOCK_BASE, _STOCK_COPY, False),
            (_STOCK_BASE, _MERLIN_BASE, False),
        ],
    )
    def test_gt(
        self,
        a: ARFirmware,
        b: ARFirmware,
        expected: bool,
    ) -> None:
        """Test __gt__."""

        assert (a > b) == expected

    def test_gt_not_implemented_for_non_firmware(self) -> None:
        """Test __gt__ returns NotImplemented for non-ARFirmware objects."""

        assert _STOCK_BASE.__gt__("not_a_firmware") is NotImplemented
