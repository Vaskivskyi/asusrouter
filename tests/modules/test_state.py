"""Tests for the state module."""

from typing import Any
from unittest import mock

from asusrouter import AsusData
from asusrouter.modules.state import (
    AsusState,
    _get_module,
    _get_module_name,
    _has_method,
    add_conditional_state,
    get_datatype,
    keep_state,
    save_state,
    set_state,
)
from asusrouter.modules.system import AsusSystem
from asusrouter.modules.vpnc import AsusVPNC
from asusrouter.modules.wlan import AsusWLAN
import pytest

mock_state_map = {
    AsusState.SYSTEM: AsusData.SYSTEM,
    AsusState.VPNC: AsusData.VPNC,
    AsusState.WLAN: AsusData.WLAN,
    AsusState.NONE: None,
}


class MockModule:
    """Mock module."""

    def __init__(
        self, require_state: bool = False, require_identity: bool = False
    ) -> None:
        """Initialize the mock module."""

        self.REQUIRE_STATE = require_state  # pylint: disable=invalid-name
        self.REQUIRE_IDENTITY = require_identity  # pylint: disable=invalid-name

        self.update_state = mock.Mock()
        self.offset_time = mock.Mock()

    async def set_state(self, **_: Any) -> bool:
        """Set the state."""

        return True

    async def keep_state(self, *_: Any, **__: Any) -> None:
        """Keep the state."""

        return


@pytest.mark.parametrize(
    ("state", "data", "success"),
    [
        # Existing values of AsusState
        (AsusState.LED, AsusData.LED, True),
        (AsusState.WIREGUARD_CLIENT, AsusData.WIREGUARD_CLIENT, True),
        (AsusState.PARENTAL_CONTROL, AsusData.PARENTAL_CONTROL, True),
        # Partial data
        (AsusState.PORT_FORWARDING, None, False),
        (None, AsusData.LED, False),
        # None
        (None, None, False),
        # Wrong types
        (1, AsusData.SYSTEM, False),
        (AsusState.CONNECTION, 1, False),
    ],
)
def test_add_conditional_state(
    state: AsusState, data: AsusData | None, success: bool
) -> None:
    """Test add_conditional_state."""

    # Try to add the state
    with mock.patch("asusrouter.modules.state.AsusStateMap", mock_state_map):
        add_conditional_state(state, data)

    # Check the result
    if success:
        assert mock_state_map[state] == data
    else:
        assert state not in mock_state_map


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        # Existing values of AsusState
        (AsusSystem.REBOOT, AsusData.SYSTEM),
        (AsusVPNC.ON, AsusData.VPNC),
        (AsusWLAN.OFF, AsusData.WLAN),
        # None
        (None, None),
        # Wrong types
        (1, None),
        ("string", None),
    ],
)
def test_get_datatype(
    state: AsusState | None, expected: AsusData | None
) -> None:
    """Test get_datatype."""

    # Try to get the datatype
    with mock.patch("asusrouter.modules.state.AsusStateMap", mock_state_map):
        result = get_datatype(state)

    # Check the result
    assert result == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        # Existing values of AsusState
        (AsusState.SYSTEM, AsusData.SYSTEM.value),
        (AsusState.VPNC, AsusData.VPNC.value),
        (AsusState.WLAN, AsusData.WLAN.value),
        # None
        (None, None),
        # Wrong types
        (1, None),
        ("string", None),
    ],
)
def test_get_module_name(
    state: AsusState | None, expected: str | None
) -> None:
    """Test _get_module_name."""

    # Mock the get_datatype function
    with mock.patch(
        "asusrouter.modules.state.get_datatype",
        lambda s: mock_state_map.get(s),
    ):
        result = _get_module_name(state)

    # Check the result
    assert result == expected


@pytest.mark.parametrize(
    (
        "state",
        "module_name",
        "expected_module",
        "import_result",
        "import_exception",
        "expected",
    ),
    [
        # Existing values of AsusState
        (
            AsusState.SYSTEM,
            "system",
            "system",
            mock.MagicMock(),
            None,
            "mock_module",
        ),
        (
            AsusState.VPNC,
            "vpnc",
            "vpnc",
            mock.MagicMock(),
            None,
            "mock_module",
        ),
        (
            AsusState.WLAN,
            "wlan",
            "wlan",
            mock.MagicMock(),
            None,
            "mock_module",
        ),
        (
            AsusState.WIREGUARD_CLIENT,
            "wireguard_client",
            "wireguard",
            mock.MagicMock(),
            None,
            "mock_module",
        ),
        # ModuleNotFoundError
        (
            AsusState.SYSTEM,
            "system",
            "system",
            None,
            ModuleNotFoundError,
            None,
        ),
        # None
        (None, None, None, None, None, None),
        # Wrong types
        (1, None, None, None, None, None),
        ("string", None, None, None, None, None),
    ],
)
def test_get_module(  # noqa: PLR0913
    state: AsusState | None,
    module_name: str | None,
    expected_module: str | None,
    import_result: Any,
    import_exception: Exception | None,
    expected: str | None,
) -> None:
    """Test _get_module."""

    # Mock the _get_module_name function and importlib.import_module function
    with (
        mock.patch(
            "asusrouter.modules.state._get_module_name",
            return_value=module_name,
        ),
        mock.patch("importlib.import_module") as mock_import,
    ):
        mock_import.return_value = import_result
        mock_import.side_effect = import_exception
        result = _get_module(state)
        if expected_module and import_result is not None:
            mock_import.assert_called_once_with(
                f"asusrouter.modules.{expected_module}"
            )

    # Check the result
    assert (result is not None) == (expected is not None)


@pytest.mark.parametrize(
    ("module", "method", "expected"),
    [
        # Existing method
        (MockModule(), "set_state", True),
        # Non-existing method
        (MockModule(), "non_existing_method", False),
    ],
)
def test_has_method(module: MockModule, method: str, expected: bool) -> None:
    """Test _has_method."""

    result = _has_method(module, method)

    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("has_method", "require_state", "require_identity", "expected"),
    [
        (True, False, False, True),
        (True, True, False, True),
        (True, False, True, True),
        (False, False, False, False),
    ],
)
async def test_set_state(
    has_method: bool,
    require_state: bool,
    require_identity: bool,
    expected: bool,
) -> None:
    """Test set_state."""

    # Mock the _get_module function and _has_method function
    with (
        mock.patch(
            "asusrouter.modules.state._get_module",
            return_value=MockModule(require_state, require_identity),
        ),
        mock.patch(
            "asusrouter.modules.state._has_method", return_value=has_method
        ),
    ):
        result = await set_state(mock.AsyncMock(), AsusState.SYSTEM)

    assert result == expected


@pytest.mark.parametrize(
    ("state", "datatype"),
    [
        (AsusState.VPNC, AsusData.VPNC),
        (AsusState.VPNC, None),
    ],
)
def test_save_state(state: AsusState, datatype: AsusData | None) -> None:
    """Test save_state."""

    # Mock the get_datatype function
    with mock.patch(
        "asusrouter.modules.state.get_datatype", return_value=datatype
    ):
        # Mock the AsusDataState objects
        library = {AsusData.VPNC: MockModule()}

        # Call the function
        save_state(state, library)

    # Check the calls to the AsusDataState methods
    if datatype is not None:
        library[datatype].update_state.assert_called_once_with(state, None)
        library[datatype].offset_time.assert_called_once_with(None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("states", "has_method", "expected"),
    [
        ([AsusState.SYSTEM], True, None),
        (AsusState.SYSTEM, True, None),  # Single value, not a list
        ([AsusState.SYSTEM], False, None),
        (None, False, None),
    ],
)
async def test_keep_state(
    states: list[AsusState] | None, has_method: bool, expected: bool | None
) -> None:
    """Test keep_state."""

    # Mock the _get_module function and _has_method function
    with (
        mock.patch(
            "asusrouter.modules.state._get_module", return_value=MockModule()
        ),
        mock.patch(
            "asusrouter.modules.state._has_method", return_value=has_method
        ),
    ):
        result = await keep_state(mock.AsyncMock(), states)

    assert result == expected
