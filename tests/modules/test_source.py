"""Tests for the Source module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from asusrouter.modules import source
from asusrouter.modules.source import (
    ARDataCollection,
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataTypeGeneric,
)

datetime_value = datetime(2025, 8, 1, 12, 1, 5)


class _AltSource(ARDataSource):
    """A distinct source type (sources are equal by exact type)."""


class TestARDataCollection:
    """Class for testing ARDataCollection."""

    @pytest.mark.parametrize(
        ("source", "length"),
        [
            (ARDataSource(), 1),
            ([ARDataSource(), ARDataTypeGeneric.UNKNOWN], 2),
            ({ARDataSource(), ARDataTypeGeneric.UNKNOWN, _AltSource()}, 3),
            (list(ARDataTypeGeneric), 1),
        ],
    )
    def test_from_value_valid(self, source: Any, length: int) -> None:
        """Test creating a collection from valid sources."""

        collection = ARDataCollection.from_value(source)

        if isinstance(source, (list, tuple, dict, set)):
            source = list(source)
        else:
            source = [source]

        assert collection is not None
        assert len(collection) == len(source) == length
        assert list(collection) == source

    def test_from_value_generator(self) -> None:
        """Test creating a collection from a generator."""

        _ar_data_source = ARDataSource()

        source = (
            item for item in [_ar_data_source, ARDataTypeGeneric.UNKNOWN]
        )
        collection = ARDataCollection.from_value(source)

        assert collection is not None
        assert list(collection) == [_ar_data_source, ARDataTypeGeneric.UNKNOWN]

    @pytest.mark.parametrize(
        "source",
        [
            "string",
            b"bytes",
            bytearray(b"data"),
            object(),
            ["string", object()],
        ],
    )
    def test_from_value_invalid(self, source: Any) -> None:
        """Test that invalid scalar values return None."""

        assert ARDataCollection.from_value(source) is None

    def test_from_value_ignores_invalid(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid iterable items are ignored with a warning."""

        source_item = ARDataSource()
        invalid_items = [object(), "bad"]

        caplog.set_level(logging.WARNING, logger="asusrouter.modules.source")
        result = ARDataCollection.from_value([source_item, *invalid_items])

        assert result is not None
        assert list(result) == [source_item]
        assert "Ignored invalid items for ARDataCollection" in caplog.text

    def test_iter(self) -> None:
        """Test iteration over the collection."""

        source_items = [ARDataSource(), ARDataTypeGeneric.UNKNOWN]
        collection = ARDataCollection.from_value(source_items)

        assert collection is not None
        assert list(collection) == source_items

    def test_len(self) -> None:
        """Test the length of the collection."""

        source_items = [ARDataSource(), ARDataTypeGeneric.UNKNOWN]
        collection = ARDataCollection.from_value(source_items)

        assert collection is not None
        assert len(collection) == len(source_items)

    def test_getitem(self) -> None:
        """Test that slicing and indexing returns correct types."""

        source_items = [ARDataSource(), ARDataTypeGeneric.UNKNOWN]
        collection = ARDataCollection.from_value(source_items)

        assert collection is not None
        sliced = collection[0:1]

        assert isinstance(sliced, ARDataCollection)
        assert list(sliced) == [source_items[0]]

        indexed = collection[1]
        assert indexed == source_items[1]

    def test_bool(self) -> None:
        """Test boolean behavior of the collection."""

        source_item = ARDataSource()
        collection = ARDataCollection([source_item])
        empty_collection = ARDataCollection([])

        assert collection
        assert not empty_collection

    def test_repr(self) -> None:
        """Test the string representation of the collection."""

        source_items = [ARDataSource(), ARDataTypeGeneric.UNKNOWN]
        collection = ARDataCollection.from_value(source_items)

        assert collection is not None
        expected_repr = f"ARDataCollection({source_items!r})"
        assert repr(collection) == expected_repr


class TestARDataSource:
    """Class for testing ARDataSource."""

    def test_equal_by_type(self) -> None:
        """Sources are equal and hash alike by exact type."""

        assert ARDataSource() == ARDataSource()
        assert ARDataSource() != _AltSource()
        assert hash(ARDataSource()) == hash(ARDataSource())

    def test_equality_other_type(self) -> None:
        """Comparison with a non-source returns NotImplemented / False."""

        assert ARDataSource().__eq__("x") is NotImplemented
        assert (ARDataSource() == "x") is False


class TestARDataState:
    """Class for testing ARDataState."""

    @pytest.mark.parametrize(
        ("source", "success"),
        [
            # Valid types
            (ARDataSource(), True),
            (ARDataTypeGeneric.UNKNOWN, True),
            # Invalid types
            (object(), False),
            ("string", False),
            (None, False),
        ],
    )
    def test_init(self, source: Any, success: bool) -> None:
        """Test the initialization."""

        if success:
            instance = ARDataState(source)

            assert instance._source == source
            assert instance._content is None
            assert instance._last_update is None
            assert instance._callback is None
            return

        with pytest.raises(
            TypeError,
            match="A valid `ARDataSource` or `ARDataType` is required",
        ):
            ARDataState(source)

    @pytest.mark.parametrize(
        "content",
        [
            {"key": "value"},
            ["item1", "item2"],
            None,
            "string",
            object(),
        ],
    )
    def test_update(
        self, content: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the update method."""

        mock_now = Mock(return_value=datetime_value)
        monkeypatch.setattr(source, "datetime", SimpleNamespace(now=mock_now))

        instance = ARDataState(ARDataTypeGeneric.UNKNOWN)
        instance.update(content)

        mock_now.assert_called_once_with(UTC)

        assert instance._content == content
        assert instance._last_update == datetime_value

    def test_expire(self) -> None:
        """Test that expire drops the last-update timestamp."""

        instance = ARDataState(ARDataTypeGeneric.UNKNOWN)
        instance._content = "content"
        instance._last_update = datetime_value

        instance.expire()

        assert instance._last_update is None
        # Content is kept; only freshness is invalidated
        assert instance._content == "content"
        assert instance.is_fresh(threshold=timedelta(seconds=5)) is False

    @pytest.mark.parametrize("is_fresh", [True, False, None])
    def test_is_fresh(
        self, is_fresh: bool | None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the is_fresh method."""

        instance = ARDataState(ARDataTypeGeneric.UNKNOWN)

        threshold = timedelta(seconds=5)

        # No last update
        if is_fresh is None:
            result = instance.is_fresh(threshold=threshold)
            assert result is False

        # With last update
        mock_now = Mock(return_value=datetime_value)
        monkeypatch.setattr(source, "datetime", SimpleNamespace(now=mock_now))

        # Fresh
        if is_fresh is True:
            instance._last_update = (
                datetime_value - threshold + timedelta(seconds=1)
            )

            result = instance.is_fresh(threshold=threshold)
            assert result is True
            return

        # Stale
        instance._last_update = (
            datetime_value - threshold - timedelta(seconds=1)
        )
        result = instance.is_fresh(threshold=threshold)
        assert result is False

    @pytest.mark.parametrize(
        "threshold",
        [
            "string",
            5,
            None,
            object(),
        ],
    )
    def test_is_fresh_invalid_threshold(self, threshold: Any) -> None:
        """Test the is_fresh method with invalid threshold."""

        instance = ARDataState(ARDataTypeGeneric.UNKNOWN)

        with pytest.raises(TypeError, match="A valid `timedelta` is required"):
            instance.is_fresh(threshold=threshold)

    def test_properties(self) -> None:
        """Test the properties."""

        source = ARDataTypeGeneric.UNKNOWN
        instance = ARDataState(source)

        async def mock_async_callback() -> None:
            """Mock an async callback."""

        async def mock_async_callable() -> None:
            """Mock async callable."""

        async def mock_async_translate() -> None:
            """Mock async translate callable."""

        # Mock the properties
        instance._content = "content"
        instance._last_update = datetime_value
        instance._callback = mock_async_callback
        instance._state_caller = mock_async_callable
        instance._translate_caller = mock_async_translate
        instance._state_caller_multi = True
        instance._translate_caller_multi = True

        assert instance.source == source
        assert instance.content == "content"
        assert instance.last_update == datetime_value
        assert instance.callback == mock_async_callback
        assert instance.state_caller == mock_async_callable
        assert instance.translate_caller == mock_async_translate
        assert instance.state_caller_multi is True
        assert instance.translate_caller_multi is True

    def test_setters(self) -> None:
        """Test the setters for the properties."""

        instance = ARDataState(ARDataTypeGeneric.UNKNOWN)

        async def mock_async_callback() -> None:
            """Mock an async callback."""

        async def mock_async_callable() -> None:
            """Mock async callable."""

        async def mock_async_translate() -> None:
            """Mock async translate callable."""

        instance.callback = mock_async_callback
        instance.state_caller = mock_async_callable
        instance.translate_caller = mock_async_translate
        instance.state_caller_multi = 1
        instance.translate_caller_multi = 1

        assert instance.callback == mock_async_callback
        assert instance.state_caller == mock_async_callable
        assert instance.translate_caller == mock_async_translate
        assert instance.state_caller_multi is True
        assert instance.translate_caller_multi is True


class TestARDataStateRefresh:
    """Class for testing the ARDataState in-flight refresh marker."""

    def test_refresh_cycle(self) -> None:
        """begin/end toggle the refreshing flag; end is idempotent."""

        state = ARDataState(ARDataSource())
        assert state.refreshing is False

        state.begin_refresh()
        assert state.refreshing is True

        state.end_refresh()
        assert state.refreshing is False

        # Ending an idle state is a no-op
        state.end_refresh()
        assert state.refreshing is False

    @pytest.mark.asyncio
    async def test_wait_refresh_noop_when_idle(self) -> None:
        """Waiting on an idle state returns immediately."""

        state = ARDataState(ARDataSource())
        await state.async_wait_refresh()

    @pytest.mark.asyncio
    async def test_wait_refresh_wakes_on_end(self) -> None:
        """A waiter is woken when the refresh ends."""

        state = ARDataState(ARDataSource())
        state.begin_refresh()

        waiter = asyncio.ensure_future(state.async_wait_refresh())
        await asyncio.sleep(0)
        assert not waiter.done()

        state.end_refresh()
        await waiter


class TestARDataStateStatic:
    """Class for testing ARDataStateStatic."""

    def test_init(self) -> None:
        """Test the initialization."""

        inst_source = ARDataTypeGeneric.UNKNOWN
        instance = ARDataStateStatic(inst_source)

        assert isinstance(instance, ARDataStateStatic)
        assert issubclass(instance.__class__, ARDataState)
        assert instance._source == inst_source
        assert instance._content is None
        assert instance._last_update is None
        assert instance._callback is None

    def test_property_source(self) -> None:
        """Test the source property."""

        inst_source = ARDataTypeGeneric.UNKNOWN
        instance = ARDataStateStatic(inst_source)

        assert instance.source is inst_source

    def test_init_wrong_type(self) -> None:
        """A non-ARDataType source is rejected."""

        with pytest.raises(TypeError):
            ARDataStateStatic(ARDataSource())  # type: ignore[arg-type]


class TestARDataStateDynamic:
    """Class for testing ARDataStateDynamic."""

    def test_init(self) -> None:
        """Test the initialization."""

        inst_source = ARDataSource()
        instance = ARDataStateDynamic(inst_source)

        assert isinstance(instance, ARDataStateDynamic)
        assert issubclass(instance.__class__, ARDataState)
        assert instance._source == inst_source
        assert instance._content is None
        assert instance._last_update is None
        assert instance._callback is None

    def test_property_source(self) -> None:
        """Test the source property."""

        inst_source = ARDataSource()
        instance = ARDataStateDynamic(inst_source)

        assert instance.source is inst_source

    def test_init_wrong_type(self) -> None:
        """A non-ARDataSource source is rejected."""

        with pytest.raises(TypeError):
            ARDataStateDynamic(ARDataTypeGeneric.UNKNOWN)  # type: ignore[arg-type]
