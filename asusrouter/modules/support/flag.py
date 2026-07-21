"""Flags for the support module."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARSupportType(FromStrMixin, StrEnum):
    """Device support types as stored in the system."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # AI
    AI = "ai"
    AI_CAPABILITIES = "ai_capabilities"

    # AiMesh
    AIMESH = "aimesh"
    AIMESH_CAPABILITIES = "aimesh_capabilities"

    # Aura
    AURA = "aura"
    AURA_CAPABILITIES = "aura_capabilities"

    # Connections
    CONNECTIONS = "connections"

    # Device mode
    DEVICE_MODE = "device_mode"

    # DSL
    DSL = "dsl"

    # FTP
    FTP = "ftp"
    FTP_CAPABILITIES = "ftp_capabilities"

    # LAN
    LAN_CAPABILITIES = "lan_capabilities"

    # Parental control
    PARENTAL_CONTROL = "parental_control"
    PARENTAL_CONTROL_CAPABILITIES = "parental_control_capabilities"

    # Platform
    PLATFORM = "platform"

    # SDN
    SDN = "sdn"
    SDN_CAPABILITIES = "sdn_capabilities"

    # SpeedTest
    SPEEDTEST = "speedtest"
    SPEEDTEST_CAPABILITIES = "speedtest_capabilities"

    # USB
    USB = "usb"
    USB_CAPABILITIES = "usb_capabilities"

    # VPN
    VPN = "vpn"
    VPN_CAPABILITIES = "vpn_capabilities"

    # WAN
    WAN = "wan"
    WAN_CAPABILITIES = "wan_capabilities"

    # WiFi
    WIFI = "wifi"
    WIFI_CAPABILITIES = "wifi_capabilities"


class ARSupportValue(FromStrMixin, StrEnum):
    """Device support values as stored in the system."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # AI
    AI = "ai_support"
    AI_SLM = "ai_board_slm"
    AI_UPGRADE_BETA = "ai_betaupg"
    AI_RESET_BETA = "ai_reset_beta"

    # AiMesh
    AIMESH = "amas"
    AIMESH_NEW_ONBOARDING = "AMAS_NEWOB"
    AIMESH_NODE = "amasNode"
    AIMESH_ROUTER = "amasRouter"

    # Aura
    AURA = "ledg"
    AURA_NIGHT_MODE = "ledg_night_mode"
    AURA_ZONE = "ledg_count"

    # Connections
    CONNECTION_HTTPS = "HTTPS"
    CONNECTION_SSH = "ssh"

    # DSL
    DSL = "dsl"

    # FTP
    FTP = "noftp"
    FTP_SSL = "ftp_ssl"

    # LAN capabilities
    LAN_AGGREGATION = "lacp"

    # Device mode
    MODE_MEDIA_BRIDGE = "psta"
    MODE_MEDIA_BRIDGE_PROXYSTA = "proxysta"  # newer version
    MODE_NO_ACCESS_POINT = "noAP"  # negative AP
    MODE_NO_ROUTER = "noRouter"  # negative router
    MODE_REPEATER = "repeater"

    # Parental control
    PARENTAL_CONTROL = "PARENTAL2"
    PARENTAL_CONTROL_MAX_ENTRIES = "MaxRule_PC_DAYTIME"
    PARENTAL_CONTROL_MAX_RULES = "MaxRule_parentctrl"
    PARENTAL_CONTROL_SCHED_VERSION = "PC_SCHED_V3"

    # Platform
    PLATFORM_BROADCOM = "bcmwifi"
    PLATFORM_LANTIQ = "lantiq"
    PLATFORM_MEDIATEK = "rawifi"
    PLATFORM_QUALCOMM = "qcawifi"

    # SDN
    SDN = "mtlancfg"
    SDN_AWV = "AWV_SDN"
    SDN_MAINFH = "sdn_mainfh"
    SDN_MAX_RULES = "MaxRule_SDN"
    SDN_MWL = "sdn_mwl"
    SDN_PRIORITY = "SDN_PRIORITY"

    # SpeedTest
    SPEEDTEST = "ookla"
    SPEEDTEST_10G = "10g_speedTest"

    # USB
    USB = "usbX"
    USB_2 = "usbX2"
    USB_3 = "usb3"
    USB_MODEM = "modem"
    USB_NO_MODEM = "nomodem"  # negative modem
    USB_PORTS = "usbPortMax"
    USB_WAN = "usb_bk"

    # VPN
    VPN_CLIENT = "vpnc"
    VPN_FUSION = "vpn_fusion"
    VPN_FUSION_MAX_CONNECTIONS = "MaxRule_VPN_FUSION_Conn"  # concurrent active
    VPN_IPSEC = "ipsec_srv"
    VPN_OPENVPN = "openvpnd"
    VPN_PPTP = "pptpd"
    VPN_WIREGUARD = "wireguard"

    # WAN capabilities
    WAN_AGGREGATION = "wanbonding"
    WAN_DUALWAN = "dualwan"
    WAN_LIMIT = "wanMax"
    WAN_NOWAN = "nowan"
    WAN_REAL_IP = "realip"

    # WiFi capabilities
    WIFI_BANDSTEERING = "bandstr"  # Smart Connect v1
    WIFI_MBO = "mbo"
    WIFI_MLO = "mlo"
    WIFI_MUMIMO = "mumimo"
    WIFI_OFDMA = "ofdma"
    WIFI_OFDMA_DL = "DL_OFDMA"
    WIFI_POWER_CONTROL = "pwrctrl"
    WIFI_SMART_CONNECT = "smart_connect"
    WIFI_SMART_CONNECT_V2 = "smart_connect_v2"

    # WiFi generation
    WIFI_5 = "11AC"
    WIFI_6 = "11AX"
    WIFI_7 = "wifi7"

    # WiFi multiband
    WIFI_BANDS_DUAL = "dualband"
    WIFI_BANDS_TRI = "triband"
    WIFI_BANDS_QUAD = "quadband"

    # WiFi support by units
    # These parameter defines units at the selected id, but the
    # actual band can be different depending on the device.
    WIFI_UNIT_NONE = "noWiFi"  # No wireless modules
    WIFI_UNIT_0 = "2.4G"
    WIFI_UNIT_1 = "5G"
    WIFI_UNIT_2 = "5G-2"  # Regardless of the flag, this can be also 6GHz
