"""Tests for the ping module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from asusrouter.modules.common.metrics import ARMetricType as M
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.nvram import ARNvramType
from asusrouter.modules.ping import (
    ARPingResult,
    ARPingSource,
    ARPingSourceUniversal,
    ARPingStatus,
    _build_request,
    get_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.identifiers.ip import IpAddress

# A single finished ping run, in response/content order
_ROW = [
    "1.1.1.1",
    "Cloudflare",
    "1",
    "8.44",
    "10.12",
    "12.36",
    "5",
    "5",
    "0.0",
    "1782998188",
]


def _status_callback(value: str | None) -> AsyncMock:
    """Build a get_data_callback returning the given ping status."""

    return AsyncMock(return_value={ARNvramType.DNS_PING_STATUS: value})


class TestARPingStatus:
    """Tests for ARPingStatus."""

    def test_finished(self) -> None:
        """`3` maps to FINISHED."""

        assert ARPingStatus.from_value("3") is ARPingStatus.FINISHED

    def test_unknown(self) -> None:
        """Any other value maps to UNKNOWN."""

        assert ARPingStatus.from_value("1") is ARPingStatus.UNKNOWN


class TestSource:
    """Tests for the ping source."""

    def test_equal_by_type(self) -> None:
        """Sources are equal by exact type."""

        assert ARPingSource() == ARPingSourceUniversal
        assert hash(ARPingSource()) == hash(ARPingSourceUniversal)

    def test_registered(self) -> None:
        """The source resolves to the module get_state callable."""

        assert (
            ARCallReg.get_callable(ARPingSourceUniversal, "get_state")
            is get_state
        )


class TestBuildRequest:
    """Tests for _build_request."""

    def test_contains_db_and_content(self) -> None:
        """The request targets the dns_ping db with all columns."""

        request = _build_request()
        assert "db=dns_ping" in request
        assert "dns_ip" in request
        assert "data_time" in request


class TestGetState:
    """Tests for get_state."""

    async def test_no_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        assert await get_state(AsyncMock(), ARPingSourceUniversal) is None

    async def test_not_finished(self) -> None:
        """An unfinished run drops the results without fetching."""

        callback = AsyncMock()
        get_data_callback = _status_callback("1")
        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                callback,
                ARPingSourceUniversal,
                get_data_callback=get_data_callback,
            )

        assert result is None
        callback.assert_not_awaited()
        get_data_callback.assert_awaited_with(
            ARNvramType.DNS_PING_STATUS, force=True
        )

    async def test_status_non_dict(self) -> None:
        """A non-dict status reply counts as not finished."""

        get_data_callback = AsyncMock(return_value=None)
        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await get_state(
                AsyncMock(),
                ARPingSourceUniversal,
                get_data_callback=get_data_callback,
            )

        assert result is None

    async def test_finished_returns_contents(self) -> None:
        """A finished run fetches and returns the diagnostics rows."""

        callback = AsyncMock(return_value={"contents": [_ROW]})
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
        )

        assert result == [_ROW]
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DIAGNOSTICS_DATA

    async def test_finished_empty_contents(self) -> None:
        """Empty rows yield no data."""

        callback = AsyncMock(return_value={"contents": []})
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
        )

        assert result is None

    async def test_finished_non_dict_data(self) -> None:
        """A non-dict diagnostics reply yields no data."""

        callback = AsyncMock(return_value=None)
        result = await get_state(
            callback,
            ARPingSourceUniversal,
            get_data_callback=_status_callback("3"),
        )

        assert result is None


class TestTranslateState:
    """Tests for translate_state."""

    def test_full_row(self) -> None:
        """A complete row translates into a full result."""

        result = translate_state([_ROW])

        ip = IpAddress.from_value_safe("1.1.1.1")
        assert result == {
            ip: ARPingResult(
                alias="Cloudflare",
                valid=True,
                timestamp=1782998188,
                metrics={
                    M.LATENCY_MIN: 8.44,
                    M.LATENCY_AVG: 10.12,
                    M.LATENCY_MAX: 12.36,
                    M.PACKETS_SENT: 5,
                    M.PACKETS_RECEIVED: 5,
                    M.PACKET_LOSS: 0.0,
                },
            )
        }

    def test_short_row(self) -> None:
        """Absent columns fall back to None / empty metrics."""

        result = translate_state([["1.1.1.1"]])

        ip = IpAddress.from_value_safe("1.1.1.1")
        assert result == {ip: ARPingResult()}

    def test_non_list(self) -> None:
        """Non-list input yields an empty mapping."""

        assert translate_state({"contents": []}) == {}

    def test_skips_malformed_rows(self) -> None:
        """Empty rows, non-list rows and bad IPs are skipped."""

        result = translate_state([[], "not-a-row", ["not-an-ip"], _ROW])

        assert list(result) == [IpAddress.from_value_safe("1.1.1.1")]
