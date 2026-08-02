"""Tests for the service dispatch (rc_service) event translation."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.common.command import ARService
from asusrouter.modules.log.enums import AREventKey
from asusrouter.modules.log.translate.rc_service import (
    PATTERNS,
    AREventRcService,
)
from tests.modules.log.translate import unread

_KEY = AREventKey
_WAITING = 'waitting "stop_httpd" via udhcpc_lan ...'
# Newer firmware appends the in-flight action right after the quote
_WAITING_LAST_RC = (
    'waitting "restart_wan_if 0"(last_rc:stop_samba) via wanduck ...'
)


def _translate(content: str) -> dict[AREventKey, Any]:
    """Translate a raw service dispatch message."""

    return PATTERNS.translate(content)


class TestNotify:
    """`notify_rc` dispatch translation."""

    def test_single(self) -> None:
        """A single action carries caller, pid and one service."""

        content = "service 2011:notify_rc restart_firewall"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRcService.NOTIFY,
            _KEY.RAW: content,
            _KEY.CALLER: "service",
            _KEY.PID: 2011,
            _KEY.SERVICES: (ARService.FIREWALL_RESTART,),
            _KEY.ACTIONS: ("restart_firewall",),
        }

    def test_multiple(self) -> None:
        """A `;`-separated action list maps to an ordered service tuple."""

        content = (
            "cfg_client 2621:notify_rc "
            "restart_wireless;chpass;restart_time;restart_qos;restart_firewall"
        )

        assert _translate(content)[_KEY.SERVICES] == (
            ARService.WIRELESS_RESTART,
            ARService.CHPASS,
            ARService.TIME_RESTART,
            ARService.QOS_RESTART,
            ARService.FIREWALL_RESTART,
        )

    def test_trailing_separator(self) -> None:
        """A list ending on a separator yields no empty action."""

        # A real RT-AC66U line
        event = _translate("httpd 1234:notify_rc restart_time;restart_upnp;")

        assert event[_KEY.ACTIONS] == ("restart_time", "restart_upnp")
        assert event[_KEY.SERVICES] == (
            ARService.TIME_RESTART,
            ARService.UPNP_RESTART,
        )

    def test_action_argument(self) -> None:
        """The argument is dropped from the service but kept in the action."""

        event = _translate(
            "cfg_client 4875:notify_rc stop_upgrade;start_webs_upgrade 1"
        )

        assert event[_KEY.SERVICES] == (
            ARService.FIRMWARE_UPGRADE_STOP,
            ARService.FIRMWARE_WEB_UPGRADE_START,
        )
        assert event[_KEY.ACTIONS] == ("stop_upgrade", "start_webs_upgrade 1")

    def test_unknown_service(self) -> None:
        """An unmapped action keeps its raw token next to UNKNOWN."""

        event = _translate(
            "rc 5715:notify_rc restart_wireless;start_madeup_service"
        )

        assert event[_KEY.SERVICES] == (
            ARService.WIRELESS_RESTART,
            ARService.UNKNOWN,
        )
        assert event[_KEY.ACTIONS] == (
            "restart_wireless",
            "start_madeup_service",
        )


class TestWaiting:
    """Dispatch waiting for an in-flight service translation."""

    def test_match(self) -> None:
        """The waited-on service and its caller are extracted."""

        assert _translate(_WAITING) == {
            _KEY.EVENT_TYPE: AREventRcService.WAITING,
            _KEY.RAW: _WAITING,
            _KEY.CALLER: "udhcpc_lan",
            _KEY.SERVICE: ARService.WEBUI_STOP,
            _KEY.ACTION: "stop_httpd",
        }

    def test_last_rc(self) -> None:
        """The newer `(last_rc:...)` form parses and keeps the last action."""

        assert _translate(_WAITING_LAST_RC) == {
            _KEY.EVENT_TYPE: AREventRcService.WAITING,
            _KEY.RAW: _WAITING_LAST_RC,
            _KEY.CALLER: "wanduck",
            _KEY.SERVICE: ARService.WAN_INTERFACE_RESTART,
            _KEY.ACTION: "restart_wan_if 0",
            _KEY.LAST_ACTION: "stop_samba",
            _KEY.LAST_SERVICE: ARService.SAMBA_STOP,
        }

    def test_empty_last_rc_dropped(self) -> None:
        """An empty `(last_rc:)` carries no last-action keys."""

        event = _translate('waitting "stop_httpd"(last_rc:) via wanduck ...')

        assert _KEY.LAST_ACTION not in event
        assert _KEY.LAST_SERVICE not in event


class TestTranslateRcService:
    """The per-program dispatcher."""

    def test_unrecognized(self) -> None:
        """An unhandled message becomes an UNKNOWN event keeping the raw."""

        content = "some future rc_service message we do not handle yet"

        assert _translate(content) == {
            _KEY.EVENT_TYPE: AREventRcService.UNKNOWN,
            _KEY.RAW: unread(content),
        }
