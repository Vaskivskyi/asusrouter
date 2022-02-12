"""Connection module"""

import asyncio
from asyncio import IncompleteReadError
import logging
from asyncio import LimitOverrunError, TimeoutError
from math import floor
from textwrap import indent
import aiohttp
import base64
import json
import time
import urllib.parse

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

#Use the last known working Android app user-agent, so the device will reply
#_FAKE_USER_AGENT = "asusrouter-Android-DUTUtil-1.0.0.255"

#Or use just "asusrouter--DUTUtil-", since only this is needed for a correct replies
_FAKE_USER_AGENT = "asusrouter--DUTUtil-"

#Or even this - all the response will be correct, but the HTTP header will be missing 'AiHOMEAPILevel', 'Httpd_AiHome_Ver' and 'Model_Name' on connect
#_FAKE_USER_AGENT = "asusrouter--"

_MSG_ERROR_TO_CONNECT = "Cannot connect to host - aborting"
_MSG_ERROR_TO_TOKEN = "Cannot get asus_token"
_MSG_ERROR_TO_REQUEST = "Cannot send request"
_MSG_ERROR_CREDENTIALS = "Wrong credentials"
_MSG_ERROR_UNKNOWN_CODE = "Unknown ERROR code"
_MSG_ERROR_TIMEOUT = "Host timeout"
_MSG_ERROR_DISCONNECTED = "Host disconnected"

class Connection:
    """Create connection"""

    def __init__(self, host, username, password):
        """Properties for connection"""

        self._host = host
        self._username = username
        self._password = password
        self._token = None
        self._headers = None
        self._session = None

    async def async_run_command(self, command, endpoint = "appGet.cgi", retry = False):
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

    async def async_request(self, payload, endpoint, headers):
        """Send a request"""

        try:
            async with self._session.post(url="http://{}/{}".format(self._host, endpoint), data = urllib.parse.quote(payload), headers = headers) as r:
                json_body = await r.json()
            return json_body
        except aiohttp.ServerDisconnectedError:
            _LOGGER.error(_MSG_ERROR_DISCONNECTED)
            return {}
        except aiohttp.ServerTimeoutError:
            _LOGGER.error(_MSG_ERROR_TIMEOUT)
            return {}
        except Exception as ex:
            _LOGGER.error(ex)
            _LOGGER.debug("here")
            return {}

    async def async_connect(self):
        """Start new connection to and get new auth token"""

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
        elif "error_status" in response:
            error_code = response['error_status']
            if error_code == '3':
                _LOGGER.error(_MSG_ERROR_CREDENTIALS)
            else:
                _LOGGER.error(_MSG_ERROR_UNKNOWN_CODE)
        else:
            _LOGGER.error(_MSG_ERROR_TO_TOKEN)

    async def async_close(self):
        await self._session.close()