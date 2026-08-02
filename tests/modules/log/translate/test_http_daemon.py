"""Tests for the HTTP daemon event translation."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from asusrouter.modules.common.api import ARApiClient
from asusrouter.modules.common.status import ARStatusCode
from asusrouter.modules.connection import ARConnection
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.http_daemon import (
    PATTERNS,
    AREventHttpDaemon,
)
from asusrouter.tools.identifiers import IpAddress
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey
_IP = "192.168.1.100"


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw HTTP daemon message."""

    return PATTERNS.translate(content)


class TestCertificate:
    """SSL certificate message translation."""

    def test_generate(self) -> None:
        """Generate extracts the port."""

        content = "Generating SSL certificate...8443"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.CERTIFICATE_GENERATE,
            _KEY.RAW: content,
            _KEY.PORT: 8443,
        }

    def test_info(self) -> None:
        """Info extracts subject, issuer, serial and validity dates."""

        content = (
            "S:RT-AX88U-6D90 Server Certificate, "
            "I:GT-BE19000AI-53A0 Root Certificate 20240101000111, "
            "2018/5/5 ~ 2045/12/29"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.CERTIFICATE_INFO,
            _KEY.RAW: content,
            _KEY.SUBJECT: "RT-AX88U-6D90",
            _KEY.ISSUER: "GT-BE19000AI-53A0",
            _KEY.SERIAL: "20240101000111",
            _KEY.VALID_FROM: date(2018, 5, 5),
            _KEY.VALID_TO: date(2045, 12, 29),
        }

    @pytest.mark.parametrize("bad", ["2018/13/40", "2018/12"])
    def test_info_bad_date_omitted(self, bad: str) -> None:
        """A wrong-shape or calendar-invalid date is left out (other kept)."""

        content = (
            f"S:X Server Certificate, I:Y Root Certificate 1, "
            f"{bad} ~ 2045/12/29"
        )

        event = _translate(content)

        assert _KEY.VALID_FROM not in event
        assert event[_KEY.VALID_TO] == date(2045, 12, 29)

    def test_init_success(self) -> None:
        """Init carries port and a success status (`Succeed` word)."""

        content = "Succeed to init SSL certificate...8443"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.CERTIFICATE_INIT,
            _KEY.RAW: content,
            _KEY.STATUS: ARStatusCode.SUCCESS,
            _KEY.PORT: 8443,
        }

    def test_reload(self) -> None:
        """Reload has no port or status."""

        content = "reload cert and clean all files"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.CERTIFICATE_RELOAD,
            _KEY.RAW: content,
        }

    def test_restore(self) -> None:
        """Restore extracts the port after the literal `...`."""

        content = "Restore saved SSL certificate...8443"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.CERTIFICATE_RESTORE,
            _KEY.RAW: content,
            _KEY.PORT: 8443,
        }


class TestLogin:
    """Login message translation."""

    def test_success_app_http(self) -> None:
        """A successful app login over http parses every field."""

        content = f"[LOGIN][http][APP] successed ({_IP})"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.LOGIN,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.CONNECTION: ARConnection.HTTP,
            _KEY.API_CLIENT: ARApiClient.APP,
            _KEY.STATUS: ARStatusCode.SUCCESS,
            _KEY.CLIENT_IP: IpAddress.from_value(_IP),
        }

    def test_failed_web_https(self) -> None:
        """A failed web login over https maps status and client correctly."""

        event = _translate(f"[LOGIN][https][Web] failed ({_IP})")

        assert event[_KEY.CONNECTION] is ARConnection.HTTPS
        assert event[_KEY.API_CLIENT] is ARApiClient.WEB
        assert event[_KEY.STATUS] is ARStatusCode.FAIL

    def test_unknown_status(self) -> None:
        """An unexpected status word maps to UNKNOWN."""

        content = f"[LOGIN][http][APP] pending ({_IP})"

        assert _translate(content)[_KEY.STATUS] is ARStatusCode.UNKNOWN


class TestTranslateHttpDaemon:
    """The per-program dispatcher."""

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future httpd message"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventHttpDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
