"""DDNS enums for AsusRouter."""

from __future__ import annotations

from enum import StrEnum

from asusrouter.const import UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromStrMixin


class ARDdnsCommand(FromStrMixin, StrEnum):
    """The mutation an action performs on DDNS."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    DEREGISTER = "deregister"  # release an ASUS DDNS hostname
    SET = "set"
    STATE = "state"
    UPDATE = "update"  # force a registration update


class ARDdnsField(FromStrMixin, StrEnum):
    """Keys of the DDNS data dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    HOSTNAME = "hostname"
    HOSTNAME_OLD = "hostname_old"
    IP_ADDRESS = "ip_address"  # last registered WAN IP
    IPV6_UPDATE = "ipv6_update"
    PASSWORD = "password"
    REFRESH_INTERVAL = "refresh_interval"  # days, Merlin only
    REPLACE_STATUS = "replace_status"
    SERVER = "server"
    STATE = "state"
    STATUS = "status"
    TOKEN_STATE = "token_state"  # hostname bound to app account
    UPDATED = "updated"
    USERNAME = "username"
    VERIFICATION = "verification"  # WAN IP and hostname verification
    VERIFICATION_PERIOD = "verification_period"  # minutes, min 30
    WAN_UNIT = "wan_unit"  # -1 auto, 0 primary, 1 secondary
    WILDCARD = "wildcard"


class ARDdnsServer(FromStrMixin, StrEnum):
    """DDNS service provider. Values are the device nvram strings."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    ASUS = "WWW.ASUS.COM"
    ASUS_CN = "WWW.ASUS.COM.CN"
    CLOUDFLARE = "CLOUDFLARE.COM"  # Merlin only
    CUSTOM = "CUSTOM"  # Merlin only, needs a ddns-start script
    DEDYN = "DEDYN.IO"  # Merlin only
    DNSOMATIC = "WWW.DNSOMATIC.COM"
    DYNDNS = "WWW.DYNDNS.ORG"
    DYNDNS_CUSTOM = "WWW.DYNDNS.ORG(CUSTOM)"
    DYNDNS_STATIC = "WWW.DYNDNS.ORG(STATIC)"
    DYNU = "DYNU.COM"
    FREEDNS = "FREEDNS.AFRAID.ORG"
    FREEMYIP = "FREEMYIP.COM"
    GOOGLE = "DOMAINS.GOOGLE.COM"
    HE_NET = "DNS.HE.NET"
    NAMECHEAP = "WWW.NAMECHEAP.COM"  # Merlin only
    NO_IP = "WWW.NO-IP.COM"
    ORAY = "WWW.ORAY.COM"
    PUBYUN = "PUBYUN.COM"  # Merlin only
    SELFHOST = "WWW.SELFHOST.DE"
    TUNNELBROKER = "WWW.TUNNELBROKER.NET"
    ZONEEDIT = "WWW.ZONEEDIT.COM"


class ARDdnsStatus(FromStrMixin, StrEnum):
    """DDNS registration/update status. Values are the device strings."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    AUTH_FAILED = "auth_fail"
    CONNECT_FAILED = "connect_fail"
    DOMAIN_TAKEN = "203"
    ERROR = "-1"
    FIRMWARE_UPDATE_REQUIRED = "402"
    INVALID_DOMAIN = "298"
    INVALID_HOSTNAME = "297"
    INVALID_IP = "299"
    NEW_DOMAIN_TAKEN = "233"
    NO_CHANGE = "no_change"
    NONE = ""
    NOT_REGISTERED = "296"
    PROXY_AUTH_REQUIRED = "407"
    QUERY = "ddns_query"  # update in progress
    REGISTERED_NEW = "230"
    REGISTERED_ORIGINAL = "220"
    SERVER_ERROR = "390"
    SUCCESS = "200"
    TIMEOUT = "Time-out"
    UNAUTHORIZED = "401"
    UNKNOWN_ERROR = "unknown_error"


# Statuses the device treats as an active DDNS registration
ACTIVE_STATUSES: frozenset[ARDdnsStatus] = frozenset(
    {
        ARDdnsStatus.SUCCESS,
        ARDdnsStatus.REGISTERED_NEW,
        ARDdnsStatus.REGISTERED_ORIGINAL,
    }
)


__all__ = [
    "ACTIVE_STATUSES",
    "ARDdnsCommand",
    "ARDdnsField",
    "ARDdnsServer",
    "ARDdnsStatus",
]
