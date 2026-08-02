"""Tests for the WiFi scheduler event translation."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.wifi_scheduler import (
    PATTERNS,
    AREventWifiScheduler,
)
from asusrouter.tools.identifiers import WiFiInterface
from tests.modules.log.translate import unread

_KEY = AREventKey


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw wifi scheduler message."""

    return PATTERNS.translate(content)


class TestTranslateWifiScheduler:
    """The per-program dispatcher."""

    def test_radio_on(self) -> None:
        """The two indices name the interface they belong to."""

        content = "Turn radio [band_index=0, subunit=2] on."

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWifiScheduler.RADIO_ON,
            _KEY.RAW: content,
            _KEY.WL_ID: WiFiInterface(0, 2),
        }

    def test_radio_off(self) -> None:
        """The opposite wording is its own event."""

        content = "Turn radio [band_index=1, subunit=4] off."

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWifiScheduler.RADIO_OFF,
            _KEY.RAW: content,
            _KEY.WL_ID: WiFiInterface(1, 4),
        }

    @pytest.mark.parametrize(
        ("band", "subunit"), [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)]
    )
    def test_every_observed_radio(self, band: int, subunit: int) -> None:
        """Each radio the scheduler drives resolves to its interface."""

        content = f"Turn radio [band_index={band}, subunit={subunit}] on."

        assert _translate(content)[_KEY.WL_ID] == WiFiInterface(band, subunit)

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future scheduler message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventWifiScheduler.UNKNOWN,
            _KEY.RAW: unread(content),
        }
