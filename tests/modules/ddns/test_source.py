"""Tests for the DDNS data source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.modules.ddns.enums import (
    ARDdnsField,
    ARDdnsServer,
    ARDdnsStatus,
)
from asusrouter.modules.ddns.source import (
    ARDdnsSourceUniversal,
    fetch_state,
    read_status,
    translate_state,
)
from asusrouter.modules.nvram import ARNvramType

_FULL_DATA = {
    "ddns_enable_x": "1",
    "ddns_server_x": "WWW.ASUS.COM",
    "ddns_hostname_x": "myhome.asuscomm.com",
    "ddns_hostname_old": "taken.asuscomm.com",
    "ddns_username_x": "user@example.com",
    "ddns_passwd_x": "secret",
    "ddns_ipaddr": "1.2.3.4",
    "ddns_ipv6_update": "1",
    "ddns_refresh_x": "21",
    "ddns_regular_check": "1",
    "ddns_regular_period": "60",
    "ddns_replace_status": "1",
    "ddns_return_code_chk": "register,230",
    "ddns_updated": "1",
    "ddns_wan_unit": "-1",
    "ddns_wildcard_x": "0",
    "asusddns_token_state": "0",
}


class TestGetState:
    """Tests for fetch_state."""

    async def test_fetches_via_nvram(self) -> None:
        """The DDNS items are requested from the NVRAM module."""

        values = {ARNvramType.DDNS_STATE: "1"}
        get_data = AsyncMock(return_value=values)
        callback = AsyncMock()

        result = await fetch_state(
            callback, ARDdnsSourceUniversal, fetch_data_callback=get_data
        )

        assert result == values
        callback.assert_not_awaited()
        requested = get_data.await_args.args[0]
        assert set(requested) == {
            ARNvramType.DDNS_HOSTNAME,
            ARNvramType.DDNS_HOSTNAME_OLD,
            ARNvramType.DDNS_IP_ADDRESS,
            ARNvramType.DDNS_IPV6_UPDATE,
            ARNvramType.DDNS_PASSWORD,
            ARNvramType.DDNS_REFRESH_INTERVAL,
            ARNvramType.DDNS_REGULAR_CHECK,
            ARNvramType.DDNS_REGULAR_PERIOD,
            ARNvramType.DDNS_REPLACE_STATUS,
            ARNvramType.DDNS_RETURN_CODE_CHK,
            ARNvramType.DDNS_SERVER,
            ARNvramType.DDNS_STATE,
            ARNvramType.DDNS_TOKEN_STATE,
            ARNvramType.DDNS_UPDATED,
            ARNvramType.DDNS_USERNAME,
            ARNvramType.DDNS_WAN_UNIT,
            ARNvramType.DDNS_WILDCARD,
        }

    async def test_no_get_data_callback(self) -> None:
        """Without a data callback nothing is fetched."""

        callback = AsyncMock()
        result = await fetch_state(callback, ARDdnsSourceUniversal)
        assert result == {}
        callback.assert_not_awaited()

    async def test_non_dict_response(self) -> None:
        """A non-dict response is normalized to an empty dict."""

        get_data = AsyncMock(return_value=None)
        result = await fetch_state(
            AsyncMock(), ARDdnsSourceUniversal, fetch_data_callback=get_data
        )
        assert result == {}


class TestReadStatus:
    """Tests for read_status."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, ARDdnsStatus.NONE),
            ("", ARDdnsStatus.NONE),
            ("Time-out", ARDdnsStatus.TIMEOUT),
            ("unknown_error", ARDdnsStatus.UNKNOWN_ERROR),
            ("connect_fail", ARDdnsStatus.CONNECT_FAILED),
            ("no_change", ARDdnsStatus.NO_CHANGE),
            ("ddns_query", ARDdnsStatus.QUERY),
            ("auth_fail", ARDdnsStatus.AUTH_FAILED),
            ("200", ARDdnsStatus.SUCCESS),
            ("register,200", ARDdnsStatus.SUCCESS),
            ("register,230", ARDdnsStatus.REGISTERED_NEW),
            ("unregister,-1", ARDdnsStatus.ERROR),
            ("203", ARDdnsStatus.DOMAIN_TAKEN),
            ("220", ARDdnsStatus.REGISTERED_ORIGINAL),
            ("233", ARDdnsStatus.NEW_DOMAIN_TAKEN),
            ("296", ARDdnsStatus.NOT_REGISTERED),
            ("297", ARDdnsStatus.INVALID_HOSTNAME),
            ("298", ARDdnsStatus.INVALID_DOMAIN),
            ("299", ARDdnsStatus.INVALID_IP),
            ("390", ARDdnsStatus.SERVER_ERROR),
            ("401", ARDdnsStatus.UNAUTHORIZED),
            ("402", ARDdnsStatus.FIRMWARE_UPDATE_REQUIRED),
            ("407", ARDdnsStatus.PROXY_AUTH_REQUIRED),
            ("something else", ARDdnsStatus.UNKNOWN),
            (42, ARDdnsStatus.NONE),
        ],
    )
    def test_read(self, raw: Any, expected: ARDdnsStatus) -> None:
        """Raw return codes map to statuses."""

        assert read_status(raw) is expected


class TestTranslateState:
    """Tests for translate_state."""

    @pytest.mark.parametrize("data", [None, {}, "text", []])
    def test_empty(self, data: Any) -> None:
        """Non-dict or empty data yields an empty result."""

        assert translate_state(data) == {}

    def test_full(self) -> None:
        """A full nvram set maps every field."""

        result = translate_state(_FULL_DATA)

        assert result[ARDdnsField.STATE] is True
        assert result[ARDdnsField.SERVER] is ARDdnsServer.ASUS
        assert str(result[ARDdnsField.HOSTNAME]) == "myhome.asuscomm.com"
        assert str(result[ARDdnsField.HOSTNAME_OLD]) == "taken.asuscomm.com"
        assert result[ARDdnsField.USERNAME] == "user@example.com"
        assert result[ARDdnsField.PASSWORD].value == "secret"
        assert str(result[ARDdnsField.IP_ADDRESS]) == "1.2.3.4"
        assert result[ARDdnsField.IPV6_UPDATE] is True
        assert result[ARDdnsField.REFRESH_INTERVAL] == 21
        assert result[ARDdnsField.VERIFICATION] is True
        assert result[ARDdnsField.VERIFICATION_PERIOD] == 60
        assert result[ARDdnsField.REPLACE_STATUS] is True
        assert result[ARDdnsField.STATUS] is ARDdnsStatus.REGISTERED_NEW
        assert result[ARDdnsField.TOKEN_STATE] is False
        assert result[ARDdnsField.UPDATED] is True
        assert result[ARDdnsField.WAN_UNIT] == -1
        assert result[ARDdnsField.WILDCARD] is False

    def test_missing_keys(self) -> None:
        """Missing keys yield None fields and a False state."""

        result = translate_state({"ddns_enable_x": "0"})

        assert result[ARDdnsField.STATE] is False
        assert result[ARDdnsField.SERVER] is None
        assert result[ARDdnsField.HOSTNAME] is None
        assert result[ARDdnsField.HOSTNAME_OLD] is None
        assert result[ARDdnsField.USERNAME] is None
        assert result[ARDdnsField.PASSWORD] is None
        assert result[ARDdnsField.IP_ADDRESS] is None
        assert result[ARDdnsField.IPV6_UPDATE] is None
        assert result[ARDdnsField.REFRESH_INTERVAL] is None
        assert result[ARDdnsField.VERIFICATION] is None
        assert result[ARDdnsField.VERIFICATION_PERIOD] is None
        assert result[ARDdnsField.REPLACE_STATUS] is None
        assert result[ARDdnsField.STATUS] is ARDdnsStatus.NONE
        assert result[ARDdnsField.TOKEN_STATE] is None
        assert result[ARDdnsField.UPDATED] is None
        assert result[ARDdnsField.WAN_UNIT] is None
        assert result[ARDdnsField.WILDCARD] is None

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("WWW.DYNDNS.ORG(CUSTOM)", ARDdnsServer.DYNDNS_CUSTOM),
            ("NOT.A.SERVER", ARDdnsServer.UNKNOWN),
        ],
    )
    def test_server(self, raw: str, expected: ARDdnsServer) -> None:
        """Server strings resolve to enum members."""

        result = translate_state({"ddns_server_x": raw})
        assert result[ARDdnsField.SERVER] is expected
