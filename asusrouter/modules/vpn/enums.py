"""VPN enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARVpnProtocol(FromStrMixin, StrEnum):
    """VPN protocol. Acts as a database; not every member has a backend yet."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    IPSEC = "ipsec"
    OPENVPN = "openvpn"
    PPTP = "pptp"
    WIREGUARD = "wireguard"


class ARVpnRole(FromStrMixin, StrEnum):
    """Side of a VPN connection."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CLIENT = "client"
    SERVER = "server"


class ARVpnState(FromIntMixin, IntEnum):
    """Unified VPN connection state across protocols."""

    UNKNOWN = UNKNOWN_MEMBER

    ERROR = -1
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class ARVpnServerField(FromStrMixin, StrEnum):
    """Keys of a VPN server profile dict."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Common
    CLIENTS = "clients"  # peers (WireGuard) or connected accounts (OpenVPN)
    ENABLED = "enabled"
    ERRNO = "errno"
    PORT = "port"
    STATE = "state"

    # Addressing
    ADDRESS = "address"  # server interface address, may carry a prefix
    DHCP = "dhcp"  # assign client addresses from the LAN DHCP range
    LAN_ACCESS = "lan_access"
    LOCAL_ADDRESS = "local_address"  # tunnel local endpoint
    NAT6 = "nat6"
    NETMASK = "netmask"
    POOL_END = "pool_end"  # client address pool end
    POOL_START = "pool_start"  # client address pool start
    REMOTE_ADDRESS = "remote_address"  # tunnel remote endpoint
    SUBNET = "subnet"

    # OpenVPN
    CIPHER = "cipher"
    CLIENT_TO_CLIENT = "client_to_client"
    COMPRESSION = "compression"
    CRYPT = "crypt"  # authorization mode (tls / secret / custom)
    DIGEST = "digest"
    HMAC = "hmac"
    IGNORE_CERTIFICATE = "ignore_certificate"  # client cert not required
    INTERFACE = "interface"  # tun / tap
    PROTOCOL = "protocol"  # udp / tcp
    PUSH_DNS = "push_dns"  # advertise the router as DNS to clients
    REDIRECT_GATEWAY = "redirect_gateway"
    RENEG = "reneg"  # TLS renegotiation interval, seconds
    TLS_KEYSIZE = "tls_keysize"

    # WireGuard
    ALLOW_DNS = "allow_dns"  # advertise the router as DNS to clients
    KEEPALIVE = "keepalive"  # persistent keepalive, seconds
    PRIVATE_KEY = "private_key"  # server private key (secret)
    PSK = "psk"  # pre-shared-key mode toggle
    PUBLIC_KEY = "public_key"  # server public key (clients need it)


class ARVpnClientField(FromStrMixin, StrEnum):
    """Keys of a VPN server client entry (a WireGuard peer or a user)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Common
    ADDRESS = "address"  # VPN-side address(es) of the client
    ENABLED = "enabled"
    NAME = "name"
    REMOTE_ADDRESS = "remote_address"  # client's public endpoint IP
    REMOTE_PORT = "remote_port"
    STATE = "state"

    # OpenVPN account
    PASSWORD = "password"

    # WireGuard peer
    ALLOWED_IPS = "allowed_ips"  # peer's allowed IPs on the server side
    CLIENT_ALLOWED_IPS = "client_allowed_ips"  # allowed IPs pushed to the peer
