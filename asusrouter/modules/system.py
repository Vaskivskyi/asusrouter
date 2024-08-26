"""System module for AsusRouter."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Awaitable, Callable

_LOGGER = logging.getLogger(__name__)


class AsusSystem(str, Enum):
    """Asus system enum.

    This enum contains all known system services. The availability of these
    services depends on the router model and firmware version.

    Some services might not be tested and might not work as expected. Use with
    caution and at your own risk."""

    # ---------------------
    # DISCLAIMER: Migration to the new format
    #
    # AsusSystem enum is being migrated to a new format. Instead of
    # `{ACTION}_{FEATURE}`, the format should be `{FEATURE}_{ACTION}`. This
    # will allow better grouping of related actions and easier access.
    #
    # E.g. `REBUILD_AIMESH` -> `AIMESH_REBUILD`
    #
    # The old format will be deprecated and removed in a future version.
    # Please, only add new actions in the new format.
    #
    # All the old actions will be migrated to the new format with time
    # (and updates in the corresponding modules). Any deprecated actions
    # with a new format should be added to the `AsusSystemDeprecated` dict.
    #
    # Check the AiMesh for an example of the new format.
    # ---------------------

    # ---------------------
    # AiMesh
    AIMESH_REBOOT = "device_reboot"  # Restart router + all nodes
    AIMESH_REBUILD = "re_reconnect"  # Rebuild AiMesh
    REBUILD_AIMESH = "_depr_re_reconnect"  # Rebuild AiMesh / legacy name
    # ---------------------
    # Aura
    AURA_RESTART = "restart_ledg"  # Restart Aura RGB
    # ---------------------
    # Firmware
    FIRMWARE_CHECK = "firmware_check"  # Check for firmware update
    # Firmware upgrade will upgrade the firmware to the latest version
    # if available. The firmware file is downloaded from the Asus server.
    # After the download, the router will reboot and install the firmware.
    FIRMWARE_UPGRADE = "firmware_upgrade"  # Firmware upgrade
    # ---------------------
    # Upgrades and updates
    UPGRADE_RESTART = "restart_upgrade"  # Upgrade firmware and restart device
    UPGRADE_START = "start_upgrade"  # Start firmware upgrade / installation
    UPGRADE_STOP = "stop_upgrade"  # Stop firmware upgrade / installation
    RESTART_UPGRADE = "_depr_restart_upgrade"
    START_UPGRADE = "_depr_start_upgrade"
    STOP_UPGRADE = "_depr_stop_upgrade"
    # ---------------------
    PREPARE_CERT = "prepare_cert"  # Prepare certificate
    REBOOT = "reboot"  # Reboot the router
    RESTART_CHPASS = "restart_chpass"
    RESTART_CLOUDSYNC = "restart_cloudsync"  # AiCloud 2.0 sync
    RESTART_CP = "restart_CP"  # Captive Portal
    RESTART_DDNS_LE = "restart_ddns_le"
    RESTART_DEFAULT_WAN = "restart_default_wan"  # Default WAN
    RESTART_DISKMON = "restart_diskmon"  # Disk monitor
    RESTART_DNSFILTER = "restart_dnsfilter"  # DNS filter
    RESTART_DNSMASQ = "restart_dnsmasq"  # DNS
    RESTART_DNSQD = "restart_dnsqd"  #
    RESTART_FIREWALL = "restart_firewall"  # Firewall
    RESTART_FTPD = "restart_ftpd"  # FTP server
    RESTART_FTPSAMBA = "restart_ftpsamba"
    RESTART_HTTPD = "restart_httpd"  # Web server
    RESTART_KEY_GUARD = "restart_key_guard"
    RESTART_LEDS = "restart_leds"
    RESTART_LPD = "restart_lpd"  # Line Printer Daemon (LPD)
    RESTART_NASAPPS = "restart_nasapps"
    RESTART_NET = "restart_net"  # Restart all wired interfaces
    RESTART_NET_AND_PHY = (
        "restart_net_and_phy"  # Restart all network interfaces
    )
    RESTART_NFCM = "restart_nfcm"
    RESTART_OAM = "restart_oam"
    RESTART_OPENVPND = "restart_openvpnd"  # OpenVPN daemon
    RESTART_QOS = "restart_qos"  # Quality of Service (QoS)
    RESTART_ROUTERBOOST = "restart_routerboost"
    RESTART_SAMBA = "restart_samba"  # Samba file sharing
    RESTART_SETTINGS_WEBDAV = "restart_settings_webdav"  # WebDAV
    RESTART_SNMPD = (
        "restart_snmpd"  # Simple Network Management Protocol (SNMP)
    )
    RESTART_SUBNET = "restart_subnet"
    RESTART_TIME = "restart_time"
    RESTART_TIMEMACHINE = "restart_timemachine"
    RESTART_TOR = "restart_tor"  # The Onion Router (TOR)
    RESTART_TR = "restart_tr"
    RESTART_U2EC = "restart_u2ec"  # USB to Ethernet Connector
    RESTART_UPNP = "restart_upnp"  # Universal Plug and Play (UPnP)
    RESTART_USB_IDLE = "restart_usb_idle"
    RESTART_VPNC = "restart_vpnc"
    RESTART_VPND = "restart_vpnd"  # VPN daemon for legacy VPNs
    RESTART_WAN = (
        "restart_wan"  # Restart WAN connection (optional if number, e.g. 0)
    )
    RESTART_WAN_DNS = "restart_wan_dns"  # Restart WAN DNS (optional if number)
    RESTART_WAN_IF = (
        "restart_wan_if"  # Restart WAN interfaces (optional if number)
    )
    RESTART_WEBDAV = "restart_webdav"  # WebDAV
    RESTART_WIRELESS = "restart_wireless"  # Restart all wireless interfaces
    RESTART_WLCSCAN = "restart_wlcscan"
    RESTART_WGS = "restart_wgs"  # Restart all wireguard server interfaces
    RESTART_WPSIE = "restart_wpsie"
    RESTART_WRS = "restart_wrs"
    RESTART_WTFAST_RULE = "restart_wtfast_rule"
    RESET_LED = "reset_led"
    START_AURARGB = "start_aurargb"  # Aura RGB
    START_DISKFORMAT = "start_diskformat"  # Format disk
    START_DISKSCAN = "start_diskscan"  # Scan disk
    START_WEBS_UPGRADE = (
        "start_webs_upgrade"  # Start firmware upgrade from the web
    )
    START_WEBS_UPDATE = "start_webs_update"  # Check for firmware update
    START_WRS = "start_wrs"
    STOP_AURARGB = "stop_aurargb"  # Aura RGB
    STOP_LOGGER = "stop_logger"
    STOP_OPENVPND = "stop_openvpnd"  # Stop OpenVPN server
    STOP_VPNC = "stop_vpnc"
    STOP_VPND = "stop_vpnd"  # Stop VPN server for legacy VPNs
    STOP_WRS_FORCE = "stop_wrs_force"
    UPDATE_CLIENTS = "update_clients"


# Deprecated states for AsusSystem
# Format: {DeprecatedState: (NewState, Version)}
# Version is the version when the deprecated state will be removed (optional)
AsusSystemDeprecated = {
    # AiMesh
    AsusSystem.REBUILD_AIMESH: (AsusSystem.AIMESH_REBUILD, None),
    # Upgrades and updates
    AsusSystem.RESTART_UPGRADE: (AsusSystem.UPGRADE_RESTART, None),
    AsusSystem.START_UPGRADE: (AsusSystem.UPGRADE_START, None),
    AsusSystem.STOP_UPGRADE: (AsusSystem.UPGRADE_STOP, None),
}


# Map AsusSystem special cases to service calls
STATE_MAP: dict[AsusSystem, dict[str, Any]] = {
    AsusSystem.AIMESH_REBOOT: {
        "service": None,
        "arguments": {"action_mode": "device_reboot"},
        "apply": False,
        "expect_modify": False,
    },
    AsusSystem.FIRMWARE_CHECK: {
        "service": None,
        "arguments": {"action_mode": "firmware_check"},
        "apply": False,
        "expect_modify": False,
    },
    AsusSystem.FIRMWARE_UPGRADE: {
        "service": None,
        "arguments": {"action_mode": "firmware_upgrade"},
        "apply": False,
        "expect_modify": False,
    },
    AsusSystem.UPDATE_CLIENTS: {
        "service": None,
        "arguments": {"action_mode": "update_client_list"},
        "apply": False,
        "expect_modify": False,
    },
}


async def set_state(
    callback: Callable[..., Awaitable[bool]],
    state: AsusSystem,
    **kwargs: Any,
) -> bool:
    """Set the system state."""

    # Check and notify if the state is deprecated
    if state in AsusSystemDeprecated:
        repl_state, repl_ver = AsusSystemDeprecated[state]
        message = f"Deprecated state `{state.name}` from `AsusSystem` \
enum used. Use `{repl_state.name}` instead"
        if repl_ver:
            message += f". This state will be removed in version {repl_ver}"
        _LOGGER.warning(
            message,
        )
        state = repl_state

    # Get the arguments for the callback function based on the state
    callback_args = STATE_MAP.get(
        state,
        {
            "service": state.value,
            "arguments": kwargs.get("arguments", {}),
            "apply": True,
            "expect_modify": kwargs.get("expect_modify", False),
        },
    )

    # Run the service
    return await callback(**callback_args)
