"""Firmware data source for AsusRouter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.firmware.enums import (
    ARFirmwareWebError,
    ARFirmwareWebFetch,
    ARFirmwareWebNotify,
    ARFirmwareWebUpgrade,
)
from asusrouter.modules.firmware.note import read_firmware_note
from asusrouter.modules.firmware.version import ARFirmware
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_int, raw_to_str
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity

__all__ = [
    "ARFirmwareSignature",
    "ARFirmwareSource",
    "ARFirmwareSourceUniversal",
    "ARFirmwareState",
    "ARFirmwareSync",
    "ARFirmwareWeb",
    "fetch_state",
    "translate_state",
]


@dataclass
class ARFirmwareSignature:
    """DPI (bwdpi) signature update state (`sig_*`)."""

    version: str | None = None
    update: int | None = None
    upgrade: int | None = None
    error: int | None = None
    flag: int | None = None


@dataclass
class ARFirmwareSync:
    """AiMesh config-sync firmware state (`cfg_*`)."""

    check: int | None = None
    upgrade: int | None = None


@dataclass
class ARFirmwareWeb:
    """Firmware web-update state (`webs_state_*`)."""

    fetch: ARFirmwareWebFetch = ARFirmwareWebFetch.UNKNOWN
    upgrade: ARFirmwareWebUpgrade = ARFirmwareWebUpgrade.UNKNOWN
    error: ARFirmwareWebError = ARFirmwareWebError.UNKNOWN
    notify: ARFirmwareWebNotify = ARFirmwareWebNotify.UNKNOWN
    level: int | None = None
    available: ARFirmware | None = None
    available_beta: ARFirmware | None = None
    required: ARFirmware | None = None
    state: bool = False
    state_beta: bool = False
    release_note: str | None = None


@dataclass
class ARFirmwareState:
    """The firmware state of the router."""

    current: ARFirmware | None = None
    web: ARFirmwareWeb = field(default_factory=ARFirmwareWeb)
    signature: ARFirmwareSignature = field(default_factory=ARFirmwareSignature)
    sync: ARFirmwareSync = field(default_factory=ARFirmwareSync)


class ARFirmwareSource(ARDataSource):
    """Firmware data source for the connected router."""


# Universal instance - preferred
ARFirmwareSourceUniversal: ARFirmwareSource = ARFirmwareSource()


# Release-note endpoints, tried in order until one returns a note
_NOTE_ENDPOINTS: tuple[AREndpoint, ...] = (
    AREndpoint.FETCH_FIRMWARE_UPDATE_NOTE,
    AREndpoint.FETCH_FIRMWARE_UPDATE_NOTE_AIMESH,
)


def _available(raw: Any) -> ARFirmware | None:
    """Parse an available-firmware string, or None when unparsable."""

    firmware = ARFirmware.from_string(raw)
    return firmware if firmware.major is not None else None


def _is_stable_update(
    current: ARFirmware | None, available: ARFirmware | None
) -> bool:
    """Check whether a newer stable firmware is available."""

    if available is None:
        return False
    if current is not None and current.major is not None:
        return current < available
    return True


async def _fetch_note(fetch_raw_callback: ARCallbackType) -> str | None:
    """Fetch the release note from the first endpoint that returns one."""

    for endpoint in _NOTE_ENDPOINTS:
        content = raw_to_str(await fetch_raw_callback(endpoint))
        if not content:
            continue
        note = read_firmware_note(content)
        if note:
            return note
    return None


async def fetch_state(
    callback: ARCallbackType,
    source: ARFirmwareSource,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch the firmware state and release note when available."""

    update = await callback(endpoint=AREndpoint.FETCH_FIRMWARE_UPDATE)
    if not isinstance(update, dict):
        update = {}

    note: str | None = None
    fetch_raw_callback = kwargs.get("fetch_raw_callback")
    current = identity.firmware
    available = _available(update.get("webs_state_info"))
    if fetch_raw_callback is not None and _is_stable_update(
        current, available
    ):
        note = await _fetch_note(fetch_raw_callback)

    return {"update": update, "note": note, "available": available}


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity,
    **kwargs: Any,
) -> ARFirmwareState:
    """Translate the fetched firmware state into an `ARFirmwareState`."""

    if not isinstance(data, dict):
        return ARFirmwareState()

    update: dict[str, Any] = data.get("update") or {}
    current = identity.firmware

    # Reuse the available firmware parsed by `fetch_state` when present
    available = data.get("available")
    if available is None:
        available = _available(update.get("webs_state_info"))
    available_beta = _available(update.get("webs_state_info_beta"))
    state = _is_stable_update(current, available)

    web = ARFirmwareWeb(
        fetch=ARFirmwareWebFetch.from_value(update.get("webs_state_update")),
        upgrade=ARFirmwareWebUpgrade.from_value(
            update.get("webs_state_upgrade")
        ),
        error=ARFirmwareWebError.from_value(update.get("webs_state_error")),
        notify=ARFirmwareWebNotify.from_value(update.get("webs_state_flag")),
        level=raw_to_int(update.get("webs_state_level")),
        available=available if state else None,
        available_beta=available_beta,
        required=_available(update.get("webs_state_REQinfo")),
        state=state,
        state_beta=available_beta is not None,
        release_note=data.get("note"),
    )

    signature = ARFirmwareSignature(
        version=raw_to_str(update.get("sig_ver")),
        update=raw_to_int(update.get("sig_state_update")),
        upgrade=raw_to_int(update.get("sig_state_upgrade")),
        error=raw_to_int(update.get("sig_state_error")),
        flag=raw_to_int(update.get("sig_state_flag")),
    )

    sync = ARFirmwareSync(
        check=raw_to_int(update.get("cfg_check")),
        upgrade=raw_to_int(update.get("cfg_upgrade")),
    )

    return ARFirmwareState(
        current=current, web=web, signature=signature, sync=sync
    )


ARCallReg.register_source(
    ARFirmwareSource, fetch_state=fetch_state, translate_state=translate_state
)
