"""AiMesh enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARAiMeshCapability(FromStrMixin, StrEnum):
    """AiMesh capabilities."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    GENERATION = "generation"
    NEW_ONBOARDING = "new_onboarding"
    NODE = "node"
    ROUTER = "router"


class ARAiMeshDirection(FromStrMixin, StrEnum):
    """Direction of an AiMesh traffic link."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    BACKHAUL = "backhaul"
    FRONTHAUL = "fronthaul"


class ARAiMeshFeature(FromStrMixin, StrEnum):
    """An AiMesh-controllable node feature (a capability bit)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Ethernet backhaul
    ETHERNET_BACKHAUL_MODE = "ethernet_backhaul_mode"

    # Fronthaul AP control
    FRONTHAUL_AP_OPTION_AUTO = "fronthaul_ap_option_auto"
    FRONTHAUL_AP_OPTION_OFF = "fronthaul_ap_option_off"
    FRONTHAUL_AP_OPTION_ON = "fronthaul_ap_option_on"

    # Guest networks (count bits per band)
    GN_2G_1 = "gn_2g_1"
    GN_2G_2 = "gn_2g_2"
    GN_2G_3 = "gn_2g_3"
    GN_5G_1 = "gn_5g_1"
    GN_5G_2 = "gn_5g_2"
    GN_5G_3 = "gn_5g_3"
    GN_5GH_1 = "gn_5gh_1"
    GN_5GH_2 = "gn_5gh_2"
    GN_5GH_3 = "gn_5gh_3"
    GN_6G_1 = "gn_6g_1"
    GN_6G_2 = "gn_6g_2"
    GN_6G_3 = "gn_6g_3"
    GN_6GH_1 = "gn_6gh_1"
    GN_6GH_2 = "gn_6gh_2"
    GN_6GH_3 = "gn_6gh_3"

    # LED control
    CENTRAL_LED = "central_led"
    CENTRAL_LED_ON_OFF = "central_led_on_off"
    LED_AURA = "led_aura"
    LED_BRIGHTNESS = "led_brightness"
    LED_NIGHT_MODE = "led_night_mode"
    LED_ON_OFF = "led_on_off"
    LP55XX_LED = "lp55xx_led"

    # Link aggregation
    LACP = "lacp"

    # Reboot / reconnect / roaming / reset / binding
    MANUAL_FORCE_ROAMING = "manual_force_roaming"
    MANUAL_RECONN = "manual_reconn"
    MANUAL_REBOOT = "manual_reboot"
    MANUAL_RESET_DEFAULT = "manual_reset_default"
    MANUAL_STA_BINDING = "manual_sta_binding"

    # rc_support feature bits
    GUEST_NETWORK = "guest_network"
    LOCAL_ACCESS = "local_access"
    MLO_BH = "mlo_bh"
    MLO_FH = "mlo_fh"
    PORT_STATUS = "port_status"
    SCHED_V2 = "sched_v2"
    SMART_HOME_MASTER_UI = "smart_home_master_ui"
    SWITCHCTRL = "switchctrl"
    USB = "usb"
    VIF_ONBOARDING = "vif_onboarding"
    WIFI_RADIO = "wifi_radio"
    WPA3 = "wpa3"
    WPA3_ENTERPRISE = "wpa3_enterprise"

    # Topology control
    PREFERABLE_BACKHAUL = "preferable_backhaul"
    PREFER_NODE_APPLY = "prefer_node_apply"

    # WAN capability
    WANS_CAP_WAN = "wans_cap_wan"

    # WiFi radio control (per band index)
    WIFI_RADIO_0 = "wifi_radio_0"
    WIFI_RADIO_1 = "wifi_radio_1"
    WIFI_RADIO_2 = "wifi_radio_2"
    WIFI_RADIO_3 = "wifi_radio_3"
    WIFI_RADIO_4 = "wifi_radio_4"


class ARAiMeshMedium(FromStrMixin, StrEnum):
    """Medium of an AiMesh backhaul link."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    MLO = "mlo"
    MOCA = "moca"
    PLC = "plc"
    WIRED = "wired"
    WIRELESS = "wireless"


class ARAiMeshRole(FromStrMixin, StrEnum):
    """Role of an AiMesh device."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    NODE = "node"
    ROUTER = "router"


__all__ = [
    "ARAiMeshCapability",
    "ARAiMeshDirection",
    "ARAiMeshFeature",
    "ARAiMeshMedium",
    "ARAiMeshRole",
]
