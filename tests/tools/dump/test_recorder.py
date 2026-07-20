"""Tests for asusrouter.tools.dump.recorder."""

from __future__ import annotations

from asusrouter.const import RequestType
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.tools.dump.recorder import ARDumpRecorder, ARDumpRequest


class TestARDumpRecorder:
    """Tests for ARDumpRecorder."""

    def test_empty(self) -> None:
        """A fresh recorder is empty and falsy."""

        recorder = ARDumpRecorder()

        assert recorder.requests == []
        assert len(recorder) == 0
        assert not recorder

    def test_record_appends_ordered(self) -> None:
        """Recording appends entries with an incrementing order."""

        recorder = ARDumpRecorder()
        recorder.record(AREndpoint.FETCH_DATA, RequestType.POST, "p0", "b0")
        recorder.record(
            AREndpoint.FETCH_VPN_STATUS, RequestType.GET, None, "b1"
        )

        assert len(recorder) == 2
        assert recorder

        first, second = recorder.requests
        assert first == ARDumpRequest(
            order=0,
            endpoint=AREndpoint.FETCH_DATA,
            request_type=RequestType.POST,
            payload="p0",
            content="b0",
        )
        assert second.order == 1
        assert second.endpoint is AREndpoint.FETCH_VPN_STATUS
        assert second.payload is None
