"""Tests for the avahi daemon event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.avahi_daemon import (
    PATTERNS,
    AREventAvahiDaemon,
)
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw avahi-daemon message."""

    return PATTERNS.translate(content)


class TestTranslateAvahiDaemon:
    """The per-program dispatcher."""

    def test_alias_established(self) -> None:
        """The announced mDNS alias is extracted."""

        content = 'Alias name "RT-FAKE1" successfully established.'

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAvahiDaemon.ALIAS_ESTABLISHED,
            _KEY.RAW: content,
            _KEY.ALIAS: "RT-FAKE1",
        }

    def test_nss_unsupported(self) -> None:
        """The startup warning is recognized."""

        content = (
            "WARNING: No NSS support for mDNS detected, "
            "consider installing nss-mdns!"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAvahiDaemon.NSS_UNSUPPORTED,
            _KEY.RAW: content,
        }

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future avahi message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventAvahiDaemon.UNKNOWN,
            _KEY.RAW: unread(content),
        }
