"""Tests for sensitive value classification and rendering."""

from __future__ import annotations

import pytest

from asusrouter.tools.identifiers import IpAddress, MacAddress, Password, Ssid
from asusrouter.tools.security import (
    REDACTED,
    REDACTED_STR,
    ARSecurityLevel,
    render,
)
from asusrouter.tools.security.sensitive import ARSensitive, _Redacted

_MAC = "aa:bb:cc:11:22:33"
_IP = "192.168.1.10"
_SSID = "my-network"
_PASSWORD = "s3cr3t"


class TestRedacted:
    """Tests for the redaction marker."""

    def test_singleton(self) -> None:
        """Test that the marker is a singleton."""

        assert _Redacted() is REDACTED

    def test_str_and_repr(self) -> None:
        """Test the string and repr forms."""

        assert str(REDACTED) == REDACTED_STR
        assert str(REDACTED) == "-=REDACTED=-"
        assert repr(REDACTED) == "<redacted>"


class TestARSensitiveBase:
    """Tests for the ARSensitive base defaults."""

    def test_defaults(self) -> None:
        """Test the base class defaults."""

        assert ARSensitive.reveal_level is ARSecurityLevel.UNSAFE
        assert ARSensitive.maskable is False

    def test_default_mask(self) -> None:
        """Test that the base mask returns the redaction marker."""

        assert ARSensitive().mask() is REDACTED


class TestRenderPassthrough:
    """Tests for rendering non-sensitive values."""

    @pytest.mark.parametrize("value", ["plain", 42, None])
    def test_non_sensitive_passthrough(self, value: object) -> None:
        """Non-sensitive values pass through unchanged at any level."""

        assert render(value, ARSecurityLevel.STRICT) is value


class TestRenderMatrix:
    """Tests for rendering sensitive values across levels."""

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            # SSID reveals from DEFAULT, never maskable
            (ARSecurityLevel.STRICT, "redacted"),
            (ARSecurityLevel.DEFAULT, "raw"),
            (ARSecurityLevel.SANITIZED, "raw"),
            (ARSecurityLevel.REASONABLE, "raw"),
            (ARSecurityLevel.UNSAFE, "raw"),
        ],
    )
    def test_ssid(self, level: ARSecurityLevel, expected: str) -> None:
        """Test SSID rendering."""

        ssid = Ssid(_SSID)
        result = render(ssid, level)
        if expected == "raw":
            assert result is ssid
        else:
            assert result is REDACTED

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (ARSecurityLevel.STRICT, "redacted"),
            (ARSecurityLevel.DEFAULT, "redacted"),
            (ARSecurityLevel.SANITIZED, "masked"),
            (ARSecurityLevel.REASONABLE, "raw"),
            (ARSecurityLevel.UNSAFE, "raw"),
        ],
    )
    def test_mac(self, level: ARSecurityLevel, expected: str) -> None:
        """Test MAC rendering."""

        mac = MacAddress.from_value(_MAC)
        result = render(mac, level)
        if expected == "raw":
            assert result is mac
        elif expected == "masked":
            assert isinstance(result, MacAddress)
            assert result == mac.mask()
            assert result != mac
        else:
            assert result is REDACTED

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (ARSecurityLevel.STRICT, "redacted"),
            (ARSecurityLevel.DEFAULT, "redacted"),
            (ARSecurityLevel.SANITIZED, "masked"),
            (ARSecurityLevel.REASONABLE, "raw"),
            (ARSecurityLevel.UNSAFE, "raw"),
        ],
    )
    def test_ip(self, level: ARSecurityLevel, expected: str) -> None:
        """Test IP rendering."""

        ip = IpAddress.from_value(_IP)
        result = render(ip, level)
        if expected == "raw":
            assert result is ip
        elif expected == "masked":
            assert isinstance(result, IpAddress)
            assert result == ip.mask()
            assert result != ip
        else:
            assert result is REDACTED

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (ARSecurityLevel.STRICT, "redacted"),
            (ARSecurityLevel.DEFAULT, "redacted"),
            (ARSecurityLevel.SANITIZED, "redacted"),
            (ARSecurityLevel.REASONABLE, "redacted"),
            (ARSecurityLevel.UNSAFE, "raw"),
        ],
    )
    def test_password(self, level: ARSecurityLevel, expected: str) -> None:
        """Test password rendering - never masked, only raw at UNSAFE."""

        password = Password(_PASSWORD)
        result = render(password, level)
        if expected == "raw":
            assert result is password
        else:
            assert result is REDACTED
