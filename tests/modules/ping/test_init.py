"""Tests for the ping module."""

from __future__ import annotations

from asusrouter.const import RequestType
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_request_type
from asusrouter.modules.ping import ARPingStatus


class TestARPingStatus:
    """Tests for ARPingStatus."""

    def test_finished(self) -> None:
        """`3` maps to FINISHED."""

        assert ARPingStatus.from_value("3") is ARPingStatus.FINISHED

    def test_unknown(self) -> None:
        """Any other value maps to UNKNOWN."""

        assert ARPingStatus.from_value("1") is ARPingStatus.UNKNOWN


class TestEndpoint:
    """Tests for the ping endpoints."""

    def test_run_ping_is_get(self) -> None:
        """The run endpoint is a GET request."""

        assert (
            get_endpoint_request_type(AREndpoint.RUN_PING) is RequestType.GET
        )
