"""Supported FTP."""

from __future__ import annotations

from typing import Any

from asusrouter.modules.ftp import ARFTPCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_bool_translator
from asusrouter.tools.readers import is_true_in_dict

translate_ftp = make_bool_translator(ARSupportValue.FTP.value, negate=True)


def translate_ftp_capabilities(data: dict[str, Any]) -> list[ARFTPCapability]:
    """Translate FTP capabilities support data."""

    if not isinstance(data, dict):
        return []  # type: ignore[unreachable]

    result: list[ARFTPCapability] = []

    if is_true_in_dict(ARSupportValue.FTP_SSL.value, data):
        result.append(ARFTPCapability.SSL)

    return result
