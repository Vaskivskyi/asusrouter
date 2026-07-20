"""Tests for the speedtest servers source."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook
from asusrouter.modules.speedtest.servers import (
    ARSpeedTestServersSource,
    ARSpeedTestServersSourceUniversal,
    fetch_state,
    translate_state,
)
from asusrouter.modules.support.flag import ARSupportType
from asusrouter.registry import ARCallableRegistry as ARCallReg


def _identity(*, speedtest: bool = True) -> ARDeviceIdentity:
    """Build an identity with the SpeedTest support flag set."""

    identity = ARDeviceIdentity()
    identity._support[ARSupportType.SPEEDTEST] = speedtest
    return identity


_IDENTITY = _identity()

_HOOK = ARHook.OOKLA_SPEEDTEST_SERVERS.value
_SERVERS = [{"id": 1, "name": "A", "location": "L"}, {}]


class TestSource:
    """Tests for the servers source."""

    def test_registered(self) -> None:
        """The source resolves to the module fetch_state callable."""

        assert (
            ARCallReg.get_callable(
                ARSpeedTestServersSourceUniversal, "fetch_state"
            )
            is fetch_state
        )


class TestGetState:
    """Tests for fetch_state."""

    async def test_default_reads_list(self) -> None:
        """Without refresh the server list is read directly."""

        callback = AsyncMock(return_value={_HOOK: _SERVERS})
        result = await fetch_state(
            callback, ARSpeedTestServersSourceUniversal, identity=_IDENTITY
        )

        assert result == _SERVERS
        call = callback.await_args.kwargs
        assert call["endpoint"] == AREndpoint.FETCH_DATA

    async def test_extract_non_dict(self) -> None:
        """A non-dict hook reply yields no data."""

        callback = AsyncMock(return_value=None)
        result = await fetch_state(
            callback, ARSpeedTestServersSourceUniversal, identity=_IDENTITY
        )

        assert result == {}

    async def test_unsupported_skips_fetch(self) -> None:
        """Without SpeedTest support nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(
            callback,
            ARSpeedTestServersSourceUniversal,
            identity=_identity(speedtest=False),
        )

        assert result == {}
        callback.assert_not_awaited()

    async def test_refresh_dispatches_and_polls(self) -> None:
        """Refresh asks the router to rebuild, then reads the filled list."""

        full = [{"id": i} for i in range(3)]
        callback = AsyncMock(side_effect=[None, {_HOOK: full}])

        with patch("asusrouter.tools.poll.asyncio.sleep", AsyncMock()):
            result = await fetch_state(
                callback,
                ARSpeedTestServersSourceUniversal,
                refresh=True,
                identity=_IDENTITY,
            )

        assert result == full
        first = callback.await_args_list[0].kwargs
        assert first["endpoint"] == AREndpoint.RUN_SPEEDTEST
        assert first["request"] == "type=list&id="


class TestTranslateState:
    """Tests for translate_state."""

    def test_translates(self) -> None:
        """Named servers are kept, the trailing empty dropped."""

        servers = translate_state(_SERVERS)

        assert len(servers) == 1
        assert servers[0].name == "A"


def test_source_equal_by_type() -> None:
    """Sources are equal by exact type."""

    assert ARSpeedTestServersSource() == ARSpeedTestServersSourceUniversal
