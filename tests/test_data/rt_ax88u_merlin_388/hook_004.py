"""Result of processing hook_004.content."""

from asusrouter import AsusData
from asusrouter.modules.port_forwarding import AsusPortForwarding

expected_result = {AsusData.PORT_FORWARDING: {"state": AsusPortForwarding.OFF}}
