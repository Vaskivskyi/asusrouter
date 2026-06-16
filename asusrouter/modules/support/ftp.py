"""Supported FTP."""

from __future__ import annotations

from asusrouter.modules.ftp import ARFTPCapability
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_list_translator,
)

translate_ftp = make_bool_translator(ARSupportValue.FTP.value, negate=True)
translate_ftp_capabilities = make_list_translator(
    {
        ARSupportValue.FTP_SSL.value: ARFTPCapability.SSL,
    }
)
