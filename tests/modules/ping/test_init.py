"""Tests for the ping module."""

from __future__ import annotations

from asusrouter.const import RequestType
from asusrouter.modules.endpoint import AREndpoint, get_endpoint_request_type


class TestEndpoint:
    """Tests for the ping endpoints."""

    def test_run_ping_is_get(self) -> None:
        """The run endpoint is a GET request."""

        assert (
            get_endpoint_request_type(AREndpoint.RUN_PING) is RequestType.GET
        )
