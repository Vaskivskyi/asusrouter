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
    AIMESH_GENERATION = "aimesh_generation"

    # Aura
    AURA = "aura"
    AURA_NIGHT_MODE = "aura_night_mode"
    AURA_ZONE = "aura_zone"

    # Connections
    CONNECTIONS = "connections"

    # DSL
    DSL = "dsl"

    # FTP
    FTP = "ftp"
    FTP_CAPABILITIES = "ftp_capabilities"

    # LAN
    LAN_CAPABILITIES = "lan_capabilities"

    # Parental control
    PARENTAL_CONTROL_MAX_ENTRIES = "parental_control_max_entries"
    PARENTAL_CONTROL_MAX_RULES = "parental_control_max_rules"
    PARENTAL_CONTROL_SCHED_VERSION = "parental_control_sched_version"

    # Platform
    PLATFORM = "platform"

    # SDN
    SDN_AWV = "sdn_awv"
    SDN_MAINFH = "sdn_mainfh"
    SDN_MAX_RULES = "sdn_max_rules"
    SDN_MWL = "sdn_mwl"
    SDN_PRIORITY = "sdn_priority"

    # SpeedTest
    SPEEDTEST = "speedtest"
    SPEEDTEST_CAPABILITIES = "speedtest_capabilities"

    # USB
    USB_GENERATION = "usb_generation"
    USB_PORTS = "usb_ports"
    USB_WAN = "usb_wan"

    # WAN
    WAN = "wan"
    WAN_CAPABILITIES = "wan_capabilities"
    WAN_LIMIT = "wan_limit"

    # WiFi
    WIFI_GENERATION = "wifi_generation"
    WIFI_MULTIBAND = "wifi_multiband"
    WIFI_UNITS = "wifi_units"


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
    MODE_REPEATER = "repeater"  # TODO: use it

    # Parental control
    PARENTAL_CONTROL_MAX_ENTRIES = "MaxRule_PC_DAYTIME"
    PARENTAL_CONTROL_MAX_RULES = "MaxRule_parentctrl"
    PARENTAL_CONTROL_SCHED_VERSION = "PC_SCHED_V3"

    # Platform
    PLATFORM_BROADCOM = "bcmwifi"
    PLATFORM_LANTIQ = "lantiq"
    PLATFORM_MEDIATEK = "rawifi"
    PLATFORM_QUALCOMM = "qcawifi"

    # SDN
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
    USB_PORTS = "usbPortMax"
    USB_WAN = "usb_bk"

    # WAN capabilities
    WAN_AGGREGATION = "wanbonding"
    WAN_DUALWAN = "dualwan"
    WAN_LIMIT = "wanMax"
    WAN_NOWAN = "nowan"

    # WiFi generation
    WIFI_5 = "11AC"
    WIFI_6 = "11AX"
    WIFI_7 = "wifi7"

    # WiFi multiband
    WIFI_BANDS_DUAL = "dualband"
    WIFI_BANDS_TRI = "triband"
    WIFI_BANDS_QUAD = "quadband"

    # WiFi power
    WIFI_POWER_CONTROL = "pwrctrl"  # TODO: use it

    # WiFi support by units
    # These parameter defines units at the selected id, but the
    # actual band can be different depending on the device.
    WIFI_UNIT_NONE = "noWiFi"  # No wireless modules
    WIFI_UNIT_0 = "2.4G"
    WIFI_UNIT_1 = "5G"
    WIFI_UNIT_2 = "5G-2"  # Regardless of the flag, this can be also 6GHz
