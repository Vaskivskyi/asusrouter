"""NVRAM module for AsusRouter.

This module is for NVRAM-related operations.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.modules.common.connection import (
    ARConnectionMethod,
    ARConnectionStatus,
)
from asusrouter.modules.endpoint_v2 import AREndpoint
from asusrouter.modules.endpoint_v2.hooks import ARHook, hook_request
from asusrouter.modules.source import ARDataSource, ARDataType
from asusrouter.registry import ARCallableRegistry as ARCallReg
from asusrouter.tools.converters import safe_list_from_string
from asusrouter.tools.converters_v2.raw import raw_to_bool, raw_to_int
from asusrouter.tools.enum import FromStrMixin
from asusrouter.tools.identifiers import MacAddress
from asusrouter.tools.identifiers.ip import IpAddress, read_ip_list
from asusrouter.tools.types import ARCallableType, ARCallbackType

read_mac = MacAddress.from_value_safe


class ARNvramType(ARDataType):
    """AsusRouter NVRAM type class."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Device information
    MAC = "label_mac"
    MODEL = "productid"
    MODEL_ORIGINAL = "odmpid"
    SECRET_CODE = "secret_code"  # noqa: S105
    SERIAL = "serial_no"
    WIRELESS_BANDS = "wlnband_list"

    # Brand and geographical information
    COBRAND = "CoBrand"
    GEO_LOCATION = "location_code"
    GEO_TERRITORY = "territory_code"

    # Firmware information (can change)
    FW_MAJOR = "firmver"
    FW_MINOR = "buildno"
    FW_BUILD = "extendno"
    FW_SWPJ = "swpjverno"

    # Hardware information (cannot change)
    HW_ID = "HwId"

    # Software information (configurable by user)
    SW_MODE = "sw_mode"

    # Supported features (raw, fallback for on old firmware)
    RC_SUPPORT = "rc_support"

    # Everything further is grouped by category
    # Categories go in alphabetical order, same for items in item

    # AI Board
    AI_FW_PATH = "ai_fw_path"
    AI_RESCUE_TIME = "ai_rescue_ts"
    AI_STATUS = "ai_prog_status"

    # DDNS
    DDNS_STATE = "ddns_enable_x"
    DDNS_SERVER = "ddns_server_x"
    DDNS_HOSTNAME = "ddns_hostname_x"
    DDNS_OLD_NAME = "ddns_old_name"
    DDNS_UPDATED = "ddns_updated"
    DDNS_RETURN_CODE_CHK = "ddns_return_code_chk"

    # DNS
    DNS_PING_LIST = "dns_ping_list"
    DNS_PING_STATUS = "dns_ping_state"

    # DSL
    DSL_DATARATE_DOWN = "dsllog_dataratedown"
    DSL_DATARATE_UP = "dsllog_datarateup"

    # Dual WAN
    DUAL_WAN_CAPABILITY = "wans_cap"
    DUAL_WAN_CONFIG = "wans_dualwan"
    DUAL_WAN_EXTWAN = "wans_extwan"
    DUAL_WAN_LANPORT = "wans_lanport"
    DUAL_WAN_LB_RATIO = "wans_lb_ratio"
    DUAL_WAN_MODE = "wans_mode"
    DUAL_WAN_ROUTING = "wans_routing_enable"
    DUAL_WAN_STANDBY = "wans_standby"
    DUAL_WAN_USB_BACKUP = "wans_usb_bk_act"

    # DWB
    DWB_BAND = "dwb_band"
    DWB_MODE = "dwb_mode"

    # EULA
    EULA_STATE = "ASUS_NEW_EULA"
    EULA_TIME = "ASUS_NEW_EULA_time"
    EULA_OLD_TIME = "TM_EULA_time"
    EULA_OLD_STATE = "TM_EULA"

    # FTP
    FTP_MODE = "st_ftp_mode"
    FTP_STATE = "enable_ftp"

    # HTTP
    HTTP_AUTOLOGOUT = "http_autologout"  # minutes
    HTTP_PREFERRED_LANGUAGE = "preferred_lang"

    # IP
    IP_LAN = "lan_ipaddr"
    IP_LAN_T = "lan_ipaddr_t"

    # LED
    AURA = "AllLED"
    AURA_COUNT = "ledg_count"
    AURA_NIGHT_MODE = "ledg_night_mode"
    AURA_NIGHT_RGB = "ledg_night_rgb"
    AURA_RGB = "ledg_rgb"
    AURA_SCHEME = "ledg_scheme"
    AURA_SCHEME_PREV = "ledg_scheme_old"
    AURA_SDN = "ledg_sdn"
    LED = "led_val"

    # Let's Encrypt
    LETS_ENCRYPT_STATE = "le_enable"
    LETS_ENCRYPT_STATUS = "le_state"

    # MAC addresses
    MAC_LAN = "lan_hwaddr"
    MAC_WAN = "wan_hwaddr"

    # Port forwarding
    PORT_FORWARDING_STATE = "vts_enable_x"
    PORT_FORWARDING_LIST = "vts_rulelist"
    PORT_FORWARDING_LIST_SECONDARY = "vts1_rulelist"  # dual-WAN load-balance

    # Samba
    SAMBA_MODE = "st_samba_mode"
    SAMBA_STATE = "enable_samba"

    # SDN
    SDN_RL = "sdn_rl"

    # SpeedTest
    OOKLA_START_TIME = "ookla_start_time"
    OOKLA_STATE = "ookla_state"

    # VPN
    VPNC_CLIENTLIST = "vpnc_clientlist"
    VPNC_DEFAULT_WAN = "vpnc_default_wan"
    VPNC_PPTP_OPTIONS = "vpnc_pptp_options_x_list"
    VPNC_UNIT = "vpnc_unit"
    VPN_CLIENT_EAS = "vpn_clientx_eas"
    VPN_SERVER1_STATUS = "vpn_server1_status"
    VPN_SERVER2_STATUS = "vpn_server2_status"
    VPN_SERVER_C2C = "vpn_server_c2c"
    VPN_SERVER_CIPHER = "vpn_server_cipher"
    VPN_SERVER_CLIENTLIST = "vpn_serverx_clientlist"
    VPN_SERVER_COMP = "vpn_server_comp"
    VPN_SERVER_CRYPT = "vpn_server_crypt"
    VPN_SERVER_DHCP = "vpn_server_dhcp"
    VPN_SERVER_DIGEST = "vpn_server_digest"
    VPN_SERVER_ENABLE = "VPNServer_enable"
    VPN_SERVER_HMAC = "vpn_server_hmac"
    VPN_SERVER_IF = "vpn_server_if"
    VPN_SERVER_IGNCRT = "vpn_server_igncrt"
    VPN_SERVER_LOCAL = "vpn_server_local"
    VPN_SERVER_NM = "vpn_server_nm"
    VPN_SERVER_PDNS = "vpn_server_pdns"
    VPN_SERVER_PORT = "vpn_server_port"
    VPN_SERVER_PROTO = "vpn_server_proto"
    VPN_SERVER_R1 = "vpn_server_r1"
    VPN_SERVER_R2 = "vpn_server_r2"
    VPN_SERVER_REMOTE = "vpn_server_remote"
    VPN_SERVER_RENEG = "vpn_server_reneg"
    VPN_SERVER_RGW = "vpn_server_rgw"
    VPN_SERVER_SN = "vpn_server_sn"
    VPN_SERVER_TLS_KEYSIZE = "vpn_server_tls_keysize"
    VPN_SERVER_UNIT = "vpn_server_unit"
    WGC_ENABLE = "wgc_enable"
    WGC_UNIT = "wgc_unit"
    WGS_ADDR = "wgs_addr"
    WGS_ALIVE = "wgs_alive"
    WGS_DNS = "wgs_dns"
    WGS_ENABLE = "wgs_enable"
    WGS_LANACCESS = "wgs_lanaccess"
    WGS_NAT6 = "wgs_nat6"
    WGS_PORT = "wgs_port"
    WGS_PRIV = "wgs_priv"
    WGS_PSK = "wgs_psk"
    WGS_PUB = "wgs_pub"
    WGS_UNIT = "wgs_unit"

    # WAN
    LINK_INTERNET = "link_internet"
    LINK_WAN0 = "link_wan"
    LINK_WAN1 = "link_wan1"
    WAN_AGGREGATION = "bond_wan"
    WAN_AGGREGATION_PORTS = "wanports_bond"
    WAN_AUTODETECT = "autowan_enable"
    WAN_PROTOCOL = "wan_proto"
    WAN_UNIT = "wan_unit"

    # WAN connection (flat / active-unit working copy)
    WAN_AUTH = "wan_auth_x"
    WAN_CLIENTID = "wan_clientid"
    WAN_CLIENTID_TYPE = "wan_clientid_type"
    WAN_DHCP_ENABLE = "wan_dhcpenable_x"
    WAN_DHCP_QUERY = "wan_dhcp_qry"
    WAN_DNS1 = "wan_dns1_x"
    WAN_DNS2 = "wan_dns2_x"
    WAN_DNS_ENABLE = "wan_dnsenable_x"
    WAN_DOT1P = "wan_dot1p"
    WAN_DOT1Q = "wan_dot1q"
    WAN_ENABLE = "wan_enable"
    WAN_GATEWAY = "wan_gateway_x"
    WAN_HOSTNAME = "wan_hostname"
    WAN_IPADDR = "wan_ipaddr_x"
    WAN_MAC_CLONE = "wan_hwaddr_x"
    WAN_MTU = "wan_mtu"
    WAN_NAT = "wan_nat_x"
    WAN_NETMASK = "wan_netmask_x"
    WAN_UPNP = "wan_upnp_enable"
    WAN_VENDORID = "wan_vendorid"
    WAN_VID = "wan_vid"

    # WAN PPP (flat / active-unit working copy)
    WAN_HEARTBEAT = "wan_heartbeat_x"
    WAN_PPPOE_AC = "wan_pppoe_ac"
    WAN_PPPOE_HOSTUNIQ = "wan_pppoe_hostuniq"
    WAN_PPPOE_IDLETIME = "wan_pppoe_idletime"
    WAN_PPPOE_MRU = "wan_pppoe_mru"
    WAN_PPPOE_MTU = "wan_pppoe_mtu"
    WAN_PPPOE_OPTIONS = "wan_pppoe_options_x"
    WAN_PPPOE_SERVICE = "wan_pppoe_service"
    WAN_PPP_CONN = "wan_ppp_conn"
    WAN_PPP_ECHO = "wan_ppp_echo"
    WAN_PPP_ECHO_FAILURE = "wan_ppp_echo_failure"
    WAN_PPP_ECHO_INTERVAL = "wan_ppp_echo_interval"

    # WAN softwire / IPv6 transition (flat)
    WAN_S46_AFTR = "ipv6_s46_aftr"
    WAN_S46_B4ADDR = "ipv6_s46_b4addr"
    WAN_S46_DSLITE_MODE = "wan_s46_dslite_mode"
    WAN_S46_EALEN = "wan_s46_ealen_x"
    WAN_S46_OFFSET = "wan_s46_offset_x"
    WAN_S46_PEER = "wan_s46_peer_x"
    WAN_S46_PREFIX4 = "wan_s46_prefix4_x"
    WAN_S46_PREFIX4LEN = "wan_s46_prefix4len_x"
    WAN_S46_PREFIX6 = "wan_s46_prefix6_x"
    WAN_S46_PREFIX6LEN = "wan_s46_prefix6len_x"
    WAN_S46_PSID = "wan_s46_psid_x"
    WAN_S46_PSIDLEN = "wan_s46_psidlen_x"

    # WAN watchdog
    WATCHDOG_ENABLE = "wandog_enable"
    WATCHDOG_FAILBACK_COUNT = "wandog_fb_count"
    WATCHDOG_INTERVAL = "wandog_interval"
    WATCHDOG_MAX_FAIL = "wandog_maxfail"
    WATCHDOG_TARGET = "wandog_target"

    # WPS
    WPS_STATE = "wps_enable"

    def as_hook(self) -> tuple[ARHook, str]:
        """Render as an `nvram_get` hook call."""

        return (ARHook.NVRAM_GET, self.value)


class ARNvramIndexType(FromStrMixin, StrEnum):
    """Indexed NVRAM keys: each member is an f-string template (one `{}`)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Aura (per-scheme)
    AURA_RGB = "ledg_rgb{}"

    # SDN AP group (index = group prefix + index, e.g. `g1` for `apg1`)
    AP_11BE = "ap{}_11be"
    AP_AP_ISOLATE = "ap{}_ap_isolate"
    AP_BW_LIMIT = "ap{}_bw_limit"
    AP_DUT_LIST = "ap{}_dut_list"
    AP_ENABLE = "ap{}_enable"
    AP_EXPIRETIME = "ap{}_expiretime"
    AP_HIDE_SSID = "ap{}_hide_ssid"
    AP_MACLIST = "ap{}_maclist"
    AP_MACMODE = "ap{}_macmode"
    AP_MLO = "ap{}_mlo"
    AP_SCHED = "ap{}_sched"
    AP_SECURITY = "ap{}_security"
    AP_SSID = "ap{}_ssid"
    AP_TIMESCHED = "ap{}_timesched"

    # VPN client - OpenVPN (per-unit)
    VPN_CLIENT_ADDR = "vpn_client{}_addr"
    VPN_CLIENT_DESC = "vpn_client{}_desc"
    VPN_CLIENT_ERRNO = "vpn_client{}_errno"
    VPN_CLIENT_PORT = "vpn_client{}_port"
    VPN_CLIENT_STATE = "vpn_client{}_state"
    VPN_CLIENT_USERNAME = "vpn_client{}_username"

    # VPN client - WireGuard (per-unit)
    WGC_ADDR = "wgc{}_addr"
    WGC_AIPS = "wgc{}_aips"
    WGC_ALIVE = "wgc{}_alive"
    WGC_DNS = "wgc{}_dns"
    WGC_ENABLE = "wgc{}_enable"
    WGC_EP_ADDR = "wgc{}_ep_addr"
    WGC_EP_PORT = "wgc{}_ep_port"
    WGC_MTU = "wgc{}_mtu"
    WGC_NAT = "wgc{}_nat"
    WGC_PPUB = "wgc{}_ppub"
    WGC_PRIV = "wgc{}_priv"
    WGC_PSK = "wgc{}_psk"

    # VPN server - OpenVPN (per-unit)
    VPN_SERVER_ERRNO = "vpn_server{}_errno"
    VPN_SERVER_STATE = "vpn_server{}_state"

    # VPN server - WireGuard peers (per-peer, single server unit)
    WGS_PEER_ADDR = "wgs1_c{}_addr"
    WGS_PEER_AIPS = "wgs1_c{}_aips"
    WGS_PEER_CAIPS = "wgs1_c{}_caips"
    WGS_PEER_ENABLE = "wgs1_c{}_enable"
    WGS_PEER_NAME = "wgs1_c{}_name"

    # WAN (per-unit)
    WAN_DOT1Q = "wan{}_dot1q"
    WAN_ENABLE = "wan{}_enable"
    WAN_PRIMARY = "wan{}_primary"
    WAN_PROTO = "wan{}_proto"
    WAN_REALIP = "wan{}_realip_ip"
    WAN_REALIP_STATE = "wan{}_realip_state"
    WAN_STATE = "wan{}_state_t"
    WAN_STATE_AUX = "wan{}_auxstate_t"
    WAN_STATE_SUB = "wan{}_sbstate_t"
    WAN_VID = "wan{}_vid"

    # WAN address - main (`wan{n}_`)
    WAN_DNS = "wan{}_dns"
    WAN_EXPIRES = "wan{}_expires"
    WAN_GATEWAY = "wan{}_gateway"
    WAN_IPADDR = "wan{}_ipaddr"
    WAN_LEASE = "wan{}_lease"
    WAN_NETMASK = "wan{}_netmask"

    # WAN address - extra (`wan{n}x_`)
    WAN_DNS_X = "wan{}x_dns"
    WAN_EXPIRES_X = "wan{}x_expires"
    WAN_GATEWAY_X = "wan{}x_gateway"
    WAN_IPADDR_X = "wan{}x_ipaddr"
    WAN_LEASE_X = "wan{}x_lease"
    WAN_NETMASK_X = "wan{}x_netmask"

    # WAN connection
    WAN_CLIENTID = "wan{}_clientid"
    WAN_DHCP_ENABLE = "wan{}_dhcpenable_x"
    WAN_DNS1 = "wan{}_dns1_x"
    WAN_DNS2 = "wan{}_dns2_x"
    WAN_DNS_ENABLE = "wan{}_dnsenable_x"
    WAN_HOSTNAME = "wan{}_hostname"
    WAN_MAC_CLONE = "wan{}_hwaddr_x"
    WAN_MTU = "wan{}_mtu"
    WAN_NAT = "wan{}_nat_x"
    WAN_VENDORID = "wan{}_vendorid"

    # WAN ISP routing
    WAN_ISP_COUNTRY = "wan{}_isp_country"
    WAN_ISP_LIST = "wan{}_isp_list"
    WAN_ISP_NUM = "wan{}_country_isp_num"
    WAN_ROUTING_ISP = "wan{}_routing_isp"
    WAN_ROUTING_ISP_ENABLE = "wan{}_routing_isp_enable"

    # WAN PPP
    WAN_HEARTBEAT = "wan{}_heartbeat_x"
    WAN_PPPOE_AC = "wan{}_pppoe_ac"
    WAN_PPPOE_HOSTUNIQ = "wan{}_pppoe_hostuniq"
    WAN_PPPOE_IDLETIME = "wan{}_pppoe_idletime"
    WAN_PPPOE_MRU = "wan{}_pppoe_mru"
    WAN_PPPOE_MTU = "wan{}_pppoe_mtu"
    WAN_PPPOE_OPTIONS = "wan{}_pppoe_options_x"
    WAN_PPPOE_SERVICE = "wan{}_pppoe_service"
    WAN_PPP_CONN = "wan{}_ppp_conn"
    WAN_PPP_ECHO = "wan{}_ppp_echo"
    WAN_PPP_ECHO_FAILURE = "wan{}_ppp_echo_failure"
    WAN_PPP_ECHO_INTERVAL = "wan{}_ppp_echo_interval"

    # WAN softwire / IPv6 transition
    WAN_S46_DSLITE_MODE = "wan{}_s46_dslite_mode"
    WAN_S46_DSLITE_SVC = "wan{}_s46_dslite_svc"
    WAN_S46_EALEN = "wan{}_s46_ealen_x"
    WAN_S46_OFFSET = "wan{}_s46_offset_x"
    WAN_S46_PEER = "wan{}_s46_peer_x"
    WAN_S46_PREFIX4 = "wan{}_s46_prefix4_x"
    WAN_S46_PREFIX4LEN = "wan{}_s46_prefix4len_x"
    WAN_S46_PREFIX6 = "wan{}_s46_prefix6_x"
    WAN_S46_PREFIX6LEN = "wan{}_s46_prefix6len_x"
    WAN_S46_PSID = "wan{}_s46_psid_x"
    WAN_S46_PSIDLEN = "wan{}_s46_psidlen_x"

    # WiFi (per-unit; guest networks use a `{unit}.{slot}` index)
    WL_AP_ISOLATE = "wl{}_ap_isolate"
    WL_AUTH_MODE = "wl{}_auth_mode_x"
    WL_BSS_ENABLED = "wl{}_bss_enabled"
    WL_BW_DL = "wl{}_bw_dl"
    WL_BW_ENABLED = "wl{}_bw_enabled"
    WL_BW_UL = "wl{}_bw_ul"
    WL_CLOSED = "wl{}_closed"
    WL_COUNTRY_CODE = "wl{}_country_code"
    WL_CRYPTO = "wl{}_crypto"
    WL_EXPIRE = "wl{}_expire"
    WL_EXPIRE_TMP = "wl{}_expire_tmp"
    WL_HWADDR = "wl{}_hwaddr"
    WL_LANACCESS = "wl{}_lanaccess"
    WL_MACLIST = "wl{}_maclist"
    WL_MACLIST_X = "wl{}_maclist_x"
    WL_MACMODE = "wl{}_macmode"
    WL_NBAND = "wl{}_nband"
    WL_RADIO = "wl{}_radio"
    WL_SSID = "wl{}_ssid"
    WL_VERSION = "wl{}_version"
    WL_WPA_PSK = "wl{}_wpa_psk"

    # WiFi band (index = band prefix, e.g. `2g1`)
    WL_BAND_11BE = "{}_11be"
    WL_BAND_BW = "{}_bw"
    WL_BAND_BW_160 = "{}_bw_160"
    WL_BAND_BW_240 = "{}_bw_240"
    WL_BAND_CHANSPEC = "{}_chanspec"
    WL_BAND_NCTRLSB = "{}_nctrlsb"
    WL_BAND_NMODE = "{}_nmode_x"

    def key(self, index: int | str) -> str:
        """Resolve the template into a raw NVRAM key."""

        return self.value.format(index)


class ARNvramIndexSource(ARDataSource):
    """An `ARNvramIndexType` bound to an index, fetchable as one NVRAM key.

    The index is usually an int unit; string indices serve composite
    prefixes (e.g. a band `2g1`, a guest slot `0.1`, an AP group `g1`).
    """

    def __init__(self, kind: ARNvramIndexType, index: int | str) -> None:
        """Initialize the indexed NVRAM source."""

        super().__init__()

        self.kind = kind
        self.index = index

    @property
    def key(self) -> str:
        """The resolved NVRAM key (e.g. `wan0_ipaddr`)."""

        return self.kind.key(self.index)

    def as_hook(self) -> tuple[ARHook, str]:
        """Render as an `nvram_get` hook call."""

        return (ARHook.NVRAM_GET, self.key)

    def __eq__(self, other: object) -> bool:
        """Equal by kind and index."""

        if not isinstance(other, ARNvramIndexSource):
            return NotImplemented
        return self.kind == other.kind and self.index == other.index

    def __hash__(self) -> int:
        """Hash by kind and index."""

        return hash((type(self), self.kind, self.index))

    def __repr__(self) -> str:
        """Representation of the indexed NVRAM source."""

        return f"<ARNvramIndexSource {self.key}>"


# A flat or indexed NVRAM request item
ARNvramItem = ARNvramType | ARNvramIndexSource


# Translators per member; indexed values key on their template type
# Only general (common / utility) translations belong here - module-specific
# conversions stay in their own module
# Flat and indexed keys never collide: index templates contain `{}`
_TRANSLATION: dict[ARNvramType | ARNvramIndexType, ARCallableType] = {
    ARNvramType.MAC: read_mac,
    ARNvramType.MAC_LAN: read_mac,
    ARNvramType.MAC_WAN: read_mac,
    # WAN globals
    ARNvramType.DUAL_WAN_CAPABILITY: safe_list_from_string,
    ARNvramType.DUAL_WAN_CONFIG: safe_list_from_string,
    ARNvramType.DUAL_WAN_EXTWAN: raw_to_bool,
    ARNvramType.DUAL_WAN_LANPORT: raw_to_int,
    ARNvramType.DUAL_WAN_ROUTING: raw_to_bool,
    ARNvramType.DUAL_WAN_STANDBY: raw_to_bool,
    ARNvramType.DUAL_WAN_USB_BACKUP: raw_to_bool,
    ARNvramType.LINK_INTERNET: ARConnectionStatus.from_value,
    ARNvramType.LINK_WAN0: raw_to_bool,
    ARNvramType.LINK_WAN1: raw_to_bool,
    ARNvramType.WAN_AGGREGATION: raw_to_bool,
    ARNvramType.WAN_AGGREGATION_PORTS: safe_list_from_string,
    ARNvramType.WAN_AUTODETECT: raw_to_bool,
    ARNvramType.WAN_S46_AFTR: IpAddress.from_value_safe,
    ARNvramType.WAN_S46_B4ADDR: IpAddress.from_value_safe,
    ARNvramType.WAN_UNIT: raw_to_int,
    ARNvramType.WATCHDOG_ENABLE: raw_to_bool,
    ARNvramType.WATCHDOG_FAILBACK_COUNT: raw_to_int,
    ARNvramType.WATCHDOG_INTERVAL: raw_to_int,
    ARNvramType.WATCHDOG_MAX_FAIL: raw_to_int,
    # WAN per-unit status
    ARNvramIndexType.WAN_DOT1Q: raw_to_bool,
    ARNvramIndexType.WAN_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_PRIMARY: raw_to_bool,
    ARNvramIndexType.WAN_PROTO: ARConnectionMethod.from_value,
    ARNvramIndexType.WAN_REALIP: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_REALIP_STATE: raw_to_bool,
    ARNvramIndexType.WAN_STATE: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_AUX: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_STATE_SUB: ARConnectionStatus.from_value,
    ARNvramIndexType.WAN_VID: raw_to_int,
    # WAN per-unit addresses
    ARNvramIndexType.WAN_DNS: read_ip_list,
    ARNvramIndexType.WAN_DNS_X: read_ip_list,
    ARNvramIndexType.WAN_EXPIRES: raw_to_int,
    ARNvramIndexType.WAN_EXPIRES_X: raw_to_int,
    ARNvramIndexType.WAN_GATEWAY: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_GATEWAY_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_IPADDR_X: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_LEASE: raw_to_int,
    ARNvramIndexType.WAN_LEASE_X: raw_to_int,
    ARNvramIndexType.WAN_NETMASK: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_NETMASK_X: IpAddress.from_value_safe,
    # WAN per-unit connection config
    ARNvramIndexType.WAN_DHCP_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_DNS1: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_DNS2: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_DNS_ENABLE: raw_to_bool,
    ARNvramIndexType.WAN_MAC_CLONE: read_mac,
    ARNvramIndexType.WAN_MTU: raw_to_int,
    ARNvramIndexType.WAN_NAT: raw_to_bool,
    ARNvramIndexType.WAN_ROUTING_ISP_ENABLE: raw_to_bool,
    # WAN per-unit PPP
    ARNvramIndexType.WAN_PPPOE_IDLETIME: raw_to_int,
    ARNvramIndexType.WAN_PPPOE_MRU: raw_to_int,
    ARNvramIndexType.WAN_PPPOE_MTU: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO_FAILURE: raw_to_int,
    ARNvramIndexType.WAN_PPP_ECHO_INTERVAL: raw_to_int,
    # WAN per-unit softwire
    ARNvramIndexType.WAN_S46_DSLITE_MODE: raw_to_int,
    ARNvramIndexType.WAN_S46_EALEN: raw_to_int,
    ARNvramIndexType.WAN_S46_OFFSET: raw_to_int,
    ARNvramIndexType.WAN_S46_PEER: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX4: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX4LEN: raw_to_int,
    ARNvramIndexType.WAN_S46_PREFIX6: IpAddress.from_value_safe,
    ARNvramIndexType.WAN_S46_PREFIX6LEN: raw_to_int,
    ARNvramIndexType.WAN_S46_PSID: raw_to_int,
    ARNvramIndexType.WAN_S46_PSIDLEN: raw_to_int,
}


def _resolve_key(item: ARNvramItem) -> str:
    """Resolve a requested item to its raw NVRAM key."""

    if isinstance(item, ARNvramIndexSource):
        return item.key
    return item.value


async def get_state(
    callback: ARCallbackType,
    source: ARNvramItem | Iterable[ARNvramItem],
    **kwargs: Any,
) -> dict[ARNvramItem, str]:
    """Fetch the NVRAM data state."""

    items: list[ARNvramItem] = (
        [source]
        if isinstance(source, (ARNvramType, ARNvramIndexSource))
        else list(source)
    )

    # Map each raw key back to the item that requested it
    forward: dict[str, ARNvramItem] = {
        _resolve_key(item): item for item in items
    }

    request = hook_request(*forward.values())
    response = await callback(endpoint=AREndpoint.FETCH_DATA, request=request)

    if not isinstance(response, dict):
        return {}

    return {
        requester: value
        for key, value in response.items()
        if (requester := forward.get(key)) is not None
    }


def translate_state(
    data: dict[ARNvramItem, Any],
    **kwargs: Any,
) -> dict[ARNvramItem, Any]:
    """Translate the NVRAM data state."""

    result: dict[ARNvramItem, Any] = {}
    for item, value in data.items():
        member: ARNvramType | ARNvramIndexType = (
            item.kind if isinstance(item, ARNvramIndexSource) else item
        )
        converter = _TRANSLATION.get(member)
        result[item] = converter(value) if converter else value
    return result


ARCallReg.register_module(
    ARNvramType,
    get_state=get_state,
    translate_state=translate_state,
    multi=True,
)
ARCallReg.register_module(
    ARNvramIndexSource,
    get_state=get_state,
    translate_state=translate_state,
    multi=True,
)
