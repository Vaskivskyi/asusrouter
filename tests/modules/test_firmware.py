"""Tests for the Firmware module."""

from unittest.mock import MagicMock

import pytest
from asusrouter.modules.firmware import Firmware


class TestFirmware:
    """Test the Firmware class."""

    @pytest.mark.parametrize(
        "version, major, minor, build, revision, rog, beta, expected",
        [
            (
                "3.0.0.4.388_8_2",
                None,
                None,
                None,
                None,
                False,
                False,
                {
                    "major": "3.0.0.4",
                    "minor": 388,
                    "build": 8,
                    "revision": 2,
                    "rog": False,
                    "beta": False,
                },
            ),
            (
                None,
                "9.0.0.6",
                102,
                4856,
                "g8178ee0",
                False,
                False,
                {
                    "major": "9.0.0.6",
                    "minor": 102,
                    "build": 4856,
                    "revision": "g8178ee0",
                    "rog": False,
                    "beta": True,
                },
            ),
        ],
    )
    def test_init(
        self, version, major, minor, build, revision, rog, beta, expected
    ):
        """Test the initialization of the Firmware class."""

        fw = Firmware(
            version=version,
            major=major,
            minor=minor,
            build=build,
            revision=revision,
            rog=rog,
            beta=beta,
        )

        assert fw.major == expected["major"]
        assert fw.minor == expected["minor"]
        assert fw.build == expected["build"]
        assert fw.revision == expected["revision"]
        assert fw.rog == expected["rog"]
        assert fw.beta == expected["beta"]

    @pytest.mark.parametrize(
        "major, expected",
        [
            ("3.0.0.4", True),
            (None, False),
        ],
    )
    def test_safe(self, major, expected):
        """Test the safe method."""

        fw = Firmware(major=major)
        result = fw.safe()
        if expected:
            assert result is fw
        else:
            assert result is None

    @pytest.mark.parametrize(
        "major, expected_beta",
        [
            ("9.0.0.4", True),
            ("3.0.0.4", False),
            (None, False),
        ],
    )
    def test_update_beta(self, major, expected_beta):
        """Test the update beta method."""

        fw = Firmware(major=major, beta=False)
        fw._update_beta()

        if expected_beta is not None:
            assert fw.beta == expected_beta
        else:
            assert not hasattr(fw, "beta")

    @pytest.mark.parametrize(
        "fw_string, major, minor, build, revision, rog, beta",
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
            # Invalid input
            ("", None, None, None, None, False, False),
            ("invalid", None, None, None, None, False, False),
        ],
    )
    def test_from_string(
        self, fw_string, major, minor, build, revision, rog, beta
    ):
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
        "major, minor, build, revision, rog, expected_str",
        [
            ("1", "0", "0", "1234", False, "1.0.0_1234"),
            ("2", "1", "3", "5678", True, "2.1.3_5678_rog"),
        ],
    )
    def test_str(self, major, minor, build, revision, rog, expected_str):
        """Test the string representation of the Firmware class."""

        fw = Firmware(
            major=major, minor=minor, build=build, revision=revision, rog=rog
        )
        assert str(fw) == expected_str

    @pytest.mark.parametrize(
        "major, minor, build, revision, rog, expected_repr",
        [
            ("1", "0", "0", "1234", False, "1.0.0_1234"),
            ("2", "1", "3", "5678", True, "2.1.3_5678_rog"),
        ],
    )
    def test_repr(self, major, minor, build, revision, rog, expected_repr):
        """Test the string representation of the Firmware class."""

        fw = Firmware(
            major=major, minor=minor, build=build, revision=revision, rog=rog
        )
        assert repr(fw) == expected_repr

    @pytest.mark.parametrize(
        "fw1, fw2, expected",
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
            # ROG flag should not matter
            (Firmware(rog=True), Firmware(rog=True), True),
            (Firmware(rog=True), Firmware(rog=False), True),
            # Beta flag should not matter
            (Firmware(beta=True), Firmware(beta=True), True),
            (Firmware(beta=True), Firmware(beta=False), True),
            # Anything but Firmware
            (Firmware(), None, False),
            (Firmware(), "invalid", False),
        ],
    )
    def test_eq(self, fw1, fw2, expected):
        """Test the equal operator."""

        assert (fw1 == fw2) == expected

    @pytest.mark.parametrize(
        "fw1, fw2, expected",
        [
            # Major version
            ("3.0.0.4.123.4_5", "3.0.0.6.123.4_5", True),
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_5", False),
            ("3.0.0.6.123.4_5", "3.0.0.4.123.4_5", False),
            # Beta digit should not matter
            ("3.0.0.4.123.4_5", "9.0.0.4.123.4_5", False),
            # Minor version
            ("3.0.0.4.123.4_5", "3.0.0.4.124.4_5", True),
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.124.4_5", "3.0.0.4.123.4_5", False),
            # Build version
            ("3.0.0.4.123.4_5", "3.0.0.4.123.5_5", True),
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.5_5", "3.0.0.4.123.4_5", False),
            # Revision
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_6", True),
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.4_6", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.4_5abc6", "3.0.0.4.123.4_5abc7", True),
            ("3.0.0.4.123.4_5abc6", "3.0.0.4.123.4_5abc6", False),
            ("3.0.0.4.123.4_5abc7", "3.0.0.4.123.4_5abc6", False),
            # Other important cases
            # Flip in m<m b>b
            ("3.0.0.4.124.3.5", "3.0.0.4.123.4_5", False),
            ("3.0.0.4.123.4_5", "3.0.0.4.124.3.5", True),
            # Different types: int vs str
            ("3.0.0.4.123.4_5", "3.0.0.4.123.4_6beta1", True),
            ("3.0.0.4.123.4_6beta1", "3.0.0.4.123.4_5", False),
            # Anything but Firmware
            ("3.0.0.4.123.4_5", None, False),
            ("3.0.0.4.123.4_5", "invalid", False),
        ],
    )
    def test_lt(self, fw1, fw2, expected):
        """Test the less than operator."""

        fw1 = Firmware(fw1)
        fw2 = Firmware(fw2)

        assert (fw1 < fw2) == expected

    @pytest.mark.parametrize(
        "fw2, expected",
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
    def test_lt_invalid(self, fw2, expected):
        """Test the less than operator with invalid input."""

        fw1 = Firmware("3.0.0.4.123.4_5")

        assert (fw1 < fw2) == expected

    @pytest.mark.parametrize(
        "lt, ne, expected",
        [
            (False, False, False),
            (True, False, False),
            (False, True, True),
            (True, True, False),
        ],
    )
    def test_gt(self, lt, ne, expected):
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
