"""VPN enums for AsusRouter."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from asusrouter.const import UNKNOWN_MEMBER, UNKNOWN_MEMBER_STR
from asusrouter.tools.enum import FromIntMixin, FromStrMixin


class ARVpnCapability(FromStrMixin, StrEnum):
    """VPN capabilities a device advertises. Acts as a database."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CLIENT = "client"  # Router as a VPN client
    FUSION = "fusion"
    FUSION_CONNECTIONS = "fusion_connections"  # Max concurrent active
    IPSEC = "ipsec"
    OPENVPN = "openvpn"
    PPTP = "pptp"
    WIREGUARD = "wireguard"


class ARVpnProtocol(FromStrMixin, StrEnum):
    """VPN protocol. Acts as a database; not every member has a backend yet."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    CYBERGHOST = "cyberghost"  # OpenVPN-based provider
    IPSEC = "ipsec"
    L2TP = "l2tp"
    NORDVPN = "nordvpn"  # WireGuard-based provider
    OPENVPN = "openvpn"
    PPTP = "pptp"
    SURFSHARK = "surfshark"  # WireGuard-based provider
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


class ARVpnPeerField(FromStrMixin, StrEnum):
    """Keys of a VPN server peer entry (a WireGuard peer or an account)."""

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


class ARVpnClientField(FromStrMixin, StrEnum):
    """Keys of a VPN client profile (the router acting as a VPN client)."""

    UNKNOWN = UNKNOWN_MEMBER_STR

    # Common
    ENABLED = "enabled"  # profile activated
    NAME = "name"  # display description
    PROTOCOL = "protocol"
    STATE = "state"
    STATE_REASON = "state_reason"  # failure reason when not connected

    # Authentication
    PASSWORD = "password"
    USERNAME = "username"

    # Connection (live, non-Fusion clients)
    CONNECTED_SINCE = "connected_since"
    REMOTE_ADDRESS = "remote_address"  # server endpoint the client reached
    REMOTE_PORT = "remote_port"

    # Identity
    SERVER = "server"  # per-protocol unit (WG/OVPN) or host (PPTP/L2TP)
    UNIT = "unit"  # 0-based position, the control target (vpnc_unit)
    VPNC_INDEX = "vpnc_index"  # VPN Fusion connection id, keys the live status

    # Provider
    REGION = "region"

    # Routing
    DEFAULT_WAN = "default_wan"  # profile serves as the default-WAN route
    DEFAULT_WAN_SUPPORT = "default_wan_support"

    # PPTP
    PPTP_OPTIONS = "pptp_options"

    # Statistics (live, non-Fusion clients)
    AUTH_RX_BYTES = "auth_rx_bytes"
    POST_COMPRESS_BYTES = "post_compress_bytes"
    POST_DECOMPRESS_BYTES = "post_decompress_bytes"
    PRE_COMPRESS_BYTES = "pre_compress_bytes"
    PRE_DECOMPRESS_BYTES = "pre_decompress_bytes"
    RX_BYTES = "rx_bytes"  # tunnel transport (TCP/UDP) bytes received
    TUN_TAP_RX_BYTES = "tun_tap_rx_bytes"
    TUN_TAP_TX_BYTES = "tun_tap_tx_bytes"
    TX_BYTES = "tx_bytes"  # tunnel transport (TCP/UDP) bytes sent

    # WireGuard peer
    ADDRESS = "address"  # tunnel address (may carry a prefix)
    ALLOWED_IPS = "allowed_ips"
    DNS = "dns"
    ENDPOINT_ADDRESS = "endpoint_address"  # peer public endpoint
    ENDPOINT_PORT = "endpoint_port"
    KEEPALIVE = "keepalive"  # persistent keepalive, seconds
    MTU = "mtu"
    NAT = "nat"
    PRIVATE_KEY = "private_key"
    PSK = "psk"  # pre-shared key (secret)
    PUBLIC_KEY = "public_key"  # peer public key
