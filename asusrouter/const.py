"""AsusRouter constants module"""

#Use the last known working Android app user-agent, so the device will reply
#AR_USER_AGENT = "asusrouter-Android-DUTUtil-1.0.0.255"
#Or use just "asusrouter--DUTUtil-", since only this is needed for a correct replies
AR_USER_AGENT = "asusrouter--DUTUtil-"
#Or even this - all the response will be correct, but the HTTP header will be missing 'AiHOMEAPILevel', 'Httpd_AiHome_Ver' and 'Model_Name' on connect
#AR_USER_AGENT = "asusrouter--"


AR_API = [
    "Model_Name",
    "AiHOMEAPILevel",
    "Httpd_AiHome_Ver",
]

DEFAULT_SLEEP_RECONNECT = 5
DEFAULT_SLEEP_CONNECTING = 1
DEFAULT_SLEEP_TIME = 0.1

DEFAULT_PORT = {
    "http": 80,
    "https": 8443,
}

AR_PATH = {
    "command": "applyapp.cgi",
    "devicemap": "ajax_status.xml",
    "get": "appGet.cgi",
    "login": "login.cgi",
    "logout": "Logout.asp",
    "ports": "ajax_ethernet_ports.asp",
}

AR_ERROR = {
    "authorisation": 2,
    "credentials": 3,
    "try_again": 7,
    "logout": 8,
}

MSG_ERROR = {
    "authorisation": "Session is not authorised",
    "cert_missing": "CA certificate is missing",
    "command": "Error sending a command",
    "credentials": "Wrong credentials",
    "disabled_control": "Device is connected in no-control mode. Sending commands is blocked",
    "disabled_monitor": "Device is connected in no-monitor mode. Sending hooks is blocked",
    "token": "Cannot recieve a token from device",
    "try_again": "Too many attempts",
    "unknown": "Unknown error",
}

MSG_WARNING = {
    "not_connected": "Not connected",
    "refused": "Connection refused",
}

MSG_INFO = {
    "json_fix": "Trying to fix JSON response",
    "reconnect": "Reconnecting",
    "no_cert": "No certificate provided. Using trusted",
    "no_cert_check": "Certificate won't be checked",
    "xml": "Data is in XML",
}

MSG_SUCCESS = {
    "cert_found": "CA certificate found",
    "command": "Command was sent successfully",
    "hook": "Hook was sent successfully",
    "load": "Page was loaded successfully",
    "login": "Login successful",
    "logout": "Logout successful",
}

