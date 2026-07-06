"""Tests for AsusRouter data pipeline methods."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from functools import partial
from typing import Any, cast
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from asusrouter.asusrouter import _REBOOT_RECOVERY_INITIAL_DELAY, AsusRouter
from asusrouter.const import AR_CALL_RUN_ACTION
from asusrouter.error import AsusRouterError
from asusrouter.modules.action import ARAction
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.boottime import ARBoottime
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataTypeGeneric,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg
from tests.helpers import (
    BindStateFactory,
    MakeStateFactory,
    assert_state_not_updated,
    assert_state_updated,
)


class _AltSource(ARDataSource):
    """A distinct source type (sources are equal by exact type)."""


@pytest.fixture
def identity() -> ARDeviceIdentity:
    """Provide a blank device identity for pipeline calls."""

    return ARDeviceIdentity()


class TestCreateDataState:
    """Tests for AsusRouter._create_data_state."""

    @pytest.mark.parametrize(
        "invalid",
        [None, ARDataCollection([])],
        ids=["none", "empty_collection"],
    )
    def test_rejects_invalid_input(
        self, router: AsusRouter, invalid: ARDataCollection | None
    ) -> None:
        """Returns early for None or empty collection without side effects."""

        router._create_data_state(invalid)  # type: ignore[arg-type]
        assert router._data_states == {}

    @pytest.mark.parametrize(
        ("source", "expected_type"),
        [
            (ARDataSource(), ARDataStateDynamic),
            (ARDataTypeGeneric.UNKNOWN, ARDataStateStatic),
        ],
        ids=["datasource", "datatype"],
    )
    def test_creates_correct_state_type(
        self,
        router: AsusRouter,
        source: ARDataSource | ARDataTypeGeneric,
        expected_type: type[ARDataState],
    ) -> None:
        """Creates the correct state type and assigns the read callback."""

        router._create_data_state(ARDataCollection([source]))

        assert source in router._data_states
        state = router._data_states[source]
        assert isinstance(state, expected_type)
        assert state.callback == router.async_read

    def test_skips_existing_and_creates_new(self, router: AsusRouter) -> None:
        """Existing items are preserved; new items are created in same call."""

        existing = ARDataSource()
        new_source = _AltSource()
        sentinel = Mock(spec=ARDataState)
        router._data_states[existing] = sentinel

        router._create_data_state(ARDataCollection([existing, new_source]))

        assert router._data_states[existing] is sentinel
        new_state = router._data_states[new_source]
        assert isinstance(new_state, ARDataStateDynamic)
        assert new_state.callback == router.async_read


class TestCommitState:
    """Tests for AsusRouter._commit_data_state."""

    @pytest.mark.parametrize(
        "value",
        [{"key": "val"}, None, [1, 2, 3]],
        ids=["dict", "none", "list"],
    )
    def test_updates_state_and_persists(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
        value: Any,
    ) -> None:
        """Calls update on state and stores it in _data_states."""

        state = make_state(source)
        router._commit_data_state(state, value)

        assert_state_updated(state, value)
        assert router._data_states[source] is state

    def test_overwrites_existing_entry(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
    ) -> None:
        """Replaces an existing entry in _data_states with the new state."""

        old_state = make_state(source)
        router._data_states[source] = old_state
        new_state = make_state(source)

        router._commit_data_state(new_state, {"x": 1})

        assert_state_updated(new_state, {"x": 1})
        assert router._data_states[source] is new_state

    def test_committing_topology_syncs_identity(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
    ) -> None:
        """Committing an ARAiMeshTopology updates the identity snapshot."""

        identity = ARDeviceIdentity()
        id_state = make_state(ARDeviceSourceUniversal)
        # `update` is mocked by the fixture; set the content directly
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state

        topology = ARAiMeshTopology()
        router._commit_data_state(make_state(source), topology)

        assert identity.aimesh is topology

    def test_committing_boottime_syncs_identity(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
    ) -> None:
        """Committing an ARBoottime updates the identity boot time."""

        identity = ARDeviceIdentity()
        id_state = make_state(ARDeviceSourceUniversal)
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state

        boottime = ARBoottime(2026, 1, 1, tzinfo=UTC)
        router._commit_data_state(make_state(source), boottime)

        assert identity.boottime == boottime

    def test_committing_plain_datetime_ignores_boottime(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
    ) -> None:
        """A plain datetime from another source does not touch boot time."""

        identity = ARDeviceIdentity()
        id_state = make_state(ARDeviceSourceUniversal)
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state

        router._commit_data_state(
            make_state(source), datetime(2026, 1, 1, tzinfo=UTC)
        )

        assert identity.boottime is None


class TestAsyncRefreshDataState:
    """Tests for AsusRouter._async_refresh_data_state."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "collection",
        [ARDataCollection([]), ARDataCollection([ARDataSource()])],
        ids=["empty_collection", "missing_states"],
    )
    async def test_no_op_when_no_states(
        self,
        router: AsusRouter,
        collection: ARDataCollection,
    ) -> None:
        """Returns immediately without touching _data_states."""

        await router._async_refresh_data_state(collection, force=True)
        assert router._data_states == {}

    @pytest.mark.asyncio
    async def test_skips_state_fresh_in_v2_window(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """A state fresh within the V2 window is not refetched."""

        state_caller = AsyncMock(return_value={"a": 1})
        state = bind_state(source, caller=state_caller)
        cast(Any, state)._last_update = datetime.now(UTC)

        collection = ARDataCollection.from_value(source)
        assert collection is not None

        await router._async_refresh_data_state(collection, force=False)

        state_caller.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetches_stale_state_without_force(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """A never-fetched (stale) state is refetched without force."""

        state_caller = AsyncMock(return_value={"a": 1})
        bind_state(source, caller=state_caller)

        collection = ARDataCollection.from_value(source)
        assert collection is not None

        await router._async_refresh_data_state(collection, force=False)

        state_caller.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_force_refetches_fresh_state(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """force=True refetches even a fresh state."""

        state_caller = AsyncMock(return_value={"a": 1})
        state = bind_state(source, caller=state_caller)
        cast(Any, state)._last_update = datetime.now(UTC)

        collection = ARDataCollection.from_value(source)
        assert collection is not None

        await router._async_refresh_data_state(collection, force=True)

        state_caller.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_kwarg_passes_through(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """A `refresh` kwarg reaches the caller without colliding."""

        state_caller = AsyncMock(return_value={"a": 1})
        bind_state(source, caller=state_caller)

        collection = ARDataCollection.from_value(source)
        assert collection is not None
        await router._async_refresh_data_state(
            collection, force=True, refresh=True
        )

        state_caller.assert_awaited_once()
        assert state_caller.await_args.kwargs["refresh"] is True

    @pytest.mark.asyncio
    async def test_batch_caller(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """Batch caller receives source list; result translated."""

        state_caller = AsyncMock(return_value={source: {"a": 1}})
        state = bind_state(source, caller=state_caller, caller_multi=True)

        collection = ARDataCollection.from_value(source)
        assert collection is not None
        await router._async_refresh_data_state(
            collection, force=True, extra_kw="x"
        )

        cast(AsyncMock, state.state_caller).assert_awaited_once_with(
            router.async_read,
            [source],
            force=True,
            identity=ANY,
            connection_config=ANY,
            extra_kw="x",
        )
        assert_state_updated(state, {"a": 1})

    @pytest.mark.asyncio
    async def test_single_caller_fans_out_concurrently(
        self,
        router: AsusRouter,
        bind_state: BindStateFactory,
    ) -> None:
        """Same-caller sources are fetched concurrently, not serialized."""

        active = 0
        peak = 0

        async def caller(_read: Any, source: Any, **_kw: Any) -> Any:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return {"src": source}

        source_a, source_b = ARDataSource(), _AltSource()
        bind_state(source_a, caller=caller)
        bind_state(source_b, caller=caller)

        collection = ARDataCollection([source_a, source_b])

        await router._async_refresh_data_state(collection, force=True)

        assert peak == 2

    @pytest.mark.asyncio
    async def test_concurrent_refresh_deduplicates(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """A concurrent refresh awaits the in-flight fetch, not refetches."""

        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def caller(_read: Any, _source: Any, **_kw: Any) -> Any:
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return {"a": 1}

        bind_state(source, caller=caller)
        collection = ARDataCollection.from_value(source)
        assert collection is not None

        first = asyncio.ensure_future(
            router._async_refresh_data_state(collection, force=True)
        )
        await started.wait()
        second = asyncio.ensure_future(
            router._async_refresh_data_state(collection, force=True)
        )
        # Let the second caller reach the in-flight wait, then release
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)

        assert calls == 1

    @pytest.mark.asyncio
    async def test_refresh_error_propagates_and_releases(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
    ) -> None:
        """A caller error propagates and the in-flight marker is cleared."""

        async def caller(_read: Any, _source: Any, **_kw: Any) -> Any:
            raise RuntimeError("fetch failed")

        state = bind_state(source, caller=caller)
        collection = ARDataCollection.from_value(source)
        assert collection is not None

        with pytest.raises(RuntimeError, match="fetch failed"):
            await router._async_refresh_data_state(collection, force=True)

        assert state.refreshing is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("has_translate", "expected_value"),
        [
            (True, {"transformed": 2}),
            (False, {"a": 1}),
        ],
        ids=["with_translate", "without_translate"],
    )
    async def test_single_caller(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        has_translate: bool,
        expected_value: Any,
    ) -> None:
        """Single caller receives source; translate applied when present."""

        translator = (
            Mock(return_value={"transformed": 2}) if has_translate else None
        )
        state_caller = AsyncMock(return_value={"a": 1})
        state = bind_state(source, caller=state_caller, translator=translator)

        collection = ARDataCollection.from_value(source)
        assert collection is not None
        await router._async_refresh_data_state(
            collection, force=True, extra_kw="x"
        )

        cast(AsyncMock, state.state_caller).assert_awaited_once_with(
            router.async_read,
            source,
            force=True,
            identity=ANY,
            connection_config=ANY,
            extra_kw="x",
        )
        if translator:
            translator.assert_called_once_with({"a": 1}, identity=ANY)
        assert_state_updated(state, expected_value)


class TestAsyncGetDataState:
    """Tests for AsusRouter._async_get_data_state."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_invalid_source(
        self,
        router: AsusRouter,
    ) -> None:
        """Returns empty dict when source cannot form a collection."""

        result = await router._async_get_data_state(
            cast(Any, "invalid"), force=True
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_orchestrates_create_refresh_and_returns_states(
        self,
        router: AsusRouter,
        source: ARDataSource,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Creates states, refreshes them, and returns the populated dict."""

        sentinel = cast(ARDataState, Mock(spec=ARDataState))

        def create_side_effect(collection: ARDataCollection) -> None:
            router._data_states[source] = sentinel

        mock_create = Mock(side_effect=create_side_effect)
        mock_refresh = AsyncMock(return_value=None)

        monkeypatch.setattr(router, "_create_data_state", mock_create)
        monkeypatch.setattr(router, "_async_refresh_data_state", mock_refresh)

        result = await router._async_get_data_state(
            source, force=True, extra_kw="x"
        )

        assert isinstance(mock_create.call_args.args[0], ARDataCollection)
        assert list(mock_create.call_args.args[0]) == [source]
        mock_refresh.assert_awaited_once_with(
            mock_create.call_args.args[0],
            force=True,
            extra_kw="x",
        )
        assert result == {source: sentinel}


class TestAsyncFetchData:
    """Tests for AsusRouter.async_fetch_data."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_data_state(
        self,
        router: AsusRouter,
        source: ARDataSource,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Returns None and injects callback when no data states returned."""

        async_get = AsyncMock(return_value={})
        monkeypatch.setattr(router, "_async_get_data_state", async_get)

        result = await router.async_fetch_data(
            source, force=True, extra_kw="x"
        )

        async_get.assert_awaited_once()
        call = async_get.await_args
        assert call.args == (source,)
        assert call.kwargs["force"] is True
        assert call.kwargs["extra_kw"] == "x"
        # Sub-fetch callback is bound to this call's force
        callback = call.kwargs["get_data_callback"]
        assert isinstance(callback, partial)
        assert callback.func == router.async_fetch_data
        assert callback.keywords == {"force": True}
        # Raw fetch is injected for readers that need unparsed content
        assert call.kwargs["raw_callback"] == router.async_fetch
        # Action trigger is injected so a fetch module can run an action
        assert call.kwargs["run_action_callback"] == router.async_run_action
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_fresh",
        [True, False],
        ids=["fresh", "stale"],
    )
    async def test_filters_by_freshness(
        self,
        router: AsusRouter,
        source: ARDataSource,
        monkeypatch: pytest.MonkeyPatch,
        is_fresh: bool,
    ) -> None:
        """Returns content for fresh states; None when all states are stale."""

        content = {"ok": 1}
        fake_state = Mock()
        fake_state.content = content
        fake_state.is_fresh = Mock(return_value=is_fresh)

        monkeypatch.setattr(
            router,
            "_async_get_data_state",
            AsyncMock(return_value={source: fake_state}),
        )

        result = await router.async_fetch_data(
            source, force=True, extra_kw="x"
        )

        fake_state.is_fresh.assert_called_once_with(router._cache_threshold_v2)
        assert result == ({source: content} if is_fresh else None)

    def _seed_identity(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        rebooted: bool,
    ) -> ARDeviceIdentity:
        """Seed a device identity with the given reboot flag."""

        identity = ARDeviceIdentity()
        identity._rebooted = rebooted
        id_state = make_state(ARDeviceSourceUniversal)
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state
        return identity

    @pytest.mark.asyncio
    @pytest.mark.parametrize("rebooted", [True, False], ids=["reboot", "none"])
    async def test_fetch_handles_reboot(
        self,
        router: AsusRouter,
        source: ARDataSource,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
        rebooted: bool,
    ) -> None:
        """The reboot handler runs only when the identity flags a reboot."""

        self._seed_identity(router, make_state, rebooted)
        monkeypatch.setattr(
            router, "_async_get_data_state", AsyncMock(return_value={})
        )
        handler = AsyncMock()
        monkeypatch.setattr(router, "_async_handle_reboot", handler)

        await router.async_fetch_data(source)

        assert handler.await_count == (1 if rebooted else 0)

    @pytest.mark.asyncio
    async def test_handle_reboot_clears_flag(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
    ) -> None:
        """The reboot handler clears the identity flag."""

        identity = self._seed_identity(router, make_state, rebooted=True)

        await router._async_handle_reboot()

        assert identity.rebooted is False


class TestAsyncRunAction:
    """Tests for AsusRouter.async_run_action."""

    @pytest.mark.asyncio
    async def test_no_caller_returns_none(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns None when no run_action is registered for the action."""

        monkeypatch.setattr(ARCallReg, "get_callable", Mock(return_value=None))
        assert await router.async_run_action(ARAction()) is None

    @pytest.mark.asyncio
    async def test_runs_and_returns_raw(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Runs the action with fetch-style callbacks; result not cached."""

        run = AsyncMock(return_value="raw")

        def get_callable(action: Any, name: str) -> Any:
            return run if name == AR_CALL_RUN_ACTION else None

        monkeypatch.setattr(ARCallReg, "get_callable", get_callable)

        action = ARAction()
        result = await router.async_run_action(action, extra_kw="x")

        assert result == "raw"
        run.assert_awaited_once()
        call = run.await_args
        assert call.args == (router.async_read, action)
        kw = call.kwargs
        assert isinstance(kw["identity"], ARDeviceIdentity)
        assert kw["raw_callback"] == router.async_fetch
        assert kw["run_action_callback"] == router.async_run_action
        assert kw["extra_kw"] == "x"
        callback = kw["get_data_callback"]
        assert isinstance(callback, partial)
        assert callback.func == router.async_fetch_data
        assert callback.keywords == {"force": True}
        # Action results are never stored
        assert router._data_states == {}

    @pytest.mark.asyncio
    async def test_translate_applied(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A registered translate_action transforms the raw result."""

        run = AsyncMock(return_value="raw")
        translate = Mock(return_value="translated")

        def get_callable(action: Any, name: str) -> Any:
            return run if name == AR_CALL_RUN_ACTION else translate

        monkeypatch.setattr(ARCallReg, "get_callable", get_callable)

        result = await router.async_run_action(ARAction())

        assert result == "translated"
        assert translate.call_args.args == ("raw",)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("rebooted", [True, False], ids=["reboot", "none"])
    async def test_drops_connection_on_reboot(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
        rebooted: bool,
    ) -> None:
        """A reboot flagged during the run drops the connection."""

        identity = ARDeviceIdentity()
        id_state = make_state(ARDeviceSourceUniversal)
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state

        async def run(*_args: Any, **_kwargs: Any) -> str:
            if rebooted:
                identity.mark_reboot()
            return "raw"

        def get_callable(action: Any, name: str) -> Any:
            return run if name == AR_CALL_RUN_ACTION else None

        monkeypatch.setattr(ARCallReg, "get_callable", get_callable)
        drop = Mock()
        monkeypatch.setattr(router, "_async_drop_connection", drop)
        recover = AsyncMock()
        monkeypatch.setattr(router, "_async_recover_after_reboot", recover)

        await router.async_run_action(ARAction())

        assert drop.call_count == (1 if rebooted else 0)
        # A reboot also spawns the recovery task
        assert (router._reboot_recovery is not None) is rebooted
        if router._reboot_recovery is not None:
            await router._reboot_recovery


class TestRebootRecovery:
    """Tests for the reboot recovery gate."""

    def _seed_identity(
        self, router: AsusRouter, make_state: MakeStateFactory
    ) -> ARDeviceIdentity:
        """Seed a persistent, reboot-flagged identity."""

        identity = ARDeviceIdentity()
        identity.mark_reboot()
        id_state = make_state(ARDeviceSourceUniversal)
        cast(Any, id_state)._content = identity
        router._data_states[ARDeviceSourceUniversal] = id_state
        return identity

    @pytest.mark.asyncio
    async def test_fetch_waits_for_recovery(
        self, router: AsusRouter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A held request runs only after recovery completes."""

        order: list[str] = []

        async def recovery() -> None:
            order.append("recovery")

        router._reboot_recovery = asyncio.create_task(recovery())

        async def query(*_args: Any, **_kwargs: Any) -> tuple[int, Any, str]:
            order.append("query")
            return (200, {}, "ok")

        monkeypatch.setattr(router._connection, "async_query", query)

        result = await router.async_fetch(AREndpoint.FETCH_DATA)

        assert result == "ok"
        assert order == ["recovery", "query"]

    @pytest.mark.asyncio
    async def test_recovery_waits_before_first_probe(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The grace delay elapses before the first reconnect probe."""

        self._seed_identity(router, make_state)
        connect = AsyncMock(return_value=True)
        monkeypatch.setattr(router._connection, "async_connect", connect)
        sleep = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", sleep)

        await router._async_recover_after_reboot()

        # The very first wait is the grace delay, before any probe
        assert sleep.await_args_list[0].args == (
            _REBOOT_RECOVERY_INITIAL_DELAY,
        )
        connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_recovery_success_clears_flag(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reconnect clears the flag and the recovery handle."""

        identity = self._seed_identity(router, make_state)
        connect = AsyncMock(side_effect=[False, True])
        monkeypatch.setattr(router._connection, "async_connect", connect)
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        await router._async_recover_after_reboot()

        assert identity.rebooted is False
        assert router._reboot_recovery is None
        assert connect.await_count == 2

    @pytest.mark.asyncio
    async def test_recovery_toggles_error_suppression(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Errors are suppressed for the recovery and restored after."""

        self._seed_identity(router, make_state)
        monkeypatch.setattr(
            router._connection, "async_connect", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        suppress = Mock()
        monkeypatch.setattr(
            router._connection, "set_error_suppression", suppress
        )

        await router._async_recover_after_reboot()

        assert [c.args for c in suppress.call_args_list] == [(True,), (False,)]

    @pytest.mark.asyncio
    async def test_recovery_survives_connection_error(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A connection error during a probe is retried, not raised."""

        identity = self._seed_identity(router, make_state)
        connect = AsyncMock(side_effect=[AsusRouterError("down"), True])
        monkeypatch.setattr(router._connection, "async_connect", connect)
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        await router._async_recover_after_reboot()

        assert identity.rebooted is False
        assert connect.await_count == 2

    @pytest.mark.asyncio
    async def test_recovery_timeout_keeps_flag(
        self,
        router: AsusRouter,
        make_state: MakeStateFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A timeout leaves the flag set and clears the handle."""

        identity = self._seed_identity(router, make_state)
        connect = AsyncMock(return_value=False)
        monkeypatch.setattr(router._connection, "async_connect", connect)
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        monkeypatch.setattr(
            "asusrouter.asusrouter._REBOOT_RECOVERY_TIMEOUT", 0
        )

        await router._async_recover_after_reboot()

        assert identity.rebooted is True
        assert router._reboot_recovery is None
        connect.assert_not_awaited()


class TestTranslateMultidataBatch:
    """Tests for AsusRouter._translate_multidata_batch."""

    def test_commits_when_source_in_result(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        identity: ARDeviceIdentity,
    ) -> None:
        """Commits translated value when source key is in result."""

        state = bind_state(source)
        translator = Mock(return_value={source: {"b": 2}})

        router._translate_multidata_batch(
            translator, [state], {source: {"a": 1}}, identity
        )

        translator.assert_called_once_with(
            {source: {"a": 1}}, identity=identity
        )
        assert_state_updated(state, {"b": 2})

    @pytest.mark.parametrize(
        "make_result",
        [
            lambda src: [1, 2, 3],
            lambda src: {"other": {"b": 2}},
        ],
        ids=["non_dict", "source_not_in_result"],
    )
    def test_skips_when_result_invalid(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        make_result: Any,
        identity: ARDeviceIdentity,
    ) -> None:
        """Skips commit when result is non-dict or source absent."""

        state = bind_state(source)
        translator = Mock(return_value=make_result(source))

        router._translate_multidata_batch(
            translator, [state], {source: {"a": 1}}, identity
        )

        assert_state_not_updated(state)


class TestTranslateMultidataSingle:
    """Tests for AsusRouter._translate_multidata_single."""

    def test_skips_when_source_not_in_data(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        identity: ARDeviceIdentity,
    ) -> None:
        """Skips state when its source is absent from data."""

        state = bind_state(source)
        translator = Mock()

        router._translate_multidata_single(translator, [state], {}, identity)

        translator.assert_not_called()
        assert_state_not_updated(state)

    @pytest.mark.parametrize(
        "translator_return",
        [{"c": 3}, None, [1, 2, 3]],
        ids=["dict", "none", "list"],
    )
    def test_commits_translator_result(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        translator_return: Any,
        identity: ARDeviceIdentity,
    ) -> None:
        """Forwards any translator return value to commit."""

        state = bind_state(source)
        translator = Mock(return_value=translator_return)

        router._translate_multidata_single(
            translator, [state], {source: {"a": 1}}, identity
        )

        translator.assert_called_once_with({"a": 1}, identity=identity)
        cast(Mock, state.update).assert_called_once_with(translator_return)


class TestTranslateMultidata:
    """Tests for AsusRouter._translate_multidata."""

    def test_ignores_non_dict_data(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        identity: ARDeviceIdentity,
    ) -> None:
        """Returns early without updating state when data is not a dict."""

        state = bind_state(source)

        router._translate_multidata([state], cast(Any, [1, 2, 3]), identity)

        assert_state_not_updated(state)

    def test_no_translator_commits_when_source_present(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        identity: ARDeviceIdentity,
    ) -> None:
        """Commits directly when state has no translator and source in data."""

        state = bind_state(source)

        router._translate_multidata([state], {source: {"val": 1}}, identity)

        assert_state_updated(state, {"val": 1})

    def test_no_translator_skips_when_source_absent(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        identity: ARDeviceIdentity,
    ) -> None:
        """Skips commit when state has no translator and source absent."""

        state = bind_state(source)

        router._translate_multidata([state], {}, identity)

        assert_state_not_updated(state)

    @pytest.mark.parametrize(
        "is_batch",
        [True, False],
        ids=["batch", "single"],
    )
    def test_dispatches_to_correct_strategy(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        is_batch: bool,
        identity: ARDeviceIdentity,
    ) -> None:
        """Dispatches to batch or single translator based on callable flag."""

        translator_result = {source: {"x": 1}} if is_batch else {"x": 1}
        translator = Mock(return_value=translator_result)
        state = bind_state(
            source, translator=translator, translator_multi=is_batch
        )

        router._translate_multidata([state], {source: {"a": 1}}, identity)

        expected_arg = {source: {"a": 1}} if is_batch else {"a": 1}
        translator.assert_called_once_with(expected_arg, identity=identity)
        assert_state_updated(state, {"x": 1})
