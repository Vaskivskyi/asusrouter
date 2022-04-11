"""Connection module"""

import logging
import aiohttp
import base64
import json
import urllib.parse
import ssl
import asyncio
from pathlib import Path

import asusrouter.helpers as helpers

_LOGGER = logging.getLogger(__name__)

#Use the last known working Android app user-agent, so the device will reply
#_FAKE_USER_AGENT = "asusrouter-Android-DUTUtil-1.0.0.255"

#Or use just "asusrouter--DUTUtil-", since only this is needed for a correct replies
_FAKE_USER_AGENT = "asusrouter--DUTUtil-"

#Or even this - all the response will be correct, but the HTTP header will be missing 'AiHOMEAPILevel', 'Httpd_AiHome_Ver' and 'Model_Name' on connect
#_FAKE_USER_AGENT = "asusrouter--"

DEVICE_API = [
    "Model_Name",
    "AiHOMEAPILevel",
    "Httpd_AiHome_Ver",
]

DEFAULT_PORT = {
    "http": 80,
    "https": 8443,
}

DEFAULT_SLEEP_RECONNECT = 10

_MSG_SUCCESS_LOGIN = "Login successful"
_MSG_SUCCESS_LOGOUT = "Logout successful"
_MSG_SUCCESS_CERT_FOUND = "CA certificate file found"
_MSG_SUCCESS_CERT_CHECKED = "Certificate is valid"

_MSG_NOTIFY_CERT_DEFAULT = "Certificate will be checked using known CAs"
_MSG_NOTIFY_SOURCE_XML = "Data is in XML"
_MSG_NOTIFY_FIX_JSON = "Trying to fix JSON"
_MSG_NOTIFY_RECONNECT = "Trying to reconnect"

_MSG_ERROR_TO_CONNECT = "Cannot connect to host - aborting"
_MSG_ERROR_TO_TOKEN = "Cannot get asus_token"
_MSG_ERROR_TO_REQUEST = "Cannot send request"
_MSG_ERROR_NOT_AUTHORIZED = "Currrent session is not authorized"
_MSG_ERROR_NOT_CONNECTED = "Not connected"
_MSG_ERROR_CREDENTIALS = "Wrong credentials"
_MSG_ERROR_UNKNOWN_CODE = "Unknown ERROR code"
_MSG_ERROR_UNKNOWN_EXCEPTION = "Unknown exception"
_MSG_ERROR_TIMEOUT = "Host timeout"
_MSG_ERROR_DISCONNECTED = "Host disconnected"
_MSG_ERROR_CONNECTOR = "ERR_CONNECTION_REFUSED"
_MSG_ERROR_PARSE_JSON = "Not a valid JSON"
_MSG_ERROR_CERT_FILE_MISSING = "Certificate file does not exist"
_MSG_ERROR_CERT_WRONG_HOST = "ERR_CERT_COMMON_NAME_INVALID"
_MSG_ERROR_CERT_EXPIRED = "ERR_CERT_DATE_INVALID"

class Connection:
    """Create connection"""

    def __init__(
        self,
        host : str,
        username : str,
        password : str,
        port : int | None = None,
        use_ssl: bool = False,
        cert_check : bool = True,
        cert_path : str = ""
    ):
        """Properties for connection"""

        self._host : str | None = host
        self._port : int | None = port
        self._username : str | None = username
        self._password : str | None = password
        self._token : str | None = None
        self._headers : dict | None = None
        self._session : str | None = None

        self._device : dict | None = dict()

        self._http = "https" if use_ssl else "http"

        if self._port is None:
            self._port = DEFAULT_PORT[self._http]

        if cert_check:
            if cert_path != "":
                path = Path(cert_path)
                if path.is_file():
                    self._ssl = ssl.create_default_context(cafile = cert_path)
                    _LOGGER.debug(_MSG_SUCCESS_CERT_FOUND)
                else:
                    _LOGGER.error(_MSG_ERROR_CERT_FILE_MISSING)
                    _LOGGER.debug(_MSG_NOTIFY_CERT_DEFAULT)
                    self._ssl = True
            else:
                _LOGGER.debug(_MSG_NOTIFY_CERT_DEFAULT)
                self._ssl = True
        else:
            self._ssl = False

        self._connected: bool = None

    async def async_run_command(self, command : str, endpoint : str = "appGet.cgi", retry : bool = False) -> dict:
        """Run command. Use the existing connection token, otherwise create new one"""

        if self._token is None and not retry:
            await self.async_connect()
            return await self.async_run_command(command, endpoint, retry = True)
        else:
            if self._token is not None:
                try:
                    result = await self.async_request(command, endpoint, self._headers)
                    return result
                except Exception as ex:
                    if not retry:
                        await self.async_connect()
                        return await self.async_run_command(command, endpoint, retry = True)
                    else:
                        _LOGGER.error(_MSG_ERROR_TO_CONNECT)
                        return {}
            else:
                _LOGGER.error(_MSG_ERROR_TO_CONNECT)
                return {}

    async def async_request(self, payload : str, endpoint : str, headers : dict, retry : bool = False) -> dict:
        """Send a request"""

        json_body = {}

        try:
            async with self._session.post(url="{}://{}:{}/{}".format(self._http, self._host, self._port, endpoint), data = urllib.parse.quote(payload), headers = headers, ssl = self._ssl) as r:
                string_body = await r.text()
                json_body = await r.json()
                if "error_status" in json_body:
                    error_code = json_body['error_status']
                    if error_code == '2':
                        _LOGGER.error(_MSG_ERROR_NOT_AUTHORIZED)
            if endpoint == "login.cgi":
                r_headers = r.headers
                for item in DEVICE_API:
                    if item in r_headers:
                        self._device[item] = r_headers[item]
            return json_body
        except aiohttp.ClientConnectorSSLError:
            _LOGGER.error(_MSG_ERROR_CERT_EXPIRED)
        except aiohttp.ClientConnectorCertificateError:
            _LOGGER.error(_MSG_ERROR_CERT_WRONG_HOST)
        except aiohttp.ServerDisconnectedError:
            _LOGGER.error(_MSG_ERROR_DISCONNECTED)
        except aiohttp.ServerTimeoutError:
            _LOGGER.error(_MSG_ERROR_TIMEOUT)
        except aiohttp.ClientConnectorError:
            _LOGGER.error(_MSG_ERROR_CONNECTOR)
        except json.JSONDecodeError:
            _LOGGER.debug(_MSG_ERROR_PARSE_JSON)
            if ".xml" in endpoint:
                _LOGGER.debug(_MSG_NOTIFY_SOURCE_XML)
                json_body = await helpers.async_convert_xml(text = string_body)
            else:
                _LOGGER.debug(_MSG_NOTIFY_FIX_JSON)
                json_body = await helpers.async_convert_to_json(text = string_body)
            return json_body
        except Exception as ex:
            _LOGGER.error("{}: {}".format(_MSG_ERROR_UNKNOWN_EXCEPTION, ex))

        # If it got here, something is wrong. Reconnect and retry
        _LOGGER.debug(_MSG_NOTIFY_RECONNECT)
        if(retry):
            await asyncio.sleep(DEFAULT_SLEEP_RECONNECT)
        await self.async_connect()
        return await self.async_request(payload = payload, endpoint = endpoint, headers = headers, retry = True)

    async def async_connect(self) -> bool:
        """Start new connection to and get new auth token"""

        _success = False

        self._session = aiohttp.ClientSession()

        auth = "{}:{}".format(self._username, self._password).encode('ascii')
        logintoken = base64.b64encode(auth).decode('ascii')
        payload = "login_authorization={}".format(logintoken)
        headers = {
            'user-agent': _FAKE_USER_AGENT
        }

        response = await self.async_request(payload, "login.cgi", headers)
        if "asus_token" in response:
            self._token = response['asus_token']
            self._headers = {
                'user-agent': _FAKE_USER_AGENT,
                'cookie': 'asus_token={}'.format(self._token)
            }
            _LOGGER.debug("{} on port {}: {}".format(_MSG_SUCCESS_LOGIN, self._port, self._device))

            self._connected = True
            _success = True
        elif "error_status" in response:
            error_code = response['error_status']
            if error_code == '3':
                _LOGGER.error(_MSG_ERROR_CREDENTIALS)
            else:
                _LOGGER.error(_MSG_ERROR_UNKNOWN_CODE)
        else:
            _LOGGER.error(_MSG_ERROR_TO_TOKEN)

        return _success

    async def async_disconnect(self) -> bool:
        """Close the connection"""

        _success = False

        if not self._connected:
            _LOGGER.error(_MSG_ERROR_NOT_CONNECTED)
            await self.async_cleanup()
            return _success

        try:
            response = await self.async_request("", "Logout.asp", self._headers)
            if "error_status" in response:
                error_code = response['error_status']
                if error_code == '8':
                    _LOGGER.debug(_MSG_SUCCESS_LOGOUT)

                    self._connected = False
                    _success = True

                    await self.async_cleanup()
                else:
                    _LOGGER.error(_MSG_ERROR_UNKNOWN_CODE)
        except Exception as ex:
            _LOGGER.error(ex)

        return _success

    async def async_cleanup(self) -> None:
        """Cleanup after logout"""

        self._token = None
        self._headers = None
        if self._session is not None:
            await self._session.close()
        self._session = None

    @property
    def connected(self) -> bool:
        """Connection status"""
        return self._connected

    @property
    def device(self) -> dict:
        """Device model and API support levels"""
        return self._device

