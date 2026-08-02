"""Log data source for AsusRouter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from asusrouter.config import ARConfig, ARConfigKey as ARConfKey
from asusrouter.modules.clock import ARClockSourceUniversal
from asusrouter.modules.endpoint import AREndpoint
from asusrouter.modules.endpoint.hooks import ARHook, ARHookCall, hook_request
from asusrouter.modules.log.clock import resolve_datetimes
from asusrouter.modules.log.enums import ARLogField
from asusrouter.modules.log.parser import anchor_of, parse_text, strip_envelope
from asusrouter.modules.log.query import filter_log
from asusrouter.modules.source import ARDataSource
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters.raw import raw_to_str
from asusrouter.tools.identifiers import Serial
from asusrouter.tools.security import ARSecurityLevel
from asusrouter.tools.security.text import SensitiveText, remove_secrets
from asusrouter.tools.types import ARCallbackType

if TYPE_CHECKING:
    from asusrouter.modules.device.identity import ARDeviceIdentity
    from asusrouter.modules.log.entry import ARLogEntry

# A device clock further than this from the host's has not synced
_CLOCK_DRIFT_LIMIT = timedelta(days=1)

_LOG_HOOK: ARHookCall = (
    ARHook.NVRAM_DUMP,
    '"syslog.log","syslog.sh"',
)


class ARLogSource(ARDataSource):
    """AsusRouter system log data source."""


# Universal instance - preferred
ARLogSourceUniversal: ARLogSource = ARLogSource()


async def _async_ensure_clock(
    identity: ARDeviceIdentity | None,
    fetch_data_callback: ARCallbackType | None,
) -> None:
    """Read the device's clock unless the identity holds a usable one."""

    if fetch_data_callback is None or identity is None:
        return

    device_time = identity.device_time
    if (
        device_time is not None
        # One stating no offset cannot be measured against the host's
        and device_time.tzinfo is not None
        and abs(datetime.now(UTC) - device_time) <= _CLOCK_DRIFT_LIMIT
    ):
        return

    await fetch_data_callback(ARClockSourceUniversal)


async def fetch_state(
    callback: ARCallbackType,
    source: ARLogSource,
    *,
    fetch_raw_callback: ARCallbackType | None = None,
    fetch_data_callback: ARCallbackType | None = None,
    identity: ARDeviceIdentity | None = None,
    **kwargs: Any,
) -> str:
    """Fetch the raw system log."""

    # Before the log, so the stamps have a clock to be resolved against
    await _async_ensure_clock(identity, fetch_data_callback)

    if fetch_raw_callback is None:
        return ""

    content = raw_to_str(
        await fetch_raw_callback(
            endpoint=AREndpoint.FETCH_DATA,
            request=hook_request(_LOG_HOOK),
        )
    )

    return content or ""


def _history(previous: Any) -> tuple[list[ARLogEntry], str | None]:
    """Read the entries and the anchor an earlier read left behind."""

    if not isinstance(previous, dict):
        return [], None

    kept = previous.get(ARLogField.ENTRY_LIST)
    anchor = previous.get(ARLogField.ANCHOR)

    return (
        kept if isinstance(kept, list) else [],
        anchor.value if isinstance(anchor, SensitiveText) else None,
    )


def _clock_anchor(identity: ARDeviceIdentity | None) -> datetime | None:
    """Read the device's own clock - the year and offset a stamp lacks."""

    return identity.device_time if identity is not None else None


def _unchanged(
    kept: list[ARLogEntry], anchor: str | None
) -> dict[ARLogField, Any]:
    """Rebuild the previous result when a reply carried no log text."""

    state = filter_log(kept)
    state[ARLogField.ANCHOR] = SensitiveText(anchor or "")

    return state


def _without_secrets(
    text: str, identity: ARDeviceIdentity | None, level: ARSecurityLevel
) -> str:
    """Clean the values only we know out of the device's own text."""

    if identity is None:
        return text

    secrets = [
        secret
        for secret in (
            identity.mac,
            identity.username,
            Serial.from_value_safe(identity.serial),
        )
        if secret is not None
    ]

    return remove_secrets(text, secrets, level) if secrets else text


def translate_state(
    data: Any,
    *,
    identity: ARDeviceIdentity | None = None,
    previous: Any = None,
    **kwargs: Any,
) -> dict[ARLogField, Any]:
    """Parse the raw log into the lean dict, continuing an earlier read."""

    kept, anchor = _history(previous)
    config = kwargs.get("config", ARConfig)
    # Before parsing, so the anchor kept for the next read and the text
    # that read searches are cleaned the same way
    text = (
        _without_secrets(
            strip_envelope(data),
            identity,
            config.get(ARConfKey.SECURITY_LEVEL_DATA),
        )
        if isinstance(data, str)
        else ""
    )
    # A reply with no text says nothing about the log, so the previous
    # result stands rather than being overwritten by an empty one
    if not text:
        return _unchanged(kept, anchor)

    # Reading only what is new keeps a poll off the whole buffer, and
    # an anchor that no longer matches simply reads all of it again
    entries = resolve_datetimes(
        parse_text(text, after=anchor), _clock_anchor(identity)
    )
    if kept:
        entries = kept + entries

    limit = config.get(ARConfKey.LOG_HISTORY_LIMIT)
    if limit > 0 and len(entries) > limit:
        entries = entries[-limit:]

    state = filter_log(entries)
    # Device text like any other: bookkeeping the next read reaches
    # through `.value`, not something to hand out
    state[ARLogField.ANCHOR] = SensitiveText(anchor_of(text))

    return state


ARCallReg.register_source(
    ARLogSource,
    fetch_state=fetch_state,
    translate_state=translate_state,
)


__all__ = [
    "ARLogSource",
    "ARLogSourceUniversal",
    "fetch_state",
    "translate_state",
]
