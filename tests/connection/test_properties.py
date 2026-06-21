"""Tests for connection module — Connection read-only properties."""

from __future__ import annotations

import pytest

from asusrouter.config.connection import ARConnectionConfigKey as ARCCKey
from asusrouter.connection import Connection
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS
from tests.helpers import TCONST_HOST, TCONST_PASS, TCONST_USER


class TestConnectionProperties:
    """Tests for Connection read-only properties."""

    def test_config_property_returns_internal_config(self) -> None:
        """Config property is the same object as _config."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn.config is conn._config

    def test_connected_reflects_internal_flag(self) -> None:
        """Connected property mirrors _connected."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        assert conn.connected is False
        conn._connected = True
        assert conn.connected is True

    @pytest.mark.parametrize(
        ("use_ssl", "expected"),
        [(False, "http"), (True, "https")],
        ids=["http", "https"],
    )
    def test_http_scheme(self, use_ssl: bool, expected: str) -> None:
        """Http returns 'https' for SSL, 'http' otherwise."""

        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, use_ssl=use_ssl
        )
        assert conn.http == expected

    @pytest.mark.parametrize(
        ("port", "use_ssl", "expected_port"),
        [
            (None, False, DEFAULT_PORT_HTTP),
            (None, True, DEFAULT_PORT_HTTPS),
            (8080, False, 8080),
            (8553, True, 8553),
        ],
        ids=["default_http", "default_https", "custom_http", "custom_https"],
    )
    def test_port_property(
        self, port: int | None, use_ssl: bool, expected_port: int
    ) -> None:
        """Port property returns the int stored in config."""

        conn = Connection(
            TCONST_HOST, TCONST_USER, TCONST_PASS, port=port, use_ssl=use_ssl
        )
        assert conn.port == expected_port

    def test_port_property_coerces_non_int(self) -> None:
        """Port property coerces a non-int config value via safe_int_config."""

        conn = Connection(TCONST_HOST, TCONST_USER, TCONST_PASS)
        conn._config.set(ARCCKey.PORT, "not-a-number")
        assert conn.port == 0

    @pytest.mark.parametrize(
        ("hostname", "port", "use_ssl", "expected"),
        [
            (
                "router.local",
                None,
                False,
                f"http://router.local:{DEFAULT_PORT_HTTP}",
            ),
            (
                "router.local",
                None,
                True,
                f"https://router.local:{DEFAULT_PORT_HTTPS}",
            ),
            ("192.168.1.1", 8080, False, "http://192.168.1.1:8080"),
            ("192.168.1.1", 8553, True, "https://192.168.1.1:8553"),
        ],
        ids=["default_http", "default_https", "custom_http", "custom_https"],
    )
    def test_webpanel_url(
        self, hostname: str, port: int | None, use_ssl: bool, expected: str
    ) -> None:
        """Webpanel returns the full base URL for the router's admin panel."""

        conn = Connection(
            hostname, TCONST_USER, TCONST_PASS, port=port, use_ssl=use_ssl
        )
        assert conn.webpanel == expected
