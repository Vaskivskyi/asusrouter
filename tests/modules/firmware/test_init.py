"""Tests for the firmware module."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from asusrouter.const import AR_CALL_GET_STATE, AR_CALL_TRANSLATE_STATE
from asusrouter.modules.firmware import (
    ARFirmware,
    ARFirmwareSignature,
    ARFirmwareSource,
    ARFirmwareSourceUniversal,
    ARFirmwareState,
    ARFirmwareSync,
    ARFirmwareWeb,
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
    _available,
    _fetch_note,
    _is_stable_update,
    get_state,
    translate_state,
)
from asusrouter.registry import ARCallableRegistry as ARCallReg

# Firmware version strings reused across cases
_OLDER = "3004_388_2_0"
_NEWER = "3004_388_4_0"

# A fully populated firmware detection payload
_FULL_UPDATE: dict[str, Any] = {
    "webs_state_update": "1",
    "webs_state_upgrade": "",
    "webs_state_error": "0",
    "webs_state_info": _NEWER,
    "webs_state_info_beta": "",
    "webs_state_REQinfo": "",
    "webs_state_flag": "1",
    "webs_state_level": "0",
    "sig_ver": "2.380",
    "sig_state_update": "0",
    "sig_state_upgrade": "1",
    "sig_state_error": "0",
    "sig_state_flag": "1",
    "cfg_check": "",
    "cfg_upgrade": "",
}


def _identity(fw: str | None = None) -> Any:
    """Fake device identity exposing a firmware version."""

    return SimpleNamespace(firmware=ARFirmware.from_string(fw))


class TestWebEnums:
    """Tests for the web-state enums."""

    @pytest.mark.parametrize(
        ("enum", "raw", "expected"),
        [
            (ARFirmwareWebError, "0", ARFirmwareWebError.NONE),
            (ARFirmwareWebError, "3", ARFirmwareWebError.FW_ERROR),
            (ARFirmwareWebError, "42", ARFirmwareWebError.UNKNOWN),
            (ARFirmwareWebFetch, "0", ARFirmwareWebFetch.ACTIVE),
            (ARFirmwareWebFetch, "1", ARFirmwareWebFetch.INACTIVE),
            (ARFirmwareWebNotify, "2", ARFirmwareWebNotify.FORCE),
            (ARFirmwareWebNotify, "", ARFirmwareWebNotify.UNKNOWN),
            (ARFirmwareWebUpgrade, "-1", ARFirmwareWebUpgrade.INACTIVE),
            (ARFirmwareWebUpgrade, "2", ARFirmwareWebUpgrade.ACTIVE),
        ],
    )
    def test_from_value(self, enum: Any, raw: str, expected: Any) -> None:
        """`from_value` maps known codes and falls back to UNKNOWN."""

        assert enum.from_value(raw) == expected


class TestDataclassDefaults:
    """Tests for the firmware dataclass defaults."""

    def test_web_defaults(self) -> None:
        """A bare web state is all-unknown / empty."""

        web = ARFirmwareWeb()
        assert web.fetch is ARFirmwareWebFetch.UNKNOWN
        assert web.upgrade is ARFirmwareWebUpgrade.UNKNOWN
        assert web.error is ARFirmwareWebError.UNKNOWN
        assert web.notify is ARFirmwareWebNotify.UNKNOWN
        assert web.available is None
        assert web.state is False
        assert web.release_note is None

    def test_state_defaults(self) -> None:
        """A bare firmware state carries empty sub-structures."""

        state = ARFirmwareState()
        assert state.current is None
        assert isinstance(state.web, ARFirmwareWeb)
        assert isinstance(state.signature, ARFirmwareSignature)
        assert isinstance(state.sync, ARFirmwareSync)


class TestARFirmwareSource:
    """Tests for ARFirmwareSource."""

    def test_equality_and_hash(self) -> None:
        """All firmware sources are equal and share a hash."""

        assert ARFirmwareSource() == ARFirmwareSource()
        assert hash(ARFirmwareSource()) == hash(ARFirmwareSourceUniversal)

    def test_equality_other_type(self) -> None:
        """Comparison with a non-source returns NotImplemented / False."""

        assert ARFirmwareSource().__eq__("x") is NotImplemented
        assert (ARFirmwareSource() == "x") is False

    def test_repr(self) -> None:
        """The repr is stable."""

        assert repr(ARFirmwareSource()) == "<ARFirmwareSource>"


class TestAvailable:
    """Tests for _available."""

    def test_valid(self) -> None:
        """A parsable version string yields an ARFirmware."""

        firmware = _available(_NEWER)
        assert firmware is not None
        assert firmware.major == (3, 0, 0, 4)

    @pytest.mark.parametrize("raw", [None, "", "garbage"])
    def test_none(self, raw: Any) -> None:
        """Empty or unparsable input yields None."""

        assert _available(raw) is None


class TestIsStableUpdate:
    """Tests for _is_stable_update."""

    @pytest.mark.parametrize(
        ("current", "available", "expected"),
        [
            (None, None, False),
            (ARFirmware.from_string(_NEWER), None, False),
            (None, ARFirmware.from_string(_NEWER), True),
            (ARFirmware(), ARFirmware.from_string(_NEWER), True),
            (
                ARFirmware.from_string(_OLDER),
                ARFirmware.from_string(_NEWER),
                True,
            ),
            (
                ARFirmware.from_string(_NEWER),
                ARFirmware.from_string(_OLDER),
                False,
            ),
        ],
    )
    def test_is_stable_update(
        self,
        current: ARFirmware | None,
        available: ARFirmware | None,
        expected: bool,
    ) -> None:
        """Only a strictly newer available firmware is a stable update."""

        assert _is_stable_update(current, available) == expected


class TestFetchNote:
    """Tests for _fetch_note."""

    @pytest.mark.asyncio
    async def test_first_endpoint(self) -> None:
        """The first endpoint returning a note wins."""

        callback = AsyncMock(return_value="Release Note\n- Fix A\n")
        assert await _fetch_note(callback) == "- Fix A"
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_to_second(self) -> None:
        """An empty first endpoint falls through to the second."""

        callback = AsyncMock(side_effect=["", "Release Note\n- Fix B\n"])
        assert await _fetch_note(callback) == "- Fix B"
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_none_when_all_empty(self) -> None:
        """No content anywhere yields None."""

        callback = AsyncMock(return_value="")
        assert await _fetch_note(callback) is None
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_none_when_only_headers(self) -> None:
        """A header-only note is treated as empty."""

        callback = AsyncMock(return_value="Firmware version 1\nRelease Note\n")
        assert await _fetch_note(callback) is None
        assert callback.await_count == 2


class TestGetState:
    """Tests for get_state."""

    @pytest.mark.asyncio
    async def test_stable_update_fetches_note(self) -> None:
        """A newer available firmware triggers the release-note fetch."""

        callback = AsyncMock(return_value={"webs_state_info": _NEWER})
        raw_callback = AsyncMock(return_value="Release Note\n- Fix\n")
        result = await get_state(
            callback,
            ARFirmwareSourceUniversal,
            identity=_identity(_OLDER),
            raw_callback=raw_callback,
        )
        assert result["update"] == {"webs_state_info": _NEWER}
        assert result["note"] == "- Fix"
        assert result["available"] is not None
        raw_callback.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_stable_update_skips_note(self) -> None:
        """An older available firmware skips the note fetch."""

        callback = AsyncMock(return_value={"webs_state_info": _OLDER})
        raw_callback = AsyncMock()
        result = await get_state(
            callback,
            ARFirmwareSourceUniversal,
            identity=_identity(_NEWER),
            raw_callback=raw_callback,
        )
        assert result["note"] is None
        raw_callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_raw_callback(self) -> None:
        """Without a raw callback the note is never fetched."""

        callback = AsyncMock(return_value={"webs_state_info": _NEWER})
        result = await get_state(
            callback,
            ARFirmwareSourceUniversal,
            identity=_identity(_OLDER),
        )
        assert result["note"] is None

    @pytest.mark.asyncio
    async def test_non_dict_update(self) -> None:
        """A non-dict response degrades to an empty update."""

        callback = AsyncMock(return_value=None)
        result = await get_state(
            callback,
            ARFirmwareSourceUniversal,
            identity=_identity(),
            raw_callback=AsyncMock(),
        )
        assert result == {"update": {}, "note": None, "available": None}


class TestTranslateState:
    """Tests for translate_state."""

    def test_non_dict(self) -> None:
        """A non-dict payload yields a default state."""

        assert translate_state(None, identity=_identity()) == ARFirmwareState()

    def test_full(self) -> None:
        """A full payload maps every sub-structure."""

        data = {"update": _FULL_UPDATE, "note": "- Fix"}
        state = translate_state(data, identity=_identity(_OLDER))

        assert state.current is not None
        assert state.web.fetch is ARFirmwareWebFetch.INACTIVE
        assert state.web.upgrade is ARFirmwareWebUpgrade.UNKNOWN
        assert state.web.error is ARFirmwareWebError.NONE
        assert state.web.notify is ARFirmwareWebNotify.AVAILABLE
        assert state.web.level == 0
        assert state.web.available is not None
        assert state.web.required is None
        assert state.web.state is True
        assert state.web.state_beta is False
        assert state.web.release_note == "- Fix"

        assert state.signature.version == "2.380"
        assert state.signature.update == 0
        assert state.signature.upgrade == 1
        assert state.signature.error == 0
        assert state.signature.flag == 1

        assert state.sync.check is None
        assert state.sync.upgrade is None

    def test_available_gated_out_when_not_newer(self) -> None:
        """An older available firmware is dropped and state is False."""

        data = {"update": {"webs_state_info": _OLDER}}
        state = translate_state(data, identity=_identity(_NEWER))
        assert state.web.available is None
        assert state.web.state is False

    def test_beta_presence(self) -> None:
        """A reported beta is available by presence."""

        data = {"update": {"webs_state_info_beta": "3004_388_5_0"}}
        state = translate_state(data, identity=_identity())
        assert state.web.available_beta is not None
        assert state.web.state_beta is True

    def test_empty_update(self) -> None:
        """A missing update section yields all-unknown defaults."""

        state = translate_state({}, identity=_identity())
        assert state.web.fetch is ARFirmwareWebFetch.UNKNOWN
        assert state.web.available is None
        assert state.signature.version is None


def test_module_registers_source() -> None:
    """The firmware source resolves to the module callables."""

    assert (
        ARCallReg.get_callable(ARFirmwareSourceUniversal, AR_CALL_GET_STATE)
        is get_state
    )
    assert (
        ARCallReg.get_callable(
            ARFirmwareSourceUniversal, AR_CALL_TRANSLATE_STATE
        )
        is translate_state
    )
    assert (
        ARCallReg.get_callable_flag(
            ARFirmwareSourceUniversal, AR_CALL_GET_STATE
        )
        is False
    )
