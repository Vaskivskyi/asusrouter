"""Tests for AsusRouter data pipeline methods."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from asusrouter.asusrouter import ARCallReg, AsusRouter
from asusrouter.modules.aimesh.topology import ARAiMeshTopology
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataTypeGeneric,
)
from tests.helpers import (
    BindStateFactory,
    MakeStateFactory,
    UniversalMockPatcher,
    assert_state_not_updated,
    assert_state_updated,
)


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
        new_source = ARDataSource()
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
    async def test_batch_caller(
        self,
        router: AsusRouter,
        source: ARDataSource,
        bind_state: BindStateFactory,
        universal_mock: UniversalMockPatcher,
    ) -> None:
        """Batch caller receives source list; result translated."""

        state_caller = AsyncMock(return_value={source: {"a": 1}})
        state = bind_state(source, caller=state_caller)

        universal_mock.patch(
            ARCallReg, "get_callable_flag", return_value=True, mock_type=Mock
        )

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
        universal_mock: UniversalMockPatcher,
        has_translate: bool,
        expected_value: Any,
    ) -> None:
        """Single caller receives source; translate applied when present."""

        translator = (
            Mock(return_value={"transformed": 2}) if has_translate else None
        )
        state_caller = AsyncMock(return_value={"a": 1})
        state = bind_state(source, caller=state_caller, translator=translator)

        universal_mock.patch(
            ARCallReg, "get_callable_flag", return_value=False, mock_type=Mock
        )

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

        async_get.assert_awaited_once_with(
            source,
            force=True,
            extra_kw="x",
            get_data_callback=router.async_fetch_data,
        )
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

        fake_state.is_fresh.assert_called_once_with(router._cache_threshold)
        assert result == ({source: content} if is_fresh else None)


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
        universal_mock: UniversalMockPatcher,
        is_batch: bool,
        identity: ARDeviceIdentity,
    ) -> None:
        """Dispatches to batch or single translator based on callable flag."""

        translator_result = {source: {"x": 1}} if is_batch else {"x": 1}
        translator = Mock(return_value=translator_result)
        state = bind_state(source, translator=translator)

        universal_mock.patch(
            ARCallReg,
            "get_callable_flag",
            return_value=is_batch,
            mock_type=Mock,
        )

        router._translate_multidata([state], {source: {"a": 1}}, identity)

        expected_arg = {source: {"a": 1}} if is_batch else {"a": 1}
        translator.assert_called_once_with(expected_arg, identity=identity)
        assert_state_updated(state, {"x": 1})
