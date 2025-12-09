"""Test for the main endpoint module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asusrouter.const import RequestType
from asusrouter.error import AsusRouter404Error, AsusRouterRequestFormatError
from asusrouter.modules.endpoint import (
    SENSITIVE_ENDPOINTS,
    Endpoint,
    EndpointService,
    EndpointTools,
    EndpointType,
    _get_module,
    check_available,
    data_get,
    data_set,
    get_request_type,
    is_sensitive_endpoint,
    process,
    read,
)

TEST_SENSITIVE_ENDPOINTS: tuple[EndpointType, ...] = (EndpointService.LOGIN,)
IDS_SENSITIVE_ENDPOINTS = ("login",)


@pytest.mark.parametrize(
    ("endpoint"), TEST_SENSITIVE_ENDPOINTS, ids=IDS_SENSITIVE_ENDPOINTS
)
def test_marked_sensitive_endpoint(endpoint: EndpointType) -> None:
    """Test if the endpoint is marked as sensitive."""

    assert endpoint in SENSITIVE_ENDPOINTS
    assert is_sensitive_endpoint(endpoint) is True


def test_sensitive_endpoints_immutable() -> None:
    """SENSITIVE_ENDPOINTS should be an immutable frozenset."""

    assert isinstance(SENSITIVE_ENDPOINTS, frozenset)
    # Attempting to call add should raise AttributeError
    with pytest.raises(AttributeError):
        SENSITIVE_ENDPOINTS.add(EndpointService.LOGOUT)  # type: ignore[attr-defined]

    # union returns a new frozenset; original remains unchanged
    new_set = SENSITIVE_ENDPOINTS | frozenset({EndpointService.LOGOUT})
    assert isinstance(new_set, frozenset)
    assert EndpointService.LOGOUT not in SENSITIVE_ENDPOINTS
    assert EndpointService.LOGOUT in new_set


@pytest.mark.parametrize(
    ("endpoint", "forced_request"),
    [
        (Endpoint.PORT_STATUS, RequestType.GET),
        (EndpointTools.NETWORK, RequestType.GET),
        (EndpointTools.TRAFFIC_BACKHAUL, RequestType.GET),
        (EndpointTools.TRAFFIC_ETHERNET, RequestType.GET),
        (EndpointTools.TRAFFIC_WIFI, RequestType.GET),
        (EndpointService.LOGIN, RequestType.POST),
    ],
)
def test_get_request_type(
    endpoint: EndpointType, forced_request: RequestType
) -> None:
    """Test get_request_type function."""

    assert get_request_type(endpoint) == forced_request


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (EndpointService.LOGIN, True),
        (Endpoint.PORT_STATUS, False),
        (EndpointTools.NETWORK, False),
        (EndpointService.LOGOUT, False),
    ],
)
def test_is_sensitive_endpoint(
    endpoint: EndpointType,
    expected: bool,
) -> None:
    """is_sensitive_endpoint returns True only for sensitive endpoints."""

    assert is_sensitive_endpoint(endpoint) is expected


def test_get_module() -> None:
    """Test _get_module method."""

    # Test valid endpoint
    with patch(
        "importlib.import_module", return_value="mocked_module"
    ) as mock_import:
        result = _get_module(Endpoint.PORT_STATUS)
        assert result == "mocked_module"  # type: ignore[comparison-overlap]
        mock_import.assert_called_once_with(
            "asusrouter.modules.endpoint.port_status"
        )

    # Test invalid endpoint
    with patch("importlib.import_module") as mock_import:
        mock_import.side_effect = ModuleNotFoundError
        result = _get_module(Endpoint.FIRMWARE)
        assert result is None
        mock_import.assert_called_once_with(
            "asusrouter.modules.endpoint.firmware"
        )


def test_read() -> None:
    """Test read method."""

    # Mock the module and its read method
    mock_module = MagicMock()
    mock_module.read.return_value = {"mocked": "data"}

    # Test valid endpoint
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ) as mock_get_module:
        result = read(Endpoint.FIRMWARE, "content")
        assert result == {"mocked": "data"}
        mock_get_module.assert_called_once_with(Endpoint.FIRMWARE)
        mock_module.read.assert_called_once_with("content")

    # Test invalid endpoint
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=None
    ) as mock_get_module:
        result = read(Endpoint.PORT_STATUS, "content")
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.PORT_STATUS)


def test_read_module_return_fail() -> None:
    """Test read method when the module returns wrong result."""

    mock_module = MagicMock()
    mock_module.read.return_value = "not_a_dict"

    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ) as mock_get_module:
        result = read(Endpoint.FIRMWARE, "content")
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.FIRMWARE)


@pytest.mark.parametrize(
    ("require_history", "require_firmware", "require_wlan", "call_count"),
    [
        (True, False, False, 1),
        (False, True, False, 1),
        (False, False, True, 1),
        (False, False, False, 0),
        (True, True, True, 3),
    ],
)
def test_process(
    require_history: bool,
    require_firmware: bool,
    require_wlan: bool,
    call_count: int,
) -> None:
    """Test process method."""

    # Mock the module and its process method
    mock_module = MagicMock()
    mock_module.process.return_value = {"mocked": "data"}

    # Mock the data_set function
    mock_data_set = MagicMock()

    # Define a side effect function for getattr
    def getattr_side_effect(
        _: object, attr: str, default: bool | None = None
    ) -> bool | None:
        """Return the value of the attribute if it exists."""

        if attr == "REQUIRE_HISTORY":
            return require_history
        if attr == "REQUIRE_FIRMWARE":
            return require_firmware
        if attr == "REQUIRE_WLAN":
            return require_wlan
        return bool(default) if default is not None else None

    # Test valid endpoint
    with (
        patch(
            "asusrouter.modules.endpoint._get_module", return_value=mock_module
        ),
        patch("asusrouter.modules.endpoint.data_set", mock_data_set),
        patch(
            "asusrouter.modules.endpoint.getattr",
            side_effect=getattr_side_effect,
        ),
    ):
        result = process(Endpoint.DEVICEMAP, {"key": "value"})
        assert result == {"mocked": "data"}
        mock_module.process.assert_called_once_with({"key": "value"})
        assert mock_data_set.call_count == call_count


def test_process_no_module() -> None:
    """Test process method when no module is found."""

    # Mock the _get_module function to return None
    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=None
    ) as mock_get_module:
        result = process(Endpoint.PORT_STATUS, {"key": "value"})
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.PORT_STATUS)


def test_process_module_return_fail() -> None:
    """Test process method when the module returns wrong result."""

    mock_module = MagicMock()
    mock_module.process.return_value = "not_a_dict"

    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ) as mock_get_module:
        result = process(Endpoint.DEVICEMAP, {"key": "value"})
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.DEVICEMAP)


@pytest.mark.parametrize(
    ("error"),
    [
        AttributeError,
        ValueError,
    ],
)
def test_process_module_raises(error: type[Exception]) -> None:
    """Test process method when an exception is raised."""

    mock_module = MagicMock()
    mock_module.process.side_effect = error

    with patch(
        "asusrouter.modules.endpoint._get_module", return_value=mock_module
    ) as mock_get_module:
        result = process(Endpoint.DEVICEMAP, {"key": "value"})
        assert result == {}
        mock_get_module.assert_called_once_with(Endpoint.DEVICEMAP)


def test_data_set() -> None:
    """Test data_set function."""

    # Test data
    data = {"key1": "value1"}
    kwargs = {"key2": "value2", "key3": "value3"}

    # Call the function
    result = data_set(data, **kwargs)

    # Check the result
    assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}


@pytest.mark.parametrize(
    ("data", "key", "expected", "data_left"),
    [
        # Key exists
        (
            {"key1": "value1", "key2": "value2"},
            "key1",
            "value1",
            {"key2": "value2"},
        ),
        # Key does not exist
        (
            {"key1": "value1", "key2": "value2"},
            "key3",
            None,
            {"key1": "value1", "key2": "value2"},
        ),
        # Empty data
        ({}, "key1", None, {}),
    ],
)
def test_data_get(
    data: dict[str, str],
    key: str,
    expected: str | None,
    data_left: dict[str, str],
) -> None:
    """Test data_get function."""

    # Call the function
    result = data_get(data, key)

    # Check the result
    assert result == expected
    assert data == data_left


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("api_query_return", "expected_result"),
    [
        # Test case: status 200
        ((200, None, None), (True, None)),
        # Test case: status 200 and content
        ((200, None, "content"), (True, "content")),
        # Test case: status not 200
        ((403, None, None), (False, None)),
        # Test case: AsusRouterRequestFormatError is raised
        (AsusRouterRequestFormatError(), (True, None)),
        # Test case: AsusRouter404Error is raised
        (AsusRouter404Error(), (False, None)),
    ],
)
async def test_check_available(
    api_query_return: tuple[int, str | None, str | None],
    expected_result: tuple[bool, str | None],
) -> None:
    """Test check_available function."""

    # Mock the api_query function
    api_query = AsyncMock()
    if isinstance(api_query_return, Exception):
        api_query.side_effect = api_query_return
    else:
        api_query.return_value = api_query_return

    # Call the function
    result = await check_available(Endpoint.DEVICEMAP, api_query)

    # Check the result
    assert result == expected_result
