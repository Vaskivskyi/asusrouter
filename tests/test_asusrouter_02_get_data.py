"""Tests for the asusrouter module / Part 2 / Get Data."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.modules.source import (
    ARDataSource,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataType,
)

from .test_asusrouter_00_common import get_asusrouter_instance


class FakeState:
    """Fake state for testing."""

    def __init__(self) -> None:
        """Initialize mocks."""

        self.update = Mock()
        self.callback = Mock()


def test_get_callback_for_state() -> None:
    """Test the _get_callback_for_state method."""

    router = get_asusrouter_instance()
    callback = router._get_callback_for_state("state")  # type: ignore[arg-type]

    assert callback == router.async_api_load


@pytest.mark.parametrize(
    ("case", "expected_return", "expected_state_type", "prepopulate"),
    [
        ("datasource", True, ARDataStateDynamic, False),
        ("datatype", True, ARDataStateStatic, False),
        ("invalid", False, None, False),
        ("existing_datasource", True, "sentinel", True),
    ],
    ids=["datasource", "datatype", "invalid", "existing"],
)
def test_create_data_state(
    case: str,
    expected_return: bool,
    expected_state_type: type,
    prepopulate: bool,
) -> None:
    """Test the _create_data_state method."""

    router = get_asusrouter_instance()
    source: Any

    # Create the source
    if case == "datasource":
        source = ARDataSource()
    elif case == "datatype":
        source = ARDataType.UNKNOWN
    elif case == "invalid":
        source = object()
    elif case == "existing_datasource":
        source = ARDataSource()
    else:
        pytest.skip("unknown case")

    # Pre-populate router._data_states with a sentinel object
    sentinel = object()
    if prepopulate:
        router._data_states[source] = sentinel  # type: ignore[assignment]

    result = router._create_data_state(source)
    assert result is expected_return

    if prepopulate:
        # Check that the sentinel is still there
        assert router._data_states[source] is sentinel
    elif expected_return and expected_state_type is not None:
        # Ensure state created and is correct type
        state = router._data_states[source]
        assert isinstance(state, expected_state_type)
        # Callback should be assigned
        assert state.callback == router._get_callback_for_state(source)
    else:
        # When expected_return is False the state must not be added
        assert source not in router._data_states


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "case",
        "prepopulated",
        "data_caller_return",
        "translator_return",
        "expect_update_called",
        "expected_update_arg",
    ),
    [
        ("no_state", None, None, None, False, None),
        ("no_data_caller", FakeState(), None, None, False, None),
        (
            "wrong_data",
            FakeState(),
            None,
            None,
            False,
            None,
        ),
        (
            "data_with_translator",
            FakeState(),
            {"a": 1},
            {"b": 2},
            True,
            {"b": 2},
        ),
        ("data_no_translator", FakeState(), {"a": 1}, None, True, {"a": 1}),
    ],
)
async def test_async_refresh_data_state(
    case: str,
    prepopulated: FakeState | None,
    data_caller_return: dict[str, Any] | None,
    translator_return: dict[str, Any] | None,
    expect_update_called: bool,
    expected_update_arg: dict[str, Any] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the _async_refresh_data_state method."""

    router = get_asusrouter_instance()
    source = ARDataSource()

    # Prepare an available _data_states when needed
    if prepopulated:
        router._data_states[source] = prepopulated  # type: ignore[assignment]

    # Prepare the data_caller and translator
    if case != "no_state":
        data_caller = (
            None
            if case == "no_data_caller"
            else AsyncMock(return_value=data_caller_return)
        )

        translator = (
            None
            if translator_return is None
            else Mock(return_value=translator_return)
        )

    # Fake call and registry lookup
    def fake_get_callable(src: Any, name: Any = None) -> Any:
        """Fake get_callable."""

        if case == "no_state":
            return None
        if name == "get_state":
            return data_caller
        if name == "translate_state":
            return translator
        return None

    monkeypatch.setattr(
        "asusrouter.asusrouter.ARCallReg.get_callable",
        fake_get_callable,
        raising=True,
    )

    # Call the method
    await router._async_refresh_data_state(source, force=True, extra_kw="x")

    # No state -> nothing to update
    if not prepopulated:
        assert source not in router._data_states
        return

    # State exists
    if case in ("no_data_caller", "wrong_data"):
        # Caller or data is wrong
        prepopulated.update.assert_not_called()
        return

    # Data was returned; update should have been called once with expected arg
    if expect_update_called:
        prepopulated.update.assert_called_once_with(expected_update_arg)
        return

    prepopulated.update.assert_not_called()


@pytest.mark.asyncio
async def test_async_get_data_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the async_get_data_state method."""

    router = get_asusrouter_instance()
    source = ARDataSource()

    # Sentinel state that should be returned
    sentinel = object()

    # Patch _create_data_state to insert the sentinel and return True
    def create_side_effect(s: ARDataSource) -> bool:
        """Create a data state."""

        router._data_states[s] = sentinel  # type: ignore[assignment]
        return True

    mock_create = Mock(side_effect=create_side_effect)
    mock_refresh = AsyncMock(return_value=None)

    monkeypatch.setattr(router, "_create_data_state", mock_create)
    monkeypatch.setattr(router, "_async_refresh_data_state", mock_refresh)

    result = await router.async_get_data_state(
        source, force=True, extra_kw="x"
    )

    mock_create.assert_called_once_with(source)
    mock_refresh.assert_awaited_once_with(source, force=True, extra_kw="x")
    assert result is sentinel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("is_fresh_expected", "expected_result"),
    [
        (None, None),  # async_get_data_state returns None -> result None
        (False, None),  # state present but not fresh -> result None
        (True, {"ok": 1}),  # state present and fresh -> return content
    ],
)
async def test_async_get_data_v2(
    is_fresh_expected: bool | None,
    expected_result: dict[str, Any] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the async_get_data_v2 method."""
    router = AsusRouter(hostname="h", username="u", password="p")
    source = ARDataSource()

    # Patch async_get_data_state on the router instance
    if is_fresh_expected is None:
        async_get = AsyncMock(return_value=None)
        monkeypatch.setattr(router, "async_get_data_state", async_get)
    else:
        # create a fake state with content and a mockable is_fresh method
        content = {"ok": 1}
        fake_state = Mock()
        fake_state.content = content
        fake_state.is_fresh = Mock(return_value=is_fresh_expected)
        async_get = AsyncMock(return_value=fake_state)
        monkeypatch.setattr(router, "async_get_data_state", async_get)

    # Call under test
    result = await router.async_get_data_v2(source, force=True, extra_kw="x")

    # async_get_data_state must be awaited with the same args
    async_get.assert_awaited_once_with(source, force=True, extra_kw="x")

    # If a fake state was returned, its is_fresh should be checked
    # with the router threshold
    if is_fresh_expected is not None:
        fake_state.is_fresh.assert_called_once_with(router._cache_threshold)

    assert result == expected_result
