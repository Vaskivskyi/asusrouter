"""Common device-command envelope vocabulary for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin

# Keys of the apply/command request body
ACTION_MODE_KEY = "action_mode"
RC_SERVICE_KEY = "rc_service"


class ARActionMode(FromStrMixin, StrEnum):
    """The `action_mode` field of a device apply/command request."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # System
    APPLY = "apply"
    UPDATE = "Update"

    # AiMesh
    AIMESH_ADD_NODE = "ob_selection"
    AIMESH_NODE_CONFIG_CHANGE = "config_changed"
    AIMESH_ONBOARDING = "onboarding"
    AIMESH_REBOOT = "device_reboot"  # reboots the router and all nodes
    AIMESH_REBUILD = "re_reconnect"

    # Client
    CLIENT_LIST_UPDATE = "update_client_list"

    # Firmware
    FIRMWARE_CHECK = "firmware_check"

    # Known but unverified/niche; enable when confirmed
    # APPLY_NEW = "apply_new"
    # AIMESH_FORCE_ROAMING = "force_roaming"
    # AIMESH_NODE_PREFER = "prefer_node_apply"
    # AIMESH_RESET_DEFAULT = "reset_default"  # factory reset
    # FIRMWARE_UPGRADE = "firmware_upgrade"
    # IPTV_MULTISERVICE_WAN_DISABLE = "disable_multiservice_wan"
    # OPENVPN_CLIENT_IP_REFRESH = "refresh_vpn_ip"
    # UNIT_VPN_SERVER_CHANGE = "change_vpn_server_unit"  # apply.cgi
    # UNIT_WAN_CHANGE = "change_wan_unit"  # apply.cgi
    # UNIT_WL_CHANGE = "change_wl_unit"  # apply.cgi
    # UNIT_WPS_CHANGE = "change_wps_unit"  # apply.cgi
    # WIREGUARD_CLIENT_IP_REFRESH = "refresh_wgc_ip"
    # WPS_APPLY = "wps_apply"
    # WPS_RESET = "wps_reset"
    # WTFAST_LOGIN = "wtfast_login"
    # WTFAST_LOGOUT = "wtfast_logout"


class ARService(FromStrMixin, StrEnum):
    """A device service run via `rc_service`, reusable across modules."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # System
    REBOOT = "reboot"

    # Aura
    AURA_RESTART = "restart_ledg"
    AURA_RGB_START = "start_aurargb"
    AURA_RGB_STOP = "stop_aurargb"

    # Certificate
    CERT_PREPARE = "prepare_cert"

    # Cloud
    CLOUDSYNC_RESTART = "restart_cloudsync"

    # DDNS
    DDNS_CLIENT = "ddnsclient"  # force a DDNS update
    DDNS_LE_RESTART = "restart_ddns_le"  # DDNS restart incl. Let's Encrypt
    DDNS_RESTART = "restart_ddns"

    # DNS
    DNS_RESTART = "restart_dnsmasq"  # dnsmasq
    DNSFILTER_RESTART = "restart_dnsfilter"

    # Firewall
    FIREWALL_RESTART = "restart_firewall"

    # Firmware
    FIRMWARE_UPGRADE_RESTART = "restart_upgrade"
    FIRMWARE_UPGRADE_START = "start_upgrade"
    FIRMWARE_UPGRADE_STOP = "stop_upgrade"
    FIRMWARE_WEB_UPDATE_CHECK = "start_webs_update"
    FIRMWARE_WEB_UPGRADE_START = "start_webs_upgrade"

    # LED
    LED_RESET = "reset_led"
    LED_RESTART = "restart_leds"

    # Network
    NETWORK_PHY_RESTART = "restart_net_and_phy"
    NETWORK_RESTART = "restart_net"
    NETWORK_SUBNET_RESTART = "restart_subnet"

    # OpenVPN
    OPENVPN_RESTART = "restart_openvpnd"
    OPENVPN_STOP = "stop_openvpnd"

    # Password
    CHPASS_RESTART = "restart_chpass"  # account password daemon

    # QoS
    QOS_RESTART = "restart_qos"

    # SDN
    SDN_RESTART = "restart_sdn"

    # Storage
    FTP_RESTART = "restart_ftpd"
    FTP_SAMBA_RESTART = "restart_ftpsamba"
    NAS_APPS_RESTART = "restart_nasapps"
    SAMBA_RESTART = "restart_samba"

    # Time
    TIME_RESTART = "restart_time"
    TIMEMACHINE_RESTART = "restart_timemachine"

    # VPN client
    VPNC_RESTART = "restart_vpnc"
    VPNC_STOP = "stop_vpnc"

    # VPN server
    VPN_SERVER_RESTART = "restart_vpnd"  # vpnd, legacy servers
    VPN_SERVER_STOP = "stop_vpnd"

    # WAN
    WAN_DEFAULT_RESTART = "restart_default_wan"
    WAN_DNS_RESTART = "restart_wan_dns"
    WAN_INTERFACE_RESTART = "restart_wan_if"
    WAN_RESTART = "restart_wan"

    # Web server
    WEBUI_RESTART = "restart_httpd"  # httpd

    # WebDAV
    WEBDAV_RESTART = "restart_webdav"
    WEBDAV_SETTINGS_RESTART = "restart_settings_webdav"

    # WireGuard server
    WIREGUARD_SERVER_RESTART = "restart_wgs"

    # Wireless
    WIRELESS_RESTART = "restart_wireless"
    WIRELESS_SURVEY_RESTART = "restart_wlcscan"

    # Known but unverified feature/scope; enable when confirmed
    # AIPROTECTION_KEY_GUARD_RESTART = "restart_key_guard"
    # AIPROTECTION_RESTART = "restart_wrs"  # web reputation engine
    # AIPROTECTION_START = "start_wrs"
    # AIPROTECTION_STOP_FORCE = "stop_wrs_force"
    # CAPTIVE_PORTAL_RESTART = "restart_CP"  # needs uam_srv + adv_wl chain
    # DISK_FORMAT_START = "start_diskformat"
    # DISK_MONITOR_RESTART = "restart_diskmon"
    # DISK_SCAN_START = "start_diskscan"
    # LOGGER_STOP = "stop_logger"
    # OAM_RESTART = "restart_oam"
    # PRINTER_LPD_RESTART = "restart_lpd"
    # PRINTER_U2EC_RESTART = "restart_u2ec"
    # QOS_ROUTERBOOST_RESTART = "restart_routerboost"
    # SNMP_RESTART = "restart_snmpd"
    # TOR_RESTART = "restart_tor"
    # TR069_RESTART = "restart_tr"
    # TRAFFIC_DNSQD_RESTART = "restart_dnsqd"  # dns query daemon
    # UPNP_RESTART = "restart_upnp"
    # USB_IDLE_RESTART = "restart_usb_idle"
    # WPS_IE_RESTART = "restart_wpsie"
    # WTFAST_RULE_RESTART = "restart_wtfast_rule"


__all__ = [
    "ACTION_MODE_KEY",
    "RC_SERVICE_KEY",
    "ARActionMode",
    "ARService",
]
