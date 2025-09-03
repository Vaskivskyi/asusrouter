"""Tests for the Traffic module."""

import importlib
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from asusrouter.const import (
    AR_CALL_GET_STATE,
    AR_CALL_TRANSLATE_STATE,
    HTTPStatus,
)
from asusrouter.modules.endpoint import EndpointTools
from asusrouter.modules.source import ARDataSource
import asusrouter.modules.traffic as traffic_module
from asusrouter.modules.traffic import (
    ARTrafficSource,
    ARTrafficSourceBackhaul,
    ARTrafficSourceBetween,
    ARTrafficSourceEthernet,
    ARTrafficSourceWiFi,
    ARTrafficType,
    _check_state,
    get_state,
    translate_state,
)
from asusrouter.tools.identifiers import MacAddress

vtarget = MacAddress("00:11:22:33:44:55")
vtype = None
vtowards = MacAddress("11:22:33:44:55:66")


class TestARTrafficSource:
    """Class for testing ARTrafficSource."""

    def test_init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the initialization."""

        vtarget = "target"
        vtype = "type"

        target_calls: list[object] = []
        type_calls: list[object] = []

        # Keep original getters so reading still works
        orig_target_get = ARTrafficSource.__dict__["target"].fget
        orig_type_get = ARTrafficSource.__dict__["type"].fget

        def fake_set_target(self: ARTrafficSource, value: Any) -> None:
            """Fake setter for target."""

            target_calls.append(value)
            # Emulate original behaviour enough for assertions
            self._target = value

        def fake_set_type(self: ARTrafficSource, value: Any) -> None:
            """Fake setter for type."""

            type_calls.append(value)
            self._type = value

        # Replace the properties on the class
        monkeypatch.setattr(
            ARTrafficSource,
            "target",
            property(orig_target_get, fake_set_target),
            raising=True,
        )
        monkeypatch.setattr(
            ARTrafficSource,
            "type",
            property(orig_type_get, fake_set_type),
            raising=True,
        )

        instance = ARTrafficSource(vtarget, vtype)

        assert isinstance(instance, ARTrafficSource)
        assert issubclass(instance.__class__, ARDataSource)

        # Verify setters were invoked exactly once with expected values
        assert target_calls == [vtarget]
        assert type_calls == [vtype]

    def test_repr(self) -> None:
        """Test the __repr__ method."""

        traffic_type = ARTrafficType.WIFI

        instance = ARTrafficSource("target", traffic_type)
        assert repr(instance) == f"<ARTrafficSource type=`{traffic_type}`>"

    def test_properties(self) -> None:
        """Test the properties."""

        traffic_type = ARTrafficType.WIFI

        instance = ARTrafficSource(vtarget, traffic_type)

        assert instance.target == vtarget
        assert instance.type == traffic_type

    def test_setter_target(self) -> None:
        """Test the target setter."""

        instance = ARTrafficSource(vtarget)

        # Test with a real new target
        instance.target = vtowards
        assert instance.target == vtowards

        # Test with an invalid new target
        new_target_wrong = "string"
        instance.target = new_target_wrong  # type: ignore[assignment]
        assert instance.target is None

    def test_setter_type(self) -> None:
        """Test the type setter."""

        traffic_type = ARTrafficType.WIFI

        instance = ARTrafficSource(vtarget, traffic_type)

        with patch(
            "asusrouter.modules.traffic.ARTrafficType.from_value",
            return_value=traffic_type,
        ) as mock_from_value:
            instance.type = "string"  # type: ignore[assignment]

            mock_from_value.assert_called_once_with("string")
            assert instance.type == traffic_type


class TestARTrafficSourceEthernet:
    """Class for testing ARTrafficSourceEthernet."""

    def test_init(self) -> None:
        """Test the initialization."""

        bh_flag = "true"

        instance = ARTrafficSourceEthernet(vtarget, bh_flag=bh_flag)

        assert isinstance(instance, ARTrafficSourceEthernet)
        assert issubclass(instance.__class__, ARTrafficSource)
        assert instance.target == vtarget
        assert instance.type == ARTrafficType.ETHERNET
        assert instance.bh_flag is True

    @pytest.mark.parametrize(
        ("bh_input", "bh_flag"),
        [
            (None, False),
            ("true", True),
            (False, False),
            (object(), False),
        ],
    )
    def test_properties(self, bh_input: Any, bh_flag: bool) -> None:
        """Test the properties."""

        instance = ARTrafficSourceEthernet(vtarget, bh_flag=bh_input)

        assert instance.bh_flag is bh_flag

    def test_setter_bh_flag(self) -> None:
        """Test the bh_flag setter."""

        set_value = "string"
        return_value = True

        instance = ARTrafficSourceEthernet(vtarget)

        with patch(
            "asusrouter.modules.traffic.safe_bool_nn",
            return_value=return_value,
        ) as mock_safe_bool:
            instance.bh_flag = set_value  # type: ignore[assignment]

            assert instance.bh_flag is return_value
            mock_safe_bool.assert_called_once_with(set_value)


class TestARTrafficSourceBetween:
    """Class for testing ARTrafficSourceBetween."""

    def test_init(self) -> None:
        """Test the initialization."""

        instance = ARTrafficSourceBetween(vtarget, towards=vtowards)

        assert isinstance(instance, ARTrafficSourceBetween)
        assert issubclass(instance.__class__, ARTrafficSource)
        assert instance.target == vtarget
        assert instance.type == ARTrafficType.UNKNOWN
        assert instance.towards == vtowards

    def test_properties(self) -> None:
        """Test the properties."""

        instance = ARTrafficSourceBetween(vtarget, towards=vtowards)

        assert instance.towards == vtowards

    def test_setter_towards(self) -> None:
        """Test the towards setter."""

        instance = ARTrafficSourceBetween(vtarget, towards=vtowards)

        instance.towards = vtarget
        assert instance.towards == vtarget

        # Test with an invalid new towards
        new_towards_wrong = "string"
        instance.towards = new_towards_wrong  # type: ignore[assignment]
        assert instance.towards is None


class TestARTrafficSourceWiFi:
    """Class for testing ARTrafficSourceWiFi."""

    def test_init(self) -> None:
        """Test the initialization."""

        instance = ARTrafficSourceWiFi(vtarget, towards=vtowards)

        assert isinstance(instance, ARTrafficSourceWiFi)
        assert issubclass(instance.__class__, ARTrafficSourceBetween)
        assert instance.target == vtarget
        assert instance.towards == vtowards
        assert instance.type == ARTrafficType.WIFI


class TestARTrafficSourceBackhaul:
    """Class for testing ARTrafficSourceBackhaul."""

    def test_init(self) -> None:
        """Test the initialization."""

        instance = ARTrafficSourceBackhaul(vtarget, towards=vtowards)

        assert isinstance(instance, ARTrafficSourceBackhaul)
        assert issubclass(instance.__class__, ARTrafficSourceBetween)
        assert instance.target == vtarget
        assert instance.towards == vtowards
        assert instance.type == ARTrafficType.BACKHAUL


class TestCheckState:
    """Class for testing _check_state method."""

    def test_not_traffic_source(self) -> None:
        """Test the _check_state method with a non-traffic source."""

        with pytest.raises(TypeError, match="Expected `ARTrafficSource`, got"):
            _check_state("value")

    def test_no_target(self) -> None:
        """Test cases when no target is provided."""

        source = ARTrafficSource(target=None)

        with pytest.raises(
            ValueError,
            match="Traffic source must have a `target` property set",
        ):
            _check_state(source)

    def test_no_type(self) -> None:
        """Test cases when no type is provided."""

        source = ARTrafficSource(target=vtarget)

        with pytest.raises(
            ValueError,
            match="Traffic source must have a `type` property set",
        ):
            _check_state(source)

    @pytest.mark.parametrize(
        "source",
        [
            ARTrafficSourceWiFi(target=vtarget, towards=None),
            ARTrafficSourceBackhaul(target=vtarget, towards=None),
        ],
    )
    def test_no_towards(self, source: ARTrafficSourceBetween) -> None:
        """Test cases when no towards is provided when required."""

        with pytest.raises(
            ValueError,
            match=f"Traffic source of type `{source.type}` requires "
            "a `towards` property set",
        ):
            _check_state(source)


class TestGetState:
    """Class for testing get_state method."""

    @pytest.mark.asyncio
    async def test_generic_case(self) -> None:
        """Test the generic case for get_state."""

        callback = AsyncMock()
        callback.return_value = True
        source = ARTrafficSourceWiFi(target=vtarget, towards=vtowards)
        request_type = "request"

        with (
            patch(
                "asusrouter.modules.traffic._check_state"
            ) as mock_check_state,
            patch(
                "asusrouter.modules.traffic.isinstance",
                return_value=False,
            ) as mock_isinstance,
            patch(
                "asusrouter.modules.traffic.get_request_type",
                return_value=request_type,
            ) as mock_get_request_type,
            patch(
                "asusrouter.modules.traffic.dict_to_request",
            ) as mock_dict_to_request,
        ):
            result = await get_state(callback, source)
            assert result is True

            mock_check_state.assert_called_once_with(source)
            mock_isinstance.assert_has_calls(
                [
                    # First call for ARTrafficSourceEthernet
                    call(source, ARTrafficSourceEthernet),
                    # Second call for ARTrafficSourceBackhaul
                    call(source, ARTrafficSourceBackhaul),
                    # Third call for ARTrafficSourceWiFi
                    call(source, ARTrafficSourceWiFi),
                ],
                any_order=False,
            )
            mock_get_request_type.assert_called_once_with(
                EndpointTools.TRAFFIC_WIFI
            )
            mock_dict_to_request.assert_called_once_with(
                {
                    "node_mac": str(vtarget),
                },
                request_type=request_type,
            )

    @pytest.mark.asyncio
    async def test_no_endpoint(self) -> None:
        """Test failure due to no endpoint found."""

        callback = AsyncMock()
        source = ARTrafficSource(target=vtarget, type=ARTrafficType.UNKNOWN)

        with patch(
            "asusrouter.modules.traffic._check_state"
        ) as mock_check_state:
            with pytest.raises(
                ValueError,
                match=f"Cannot find endpoint for traffic type `{source.type}`",
            ):
                await get_state(callback, source)

            mock_check_state.assert_called_once_with(source)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("source", "endpoint", "expected_args"),
        [
            (
                ARTrafficSourceEthernet(target=vtarget, bh_flag="true"),
                EndpointTools.TRAFFIC_ETHERNET,
                {
                    "node_mac": str(vtarget),
                    "is_bh": 1,
                },
            ),
            (
                ARTrafficSourceEthernet(target=vtarget, bh_flag=False),
                EndpointTools.TRAFFIC_ETHERNET,
                {
                    "node_mac": str(vtarget),
                    "is_bh": 0,
                },
            ),
            (
                ARTrafficSourceBackhaul(target=vtarget, towards=vtowards),
                EndpointTools.TRAFFIC_BACKHAUL,
                {
                    "node_mac": str(vtarget),
                    "sta_mac": str(vtowards),
                },
            ),
            (
                ARTrafficSourceWiFi(target=vtarget, towards=vtowards),
                EndpointTools.TRAFFIC_WIFI,
                {
                    "node_mac": str(vtarget),
                    "band_mac": str(vtowards),
                },
            ),
        ],
    )
    async def test_arguments(
        self,
        source: ARTrafficSource,
        endpoint: EndpointTools,
        expected_args: dict[str, Any],
    ) -> None:
        """Test the arguments passed to the request."""

        callback = AsyncMock()
        callback.return_value = True
        request_type = "request"

        def mock_dict_to_request(
            *args: Any, **kwargs: Any
        ) -> tuple[tuple[Any], dict[Any, Any]]:
            """Mock dict to request."""

            return args, kwargs

        with (
            patch(
                "asusrouter.modules.traffic._check_state"
            ) as mock_check_state,
            patch(
                "asusrouter.modules.traffic.get_request_type",
                return_value=request_type,
            ) as mock_get_request_type,
            patch(
                "asusrouter.modules.traffic.dict_to_request",
                side_effect=mock_dict_to_request,
            ) as mock_dict_to_request,
        ):
            result = await get_state(callback, source)
            assert result is True

            mock_check_state.assert_called_once_with(source)
            mock_get_request_type.assert_called_once_with(endpoint)

            mock_dict_to_request.assert_called_once_with(
                expected_args,
                request_type=request_type,
            )


@pytest.mark.parametrize(
    ("input__dict", "output_dict"),
    [
        # No input
        ({}, {}),
        # Real input
        (
            {
                "data_rx": 1,
                "data_tx": 2,
                "data_avg_rx": 3,
                "data_avg_tx": 4,
                "phy_rx": 5,
                "phy_tx": 6,
                "error_status": 200,
            },
            {
                "rx_speed": 1024.0,
                "tx_speed": 2048.0,
                "rx_speed_avg": 3072.0,
                "tx_speed_avg": 4096.0,
                "phy_rx": 5 * 2**20,
                "phy_tx": 6 * 2**20,
                "status": HTTPStatus.OK,
            },
        ),
        # Unknown value
        ({"unknown_key": "unknown_value"}, {"unknown_key": "unknown_value"}),
    ],
)
def test_translate_state(
    input__dict: dict[str, Any], output_dict: dict[str, Any]
) -> None:
    """Test the translate_state method."""

    result = translate_state(input__dict)

    assert result == output_dict


def test_traffic_module_registers_callables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure traffic module registers callables on import."""

    # Replace the registry method that is called at import time
    mock_register = Mock()
    monkeypatch.setattr(
        "asusrouter.registry.ARCallableRegistry.register", mock_register
    )

    # Reload the module so top-level registration runs again under the mock
    importlib.reload(traffic_module)

    # Expect three registrations (Ethernet, WiFi, Backhaul)
    assert mock_register.call_count == 3  # noqa: PLR2004

    expected_kwargs = {
        AR_CALL_GET_STATE: traffic_module.get_state,
        AR_CALL_TRANSLATE_STATE: traffic_module.translate_state,
    }

    # Check each call used the expected target class and kwargs (order matters)
    expected_targets = [
        traffic_module.ARTrafficSourceEthernet,
        traffic_module.ARTrafficSourceWiFi,
        traffic_module.ARTrafficSourceBackhaul,
    ]

    for idx, target in enumerate(expected_targets):
        args, kwargs = mock_register.call_args_list[idx]
        assert args[0] is target
        assert kwargs == expected_kwargs
