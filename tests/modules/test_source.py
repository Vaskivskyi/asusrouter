"""Tests for the Source module."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest

from asusrouter.modules import source
from asusrouter.modules.source import (
    ARDataSource,
    ARDataState,
    ARDataStateDynamic,
    ARDataStateStatic,
    ARDataType,
)

datetime_value = datetime(2025, 8, 1, 12, 1, 5)


class TestARDataState:
    """Class for testing ARDataState."""

    @pytest.mark.parametrize(
        ("source", "success"),
        [
            # Valid types
            (ARDataSource(), True),
            (ARDataType.UNKNOWN, True),
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

        instance = ARDataState(ARDataType.UNKNOWN)
        instance.update(content)

        mock_now.assert_called_once_with(UTC)

        assert instance._content == content
        assert instance._last_update == datetime_value

    @pytest.mark.parametrize("is_fresh", [True, False, None])
    def test_is_fresh(
        self, is_fresh: bool | None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the is_fresh method."""

        instance = ARDataState(ARDataType.UNKNOWN)

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

        instance = ARDataState(ARDataType.UNKNOWN)

        with pytest.raises(TypeError, match="A valid `timedelta` is required"):
            instance.is_fresh(threshold=threshold)

    def test_properties(self) -> None:
        """Test the properties."""

        instance = ARDataState(ARDataType.UNKNOWN)

        async def mock_async_callback() -> None:
            """Mock an async callback."""

        # Mock the properties
        instance._content = "content"
        instance._last_update = datetime_value
        instance._callback = mock_async_callback

        assert instance.content == "content"
        assert instance.last_update == datetime_value
        assert instance.callback == mock_async_callback

    def test_setter_callback(self) -> None:
        """Test the setter for the callback property."""

        instance = ARDataState(ARDataType.UNKNOWN)

        async def mock_async_callback() -> None:
            """Mock an async callback."""

        instance.callback = mock_async_callback
        assert instance.callback == mock_async_callback


class TestARDataStateStatic:
    """Class for testing ARDataStateStatic."""

    def test_init(self) -> None:
        """Test the initialization."""

        inst_source = ARDataType.UNKNOWN
        instance = ARDataStateStatic(inst_source)

        assert isinstance(instance, ARDataStateStatic)
        assert issubclass(instance.__class__, ARDataState)
        assert instance._source == inst_source
        assert instance._content is None
        assert instance._last_update is None
        assert instance._callback is None

    def test_property_source(self) -> None:
        """Test the source property."""

        inst_source = ARDataType.UNKNOWN
        instance = ARDataStateStatic(inst_source)

        with patch(
            "asusrouter.modules.source.ARDataType.from_value",
            return_value=inst_source,
        ) as mock_from_value:
            result = instance.source
            mock_from_value.assert_called_once_with(instance._source)
            assert result == inst_source


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
        result = instance.source
        assert result == inst_source

        inst_source_wrong = ARDataType.UNKNOWN
        instance = ARDataStateDynamic(inst_source_wrong)  # type: ignore[arg-type]
        result = instance.source
        # It should return a new instance of ARDataSource
        assert isinstance(result, ARDataSource)
