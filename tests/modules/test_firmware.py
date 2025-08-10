"""Tests for the Firmware module."""

from unittest.mock import MagicMock

import pytest

from asusrouter.modules.firmware import Firmware, FirmwareType


class TestFirmware:
    """Test the Firmware class."""

    @pytest.mark.parametrize(
        ("version", "major", "minor", "build", "revision", "expected"),
        [
            (
                "3.0.0.4.388_8_2",
                None,
                None,
                None,
                None,
                {
                    "major": "3.0.0.4",
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                },
            ),
            (
                None,
                "9.0.0.6",
                102,
                4856,
                "g8178ee0",
                {
                    "major": "9.0.0.6",
                    "minor": 102,
                    "build": 4856,
                    "revision": "g8178ee0",
                },
            ),
        ],
    )
    def test_init(  # noqa: PLR0913
        self,
        version: str | None,
        major: str | None,
        minor: int | None,
        build: int | None,
        revision: str | None,
        expected: dict[str, int | str | None],
    ) -> None:
        """Test the initialization of the Firmware class."""

        fw = Firmware(
            version=version,
            major=major,
            minor=minor,
            build=build,
            revision=revision,
        )

        assert fw.major == expected["major"]
        assert fw.minor == expected["minor"]
        assert fw.build == expected["build"]
        assert fw.revision == expected["revision"]

    @pytest.mark.parametrize(
        ("major", "expected"),
        [
            ("3.0.0.4", True),
            (None, False),
        ],
    )
    def test_safe(self, major: str | None, expected: bool) -> None:
        """Test the safe method."""

        fw = Firmware(major=major)
        result = fw.safe()
        if expected:
            assert result is fw
        else:
            assert result is None

    @pytest.mark.parametrize(
        ("major", "expected_beta"),
        [
            ("9.0.0.4", True),
            ("3.0.0.4", False),
            (None, False),
        ],
    )
    def test_update_beta(self, major: str | None, expected_beta: bool) -> None:
        """Test the update beta method."""

        fw = Firmware(major=major)
        fw.beta = not expected_beta
        fw._update_beta()

        if expected_beta is not None:
            assert fw.beta == expected_beta
        else:
            assert not hasattr(fw, "beta")

    @pytest.mark.parametrize(
        ("revision", "expected_rog"),
        [
            ("123_rog", True),
            ("123", False),
        ],
    )
    def test_update_rog(
        self, revision: str | None, expected_rog: bool
    ) -> None:
        """Test the update rog method."""

        fw = Firmware()
        fw.revision = revision
        fw.rog = not expected_rog
        fw._update_rog()

        assert fw.rog == expected_rog

    @pytest.mark.parametrize(
        ("revision", "expected_source"),
        [
            # Merlin
            (0, FirmwareType.MERLIN),
            ("alpha1", FirmwareType.MERLIN),
            ("beta2", FirmwareType.MERLIN),
            ("2beta1", FirmwareType.MERLIN),
            # Gnuton
            ("gnuton", FirmwareType.GNUTON),
            ("1-gnuton0_beta2", FirmwareType.GNUTON),
            # Stock
            ("g1234567", FirmwareType.STOCK),
            ("anything", FirmwareType.STOCK),
        ],
    )
    def test_update_source(
        self, revision: str | None, expected_source: FirmwareType
    ) -> None:
        """Test the update source method."""

        fw = Firmware(revision=revision)
        fw.source = FirmwareType.UNKNOWN
        fw._update_source()

        assert fw.source == expected_source

    @pytest.mark.parametrize(
        ("fw_string", "major", "minor", "build", "revision", "rog", "beta"),
        [
            ("3.0.0.4.388.7_0_rog", "3.0.0.4", 388, 7, 0, True, False),
            ("3.0.0.4.388.8_2", "3.0.0.4", 388, 8, 2, False, False),
            ("3004.388.7_120", "3.0.0.4", 388, 7, 120, False, False),
            (
                "9006_102_4856-g8178ee0       ",
                "9.0.0.6",
                102,
                4856,
                "g8178ee0",
                False,
                True,
            ),
            (
                "3.0.0.6.102.34713_g0d793c1_386-g45e48",
                "3.0.0.6",
                102,
                34713,
                "g0d793c1_386-g45e48",
                False,
                False,
            ),
            # Additional cases
            (".386.7_120", None, 386, 7, 120, False, False),
            ("__", None, None, None, None, False, False),
            # Invalid input
            ("", None, None, None, None, False, False),
            ("invalid", None, None, None, None, False, False),
        ],
    )
    def test_from_string(  # noqa: PLR0913
        self,
        fw_string: str | None,
        major: str | None,
        minor: int | None,
        build: int | None,
        revision: str | None,
        rog: bool,
        beta: bool,
    ) -> None:
        """Test the from string method."""

        fw = Firmware()
        fw.from_string(fw_string)

        assert fw.major == major
        assert fw.minor == minor
        assert fw.build == build
        assert fw.revision == revision
        assert fw.rog == rog
        assert fw.beta == beta

    @pytest.mark.parametrize(
        ("major", "minor", "build", "revision", "expected_str"),
        [
            ("1", "0", "0", "1234", "1.0.0_1234"),
            ("2", "1", "3", "5678_rog", "2.1.3_5678_rog"),
        ],
    )
    def test_str(
        self,
        major: str | None,
        minor: int | None,
        build: int | None,
        revision: str | None,
        expected_str: str | None,
    ) -> None:
        """Test the string representation of the Firmware class."""

        fw = Firmware(major=major, minor=minor, build=build, revision=revision)
        assert str(fw) == expected_str

    @pytest.mark.parametrize(
        ("major", "minor", "build", "revision", "expected_repr"),
        [
            ("1", "0", "0", "1234", "1.0.0_1234"),
            ("2", "1", "3", "5678_rog", "2.1.3_5678_rog"),
        ],
    )
    def test_repr(
        self,
        major: str | None,
        minor: int | None,
        build: int | None,
        revision: str | None,
        expected_repr: str | None,
    ) -> None:
        """Test the string representation of the Firmware class."""

        fw = Firmware(major=major, minor=minor, build=build, revision=revision)
        assert repr(fw) == expected_repr

    @pytest.mark.parametrize(
        ("fw1", "fw2", "expected"),
        [
            # Major version
            (Firmware(major="3.0.0.4"), Firmware(major="3.0.0.4"), True),
            (Firmware(major="3.0.0.4"), Firmware(major="3.0.0.6"), False),
            # Minor version
            (Firmware(minor=1), Firmware(minor=1), True),
            (Firmware(minor=1), Firmware(minor=2), False),
            # Build version
            (Firmware(build=1), Firmware(build=1), True),
            (Firmware(build=1), Firmware(build=2), False),
            # Revision
            (Firmware(revision=1), Firmware(revision=1), True),
            (Firmware(revision=1), Firmware(revision=2), False),
            # Anything but Firmware
            (Firmware(), None, False),
            (Firmware(), "invalid", False),
        ],
    )
    def test_eq(
        self, fw1: FirmwareType, fw2: FirmwareType, expected: bool
    ) -> None:
        """Test the equal operator."""

        assert (fw1 == fw2) == expected

    @pytest.mark.parametrize(
        ("fw1", "fw2", "expected"),
        [
            # Major version
            ("3.0.0.4.123.4_5", "3.0.0.6.123.4_5", True),
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_5", False),
            ("3.0.0.6.123.4_5", "3.0.0.4.123.4_5", False),
            # Beta digit should not matter
            ("3.0.0.4.123.4_5", "9.0.0.4.123.4_5", False),
            # Minor version
            ("3.0.0.4.123.4_5", "3.0.0.4.124.4_5", True),
            ("3.0.0.4.124.4_5", "3.0.0.4.123.4_5", False),
            # Build version
            ("3.0.0.4.123.4_5", "3.0.0.4.123.5_5", True),
            ("3.0.0.4.123.5_5", "3.0.0.4.123.4_5", False),
            # Revision
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_6", True),
            ("3.0.0.4.123.4_6", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.4_5abc6", "3.0.0.4.123.4_5abc7", True),
            ("3.0.0.4.123.4_5abc6", "3.0.0.4.123.4_5abc6", False),
            ("3.0.0.4.123.4_5abc7", "3.0.0.4.123.4_5abc6", False),
            # Other important cases
            # Flip in m<m b>b
            ("3.0.0.4.124.3.5", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.4_5", "3.0.0.4.124.3.5", True),
            # Some actual cases
            (
                "3.0.0.4.388.24121_ge887338",
                "9.0.0.4.386.56742_g5d0e718",
                False,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.23759_gfd1c030",
                "9.0.0.4.386.56742_g5d0e718",
                False,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.23759_gfd1c030",
                "3.0.0.4.388.8_0",
                False,  # cannot compare stock and Merlin
            ),
            (
                "3.0.0.4.388.8_0",
                "3.0.0.4.388.23759_gfd1c030",
                False,  # cannot compare stock and Merlin
            ),
            # Beta / alpha cases
            (
                "3.0.0.4.388.8_0",
                "3.0.0.4.388.8_beta1",
                False,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.8_beta1",
                "3.0.0.4.388.8_0",
                True,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.8_1",
                "3.0.0.4.388.8_1alpha1",
                False,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.8_1alpha1",
                "3.0.0.4.388.8_1",
                True,  # beta is less than non-beta
            ),
            (
                "3.0.0.4.388.8_1beta1",
                "3.0.0.4.388.8_0",
                False,  # beta of rev 1 is less than rev 0
            ),
            (
                "3.0.0.4.388.8_0",
                "3.0.0.4.388.8_1beta1",
                True,  # beta of rev 1 is less than rev 0
            ),
            # Anything but Firmware
            ("3.0.0.4.123.4_5", None, False),
            ("3.0.0.4.123.4_5", "invalid", False),
        ],
    )
    def test_lt(
        self, fw1: FirmwareType, fw2: FirmwareType, expected: bool
    ) -> None:
        """Test the less than operator."""

        fw1 = Firmware(fw1)
        fw2 = Firmware(fw2)

        assert (fw1 < fw2) == expected

    @pytest.mark.parametrize(
        ("fw1", "fw2", "expected"),
        [
            (
                "3.0.0.4.388.5_1",
                "3.0.0.4.388.5_1a1",
                True,
            ),
            (
                "3.0.0.4.388.5_1a1",
                "3.0.0.4.388.5_1",
                False,
            ),
        ],
    )
    def test_lt_unreachable(
        self, fw1: FirmwareType, fw2: FirmwareType, expected: bool
    ) -> None:
        """Test the less than operator with unreachable cases."""

        fw1 = Firmware(fw1)
        fw2 = Firmware(fw2)

        # Rewrite source attribute
        fw1.source = FirmwareType.STOCK
        fw2.source = FirmwareType.STOCK

        assert (fw1 < fw2) == expected

    @pytest.mark.parametrize(
        ("fw2", "expected"),
        [
            (None, False),
            ("invalid", False),
            (Firmware(), False),
            (Firmware(major="3.0.0.4"), False),
            (Firmware(major="3.0.0.4", minor=123), False),
            (Firmware(major="3.0.0.4", minor=123, build=4), False),
            (Firmware(major="3.0.0.4", minor=123, build=4, revision=5), False),
        ],
    )
    def test_lt_invalid(self, fw2: FirmwareType, expected: bool) -> None:
        """Test the less than operator with invalid input."""

        fw1 = Firmware("3.0.0.4.123.4_g5")

        assert (fw1 < fw2) == expected

    @pytest.mark.parametrize(
        ("lt", "ne", "expected"),
        [
            (False, False, False),
            (True, False, False),
            (False, True, True),
            (True, True, False),
        ],
    )
    def test_gt(self, lt: bool, ne: bool, expected: bool) -> None:
        """Test the greater-than method."""

        fw1 = Firmware()
        fw2 = Firmware()

        # Mock __lt__ and __ne__ methods
        fw1.__lt__ = MagicMock(return_value=lt)
        fw1.__ne__ = MagicMock(return_value=ne)

        # Call
        result = fw1 > fw2

        # Check results
        fw1.__lt__.assert_called_once_with(fw2)
        if lt:
            fw1.__ne__.assert_not_called()
        else:
            fw1.__ne__.assert_called_once_with(fw2)
        assert result == expected
