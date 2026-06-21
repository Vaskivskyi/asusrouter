"""Tests for AsusRouter properties."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from asusrouter.asusrouter import AsusRouter
from asusrouter.config import ARInstanceConfig
from asusrouter.config.connection import ARConnectionConfig
from asusrouter.const import DEFAULT_PORT_HTTP, DEFAULT_PORT_HTTPS
from asusrouter.modules.device import ARDeviceSourceUniversal
from asusrouter.modules.device.identity import ARDeviceIdentity
from tests.helpers import TCONST_HOST, TCONST_PASS, TCONST_USER


def test_description_no_state(router: AsusRouter) -> None:
    """Returns empty ARDeviceIdentity when _data_states has no device entry."""

    result = router.description
    assert isinstance(result, ARDeviceIdentity)


def test_description_state_content_not_identity(router: AsusRouter) -> None:
    """Returns empty ARDeviceIdentity when state content is not an identity."""

    state = Mock()
    state.content = {"not": "identity"}
    router._data_states[ARDeviceSourceUniversal] = state

    result = router.description
    assert isinstance(result, ARDeviceIdentity)


def test_description_state_content_is_identity(router: AsusRouter) -> None:
    """Returns state content when it is an ARDeviceIdentity."""

    identity = ARDeviceIdentity()
    state = Mock()
    state.content = identity
    router._data_states[ARDeviceSourceUniversal] = state

    assert router.description is identity


def test_support_delegates_to_description(router: AsusRouter) -> None:
    """Support property delegates to description.support."""

    identity = Mock(spec=ARDeviceIdentity)
    identity.support = {Mock(): True}
    state = Mock()
    state.content = identity
    router._data_states[ARDeviceSourceUniversal] = state

    assert router.support is identity.support


@pytest.mark.parametrize("connected", [True, False])
def test_connected(router: AsusRouter, connected: bool) -> None:
    """Connected property delegates to _connection.connected."""

    router._connection = Mock()
    router._connection.connected = connected
    assert router.connected is connected


def test_config_returns_instance_config(router: AsusRouter) -> None:
    """Config property returns the ARInstanceConfig instance."""

    assert isinstance(router.config, ARInstanceConfig)
    assert router.config is router._config


def test_connection_config(router: AsusRouter) -> None:
    """Connection_config returns the ARConnectionConfig from _connection."""

    assert isinstance(router.connection_config, ARConnectionConfig)
    assert router.connection_config is router._connection.config


@pytest.mark.parametrize(
    ("port", "use_ssl", "expected_scheme", "expected_port"),
    [
        (None, False, "http", DEFAULT_PORT_HTTP),
        (None, True, "https", DEFAULT_PORT_HTTPS),
        (8080, False, "http", 8080),
        (8553, True, "https", 8553),
    ],
)
def test_webpanel(
    port: int | None,
    use_ssl: bool,
    expected_scheme: str,
    expected_port: int,
) -> None:
    """Webpanel property returns the correct URL for each port/SSL combo."""

    router = AsusRouter(
        hostname=TCONST_HOST,
        username=TCONST_USER,
        password=TCONST_PASS,
        port=port,
        use_ssl=use_ssl,
    )
    assert (
        router.webpanel == f"{expected_scheme}://{TCONST_HOST}:{expected_port}"
    )
