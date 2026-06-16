"""Supported connections."""

from __future__ import annotations

from asusrouter.modules.connection_v2 import ARConnection
from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import make_list_translator

translate_connection = make_list_translator(
    {
        ARSupportValue.CONNECTION_HTTPS.value: ARConnection.HTTPS,
        ARSupportValue.CONNECTION_SSH.value: ARConnection.SSH,
    }
)
