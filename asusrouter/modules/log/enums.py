"""Log enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARLogField(FromStrMixin, StrEnum):
    """Keys of the log data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ANCHOR = "anchor"  # Tail of the last read
    ENTRY_COUNT = "entry_count"
    ENTRY_LIST = "entry_list"
    EVENT_LIST = "event_list"
    LAST_ENTRY = "last_entry"
    PROGRAM_LIST = "program_list"
    TOTAL = "total"


class AREventKey(FromStrMixin, StrEnum):
    """Shared field vocabulary for translated log events."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ACTION = "action"
    ACTIONS = "actions"
    ALIAS = "alias"
    API_CLIENT = "api_client"
    AP_RSSI = "ap_rssi"
    AUTONEG = "autoneg"
    BANDWIDTH = "bandwidth"
    BRIDGE = "bridge"
    CALLER = "caller"
    CHAIN = "chain"
    CHANNEL = "channel"
    CHIP = "chip"
    CLIENT_IP = "client_ip"
    CLIENT_MAC = "client_mac"
    CLIENT_RSSI = "client_rssi"
    COMMAND = "command"
    CONNECTION = "connection"
    DEVICE_MAC = "device_mac"
    DEVICE_SERIAL = "device_serial"
    DUPLEX = "duplex"
    ENABLED = "enabled"
    ERROR = "error"
    EVENT_TYPE = "event_type"
    FREQUENCY = "frequency"
    GATEWAY = "gateway"
    HOSTNAME = "hostname"
    INTERFACE = "interface"
    ISSUER = "issuer"
    LAST_ACTION = "last_action"
    LAST_SERVICE = "last_service"
    LEASE_SECONDS = "lease_seconds"
    LOCAL_IP = "local_ip"
    LOGICAL_PORT = "logical_port"
    MINUTES = "minutes"
    MODULE = "module"
    NETMASK = "netmask"
    NODE_MAC = "node_mac"
    NODE_RSSI = "node_rssi"
    PARAMETER = "parameter"
    PATH = "path"
    PHY_ID = "phy_id"
    PID = "pid"
    PORT = "port"
    PROGRAM = "program"
    PROGRAM_NAME = "program_name"
    RAW = "raw"
    REASON = "reason"
    REASON_TEXT = "reason_text"
    REVISION = "revision"
    RSSI = "rssi"
    SERIAL = "serial"
    SERVICE = "service"
    SERVICES = "services"
    SPEED = "speed"
    STATE = "state"
    STATUS = "status"
    STATUS_TEXT = "status_text"
    SUBJECT = "subject"
    SWITCH_PORT = "switch_port"
    TARGET = "target"
    UUID = "uuid"
    VALID_FROM = "valid_from"
    VALID_TO = "valid_to"
    VALUE = "value"
    VERSION = "version"
    WL_ID = "wl_id"


class ARProgram(FromStrMixin, StrEnum):
    """The program that emitted a log entry."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AHS = "ahs"
    AUTO_CHANNEL_DAEMON = "acsd"
    AVAHI_DAEMON = "avahi-daemon"
    BAND_STEERING_DAEMON = "bsd"
    CRON = "crond"
    DHCP_CLIENT = "dhcp client"
    DISK_MONITOR = "disk_monitor"
    DNSMASQ = "dnsmasq"
    DNSMASQ_DHCP = "dnsmasq-dhcp"
    FTP_SERVER = "FTP Server"
    HOSTAPD = "hostapd"
    HOUR_MONITOR = "hour_monitor"
    HTTP_DAEMON = "httpd"
    INIT = "init"
    ITUNES = "iTunes"
    KERNEL = "kernel"
    MINIUPNP = "miniupnpd"
    MODPROBE = "modprobe"
    NTP = "ntp"
    PPPD = "pppd"
    RC_SERVICE = "rc_service"
    ROAMING_ASSISTANT = "roamast"
    SAMBA_SERVER = "Samba Server"
    SYSLOG = "syslogd"
    TIMEMACHINE = "Timemachine"
    VPN_CLIENT = "vpnclient"
    VPN_SERVER = "vpnserver"
    WIFI_SCHEDULER = "wifi scheduler"
    WIRELESS_CLIENT_DAEMON = "wlceventd"


__all__ = [
    "AREventKey",
    "ARLogField",
    "ARProgram",
]
