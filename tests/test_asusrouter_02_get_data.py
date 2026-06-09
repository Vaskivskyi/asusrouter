"""Tests for the asusrouter module / Part 2 / Get Data."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.asusrouter import ARCallReg, AsusRouter
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataType,
    ARDataTypeGeneric,
)
from tests.helpers import (
    BindStateFactory,
    MakeStateFactory,
    UniversalMockPatcher,
    assert_state_not_updated,
    assert_state_updated,
)


def test_get_callback_for_state(
    router: AsusRouter,
    source: ARDataSource,
) -> None:
    """Test the _get_callback_for_state method."""

    callback = router._get_callback_for_state(source)

    assert callback == router.async_api_load


@pytest.mark.parametrize(
    ("source", "expected_return", "expected_state_type", "prepopulate"),
    [
        (ARDataSource(), True, ARDataStateDynamic, False),
        (ARDataTypeGeneric.UNKNOWN, True, ARDataStateStatic, False),
        (object(), False, None, False),
        (ARDataSource(), True, "sentinel", True),
    ],
    ids=["datasource", "datatype", "invalid", "existing"],
)
def test_create_data_state(
    router: AsusRouter,
    source: Any,
    expected_return: bool,
    expected_state_type: type,
    prepopulate: bool,
) -> None:
    """Test the _create_data_state method."""

    cllctn = ARDataCollection.from_value(source)

    sentinel = cast(ARDataState, Mock(spec=ARDataState))
    if prepopulate and cllctn is not None:
        router._data_states[cast(ARDataSource | ARDataType, source)] = sentinel

    result = router._create_data_state(cast(Any, cllctn))
    assert result is expected_return

    if prepopulate:
        assert router._data_states[source] is sentinel
    elif expected_return and expected_state_type is not None:
        assert source in router._data_states
        state = cast(Any, router._data_states[source])
        assert isinstance(state, expected_state_type)
        expected_callback = router._get_callback_for_state(source)
        assert cast(ARDataState, state).callback == expected_callback
    else:
        assert source not in router._data_states


def test_create_data_state_rejects_invalid_source(router: AsusRouter) -> None:
    """Test _create_data_state rejects invalid collection values."""

    assert router._create_data_state(cast(Any, None)) is False
    assert router._data_states == {}


def test_get_call_matrix_groups_states_and_skips_invalid(
    router: AsusRouter,
    make_state: MakeStateFactory,
) -> None:
    """Test the _get_call_matrix grouping behavior."""

    caller = Mock()
    callback = Mock()

    state_one = make_state(ARDataSource(), callback=callback, caller=caller)
    state_two = make_state(ARDataSource(), callback=callback, caller=caller)
    invalid_state = make_state(ARDataSource(), callback=callback, caller=None)

    matrix = router._get_call_matrix([state_one, state_two, invalid_state])

    assert len(matrix) == 1
    assert matrix[(caller, callback)] == [state_one, state_two]


def test_save_data_state_updates_state_and_storage(
    router: AsusRouter,
    source: ARDataSource,
    make_state: MakeStateFactory,
) -> None:
    """Test the _save_data_state helper."""

    state = make_state(source)

    router._save_data_state(state, {source: {"value": 1}})

    assert_state_updated(state, {"value": 1})
    assert router._data_states[source] is state


def test_translate_multidata_raw_saves_raw_state(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
) -> None:
    """Test raw multicaller translation without a translator."""

    state = bind_state(source)

    router._translate_multidata_raw({source: {"a": 1}}, [state])

    assert_state_updated(state, {"a": 1})
    assert router._data_states[source] is state


@pytest.mark.parametrize(
    ("is_valid", "expected_update"),
    [
        (True, {"b": 2}),
        (False, None),
    ],
)
def test_translate_multidata_batch(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
    is_valid: bool,
    expected_update: Any,
) -> None:
    """Test batch multicaller translation with valid and invalid outputs."""

    state = bind_state(source)

    translator_result = {source: expected_update} if is_valid else [1, 2, 3]
    translator = Mock(return_value=translator_result)
    router._translate_multidata_batch(translator, [state], {source: {"a": 1}})

    translator.assert_called_once_with({source: {"a": 1}})
    if expected_update is None:
        assert_state_not_updated(state)
    else:
        assert_state_updated(state, expected_update)


@pytest.mark.parametrize(
    ("has_data", "expected_call", "expected_update"),
    [
        (True, True, {"c": 3}),
        (False, False, None),
    ],
)
def test_translate_multidata_single(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
    has_data: bool,
    expected_call: bool,
    expected_update: Any,
) -> None:
    """Test single-state translation for present and missing data."""

    state = bind_state(source)

    data: dict[ARDataSource | ARDataType, Any] = (
        {source: {"a": 1}} if has_data else {}
    )
    translator = Mock(return_value={"c": 3})
    router._translate_multidata_single(translator, [state], data)

    if expected_call:
        translator.assert_called_once_with({"a": 1})
        assert_state_updated(state, expected_update)
    else:
        translator.assert_not_called()
        assert_state_not_updated(state)


@pytest.mark.parametrize("translator_result", [None, [1, 2, 3]])
def test_translate_multidata_single_forwards_translator_result(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
    translator_result: Any,
) -> None:
    """Test that single-state translation forwards translator output.

    The translator result should be passed through to the state.
    """

    state = bind_state(source)
    translator = Mock(return_value=translator_result)

    router._translate_multidata_single(translator, [state], {source: {"a": 1}})

    translator.assert_called_once_with({"a": 1})
    cast(Mock, state.update).assert_called_once_with(translator_result)


def test_translate_multidata_ignores_non_dict_multicaller_result(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
) -> None:
    """Test that _translate_multidata returns early for invalid data."""

    state = bind_state(source)

    router._translate_multidata(cast(Any, [1, 2, 3]), [state])

    assert_state_not_updated(state)


@pytest.mark.parametrize(
    ("is_batch", "expected_call_arg"),
    [
        (True, True),
        (False, False),
    ],
)
def test_translate_multidata_dispatches_to_correct_translator(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
    is_batch: bool,
    expected_call_arg: bool,
    universal_mock: UniversalMockPatcher,
) -> None:
    """Test _translate_multidata dispatch for batch and single translators."""

    state = bind_state(source)
    translator_result = {source: {"x": 1}} if is_batch else {"x": 1}
    translator = Mock(return_value=translator_result)
    state.translate_caller = translator

    universal_mock.patch(
        ARCallReg,
        "get_callable_flag",
        return_value=is_batch,
        mock_type=Mock,
    )

    router._translate_multidata({source: {"a": 1}}, [state])

    expected_arg = {source: {"a": 1}} if is_batch else {"a": 1}
    translator.assert_called_once_with(expected_arg)
    assert_state_updated(state, {"x": 1})


@pytest.mark.asyncio
@pytest.mark.parametrize("is_batch", [False, True])
async def test_async_refresh_data_state(
    router: AsusRouter,
    source: ARDataSource,
    bind_state: BindStateFactory,
    is_batch: bool,
    universal_mock: UniversalMockPatcher,
) -> None:
    """Test refresh behavior in _async_refresh_data_state."""

    callback = Mock()
    expected_arg: ARDataSource | list[ARDataSource]
    if is_batch:
        state_caller = AsyncMock(return_value={source: {"a": 1}})
        translator = None
        expected_update = {"a": 1}
        expected_arg = [source]
    else:
        state_caller = AsyncMock(return_value={"a": 1})
        translator = Mock(return_value={"transformed": 2})
        expected_update = {"transformed": 2}
        expected_arg = source

    state = bind_state(
        source,
        callback=callback,
        caller=state_caller,
        translator=translator,
    )

    universal_mock.patch(
        ARCallReg,
        "get_callable_flag",
        return_value=is_batch,
        mock_type=Mock,
    )

    cllctn = ARDataCollection.from_value(source)
    assert cllctn is not None
    await router._async_refresh_data_state(cllctn, force=True, extra_kw="x")

    cast(AsyncMock, state.state_caller).assert_awaited_once_with(
        callback,
        expected_arg,
        force=True,
        extra_kw="x",
    )

    if not is_batch:
        cast(Mock, translator).assert_called_once_with({"a": 1})
    assert_state_updated(state, expected_update)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cllctn",
    [
        ARDataCollection([]),
        ARDataCollection([ARDataSource()]),
    ],
    ids=["empty_collection", "missing_states"],
)
async def test_async_refresh_data_state_returns_without_state(
    router: AsusRouter,
    cllctn: ARDataCollection,
) -> None:
    """Test no-op refresh when there are no states."""

    await router._async_refresh_data_state(cllctn, force=True)
    assert router._data_states == {}


@pytest.mark.asyncio
async def test_async_get_data_state_rejects_invalid_source(
    router: AsusRouter,
) -> None:
    """Test async_get_data_state returns empty state for invalid sources."""

    result = await router.async_get_data_state(
        cast(Any, "invalid"), force=True
    )

    assert result == {}


@pytest.mark.asyncio
async def test_async_get_data_state_returns_current_states(
    router: AsusRouter,
    source: ARDataSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test async_get_data_state returns the created states."""

    sentinel = cast(ARDataState, Mock(spec=ARDataState))

    def create_side_effect(cllctn: ARDataCollection) -> bool:
        router._data_states[source] = sentinel
        return True

    mock_create = Mock(side_effect=create_side_effect)
    mock_refresh = AsyncMock(return_value=None)

    monkeypatch.setattr(router, "_create_data_state", mock_create)
    monkeypatch.setattr(router, "_async_refresh_data_state", mock_refresh)

    result = await router.async_get_data_state(
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "is_fresh_expected",
    [
        None,
        False,
        True,
    ],
)
async def test_async_get_data_v2(
    is_fresh_expected: bool | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the async_get_data_v2 method."""

    router = AsusRouter(hostname="h", username="u", password="p")
    source = ARDataSource()

    if is_fresh_expected is None:
        async_get = AsyncMock(return_value=None)
        expected_result = None
    else:
        content = {"ok": 1}
        fake_state = Mock()
        fake_state.content = content
        fake_state.is_fresh = Mock(return_value=is_fresh_expected)
        async_get = AsyncMock(return_value={source: fake_state})
        expected_result = {source: content} if is_fresh_expected else None

    monkeypatch.setattr(router, "async_get_data_state", async_get)

    result = await router.async_get_data_v2(source, force=True, extra_kw="x")

    async_get.assert_awaited_once_with(source, force=True, extra_kw="x")

    if is_fresh_expected is not None:
        fake_state.is_fresh.assert_called_once_with(router._cache_threshold)

    assert result == expected_result
