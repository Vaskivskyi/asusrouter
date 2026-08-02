"""Tests for the system init event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.init import PATTERNS, AREventInit
from asusrouter.tools.identifiers import MacAddress, Serial
from tests.modules.log.translate import IDENTIFIER, classified, unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw init message."""

    return PATTERNS.translate(content)


class TestTranslateInit:
    """The per-program dispatcher."""

    def test_firmware_banner(self) -> None:
        """The banner names this device, so both values are typed."""

        content = (
            "fwver: 3.0.0.6_102_34735 "
            "(sn:R2FAKE000000ABC /ha:C8:7F:54:00:00:01 )"
        )

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventInit.FIRMWARE_BANNER,
            _KEY.RAW: classified(content, IDENTIFIER),
            _KEY.VERSION: "3.0.0.6_102_34735",
            _KEY.DEVICE_SERIAL: Serial("R2FAKE000000ABC"),
            _KEY.DEVICE_MAC: MacAddress("C8:7F:54:00:00:01"),
        }

    def test_banner_without_hardware(self) -> None:
        """A banner naming only the firmware still reports the version."""

        event = _translate("fwver: 3.0.0.4_388_24333-ga030aaf")

        assert event[_KEY.VERSION] == "3.0.0.4_388_24333-ga030aaf"
        assert _KEY.DEVICE_SERIAL not in event
        assert _KEY.DEVICE_MAC not in event

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future init message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventInit.UNKNOWN,
            _KEY.RAW: unread(content),
        }
