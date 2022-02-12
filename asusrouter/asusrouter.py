"""AsusRouter module"""

import asyncio
from asyncio import IncompleteReadError
import logging
from asyncio import LimitOverrunError, TimeoutError
from math import floor
import string
from textwrap import indent
import aiohttp
import base64
import json
from datetime import datetime
import urllib.parse
from collections import namedtuple

from asusrouter.connection import Connection

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

DEFAULT_CACHE_TIME = 10
DEFAULT_SLEEP_TIME = 1

INTERFACE_GROUPS = {
    
}

NVRAM_LIST = {
    "DEVICE": [
        "productid",
        "serial_no",
        "label_mac",
        "model",
        "pci/1/1/ATE_Brand",
    ],
    "FIRMWARE": [
        "firmver",
        "buildno",
        "extendno",
    ],
    "FUNCTIONS": [
        "rc_support",
        "ss_support",
    ],
    "INTERFACES": [
        "wans_dualwan",
        "wan_ifnames",
        "wl_ifnames",
        "wl0_vifnames",
        "wl1_vifnames",
        "lan_ifnames",
        "br0_ifnames",
    ],
    "REBOOT": [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time",
    ],
    "WAN": [
        "link_wan",
        "wan0_auxstate_t",
        "wan0_dns",
        "wan0_enable",
        "wan0_expires",
        "wan0_gateway",
        "wan0_gw_ifname",
        "wan0_gw_mac",
        "wan0_hwaddr",
        "wan0_ipaddr",
        "wan0_is_usb_modem_ready",
        "wan0_primary",
        "wan0_proto",
        "wan0_realip_ip",
        "wan0_realip_state",
        "wan0_sbstate_t",
        "wan0_state_t",
        "wan0_upnp_enable",
    ],
    "WAN1": [
        "link_wan1",
        "wan1_auxstate_t",
        "wan1_dns",
        "wan1_enable",
        "wan1_gateway",
        "wan1_gw_ifname",
        "wan1_gw_mac",
        "wan1_hwaddr",
        "wan1_ipaddr",
        "wan1_is_usb_modem_ready",
        "wan1_primary",
        "wan1_proto",
        "wan1_realip_ip",
        "wan1_realip_state",
        "wan1_sbstate_t",
        "wan1_state_t",
        "wan1_upnp_enable",
    ],
    "LAN": [
        "lan_gateway",
        "lan_hwaddr",
        "lan_ifname",
        "lan_ifnames",
        "lan_ipaddr",
        "lan_netmask",
        "lan_proto",
        "lanports"
    ],
    "WLAN0": [
        "wl0_radio",
        "wl0_ssid",
        "wl0_chanspec",
        "wl0_closed",
        "wl0_nmode_x",
        "wl0_bw",
        "wl0_auth_mode_x",
        "wl0_crypto",
        "wl0_wpa_psk",
        "wl0_mfp",
        "wl0_mbo_enable",
        "wl0_country_code",
        "wl0_maclist_x",
        "wl0_macmode",
    ],
    "WLAN1": [
        "wl1_radio",
        "wl1_ssid",
        "wl1_chanspec",
        "wl1_closed",
        "wl1_nmode_x",
        "wl1_bw",
        "wl1_auth_mode_x",
        "wl1_crypto",
        "wl1_wpa_psk",
        "wl1_mfp",
        "wl1_mbo_enable",
        "wl1_country_code",
        "wl1_maclist_x",
        "wl1_macmode",
    ],
    "GWLAN01": [
        "wl0.1_bss_enabled",
        "wl0.1_ssid",
        "wl0.1_auth_mode_x",
        "wl0.1_crypto",
        "wl0.1_key",
        "wl0.1_wpa_psk",
        "wl0.1_lanaccess",
        "wl0.1_expire",
        "wl0.1_expire_tmp",
        "wl0.1_macmode",
        "wl0.1_mbss",
        "wl0.1_sync_mode",
    ],
    "GWLAN02": [
        "wl0.2_bss_enabled",
        "wl0.2_ssid",
        "wl0.2_auth_mode_x",
        "wl0.2_crypto",
        "wl0.2_key",
        "wl0.2_wpa_psk",
        "wl0.2_lanaccess",
        "wl0.2_expire",
        "wl0.2_expire_tmp",
        "wl0.2_macmode",
        "wl0.2_mbss",
        "wl0.2_sync_mode",
    ],
    "GWLAN03": [
        "wl0.3_bss_enabled",
        "wl0.3_ssid",
        "wl0.3_auth_mode_x",
        "wl0.3_crypto",
        "wl0.3_key",
        "wl0.3_wpa_psk",
        "wl0.3_lanaccess",
        "wl0.3_expire",
        "wl0.3_expire_tmp",
        "wl0.3_macmode",
        "wl0.3_mbss",
        "wl0.3_sync_mode",
    ],
    "GWLAN11": [
        "wl1.1_bss_enabled",
        "wl1.1_ssid",
        "wl1.1_auth_mode_x",
        "wl1.1_crypto",
        "wl1.1_key",
        "wl1.1_wpa_psk",
        "wl1.1_lanaccess",
        "wl1.1_expire",
        "wl1.1_expire_tmp",
        "wl1.1_macmode",
        "wl1.1_mbss",
        "wl1.1_sync_mode",
    ],
    "GWLAN12": [
        "wl1.2_bss_enabled",
        "wl1.2_ssid",
        "wl1.2_auth_mode_x",
        "wl1.2_crypto",
        "wl1.2_key",
        "wl1.2_wpa_psk",
        "wl1.2_lanaccess",
        "wl1.2_expire",
        "wl1.2_expire_tmp",
        "wl1.2_macmode",
        "wl1.2_mbss",
        "wl1.2_sync_mode",
    ],
    "GWLAN13": [
        "wl1.3_bss_enabled",
        "wl1.3_ssid",
        "wl1.3_auth_mode_x",
        "wl1.3_crypto",
        "wl1.3_key",
        "wl1.3_wpa_psk",
        "wl1.3_lanaccess",
        "wl1.3_expire",
        "wl1.3_expire_tmp",
        "wl1.3_macmode",
        "wl1.3_mbss",
        "wl1.3_sync_mode",
    ],
}

class AsusRouter:
    """The interface class"""

    def __init__(
        self,
        host,
        username = None,
        password = None,
        cacheNvramTime = 5,
        cacheDeviceTime = 5,
        cacheTime = 3,
        enableMonitor = True,
        enableControl = False):
        """Init"""

        self._device_cpu : list | None = None
        self._device_interfaces : dict | None = None

        self._cacheNvram = None
        self._cacheNvramTime = cacheNvramTime
        self._cacheNvramLast = None
        self._cacheNvramGroups = None

        self._cacheHealth = None
        self._cacheHealthTime = cacheTime
        self._cacheHealthLast = None
        self._cacheHealthRaw = None
        self._cacheHealthRawTime = cacheTime
        self._cacheHealthRawLast = None

        self._cacheNetstat = None
        self._cacheNetstatTime = cacheTime
        self._cacheNetstatLast = None
        self._cacheNetstatRaw = None
        self._cacheNetstatRawTime = cacheTime
        self._cacheNetstatRawLast = None

        self._cacheDevice = None
        self._cacheDeviceTime = cacheDeviceTime
        self._cacheDeviceLast = None
        
        """Connect"""
        self.connection = Connection(host, username, password)

    async def async_compile_request(self, list):
        """"Compile request into one string"""

        data = ""
        if list is not None:
            for item in list:
                data += item
                if item[-1] != ";":
                    data += ";"

        return data

    async def async_compile_request_nvram(self, group):
        """Compile all NVRAM requests for group"""

        data = ""

        if group is not None:
            for item in NVRAM_LIST[group]:
                data += "nvram_get({});".format(item)

        return data

    async def async_hook(self, request):
        """Hook data from device"""

        result = {}

        if request is None:
            return result

        try:
            result = await self.connection.async_run_command("hook={}".format(request))
        except Exception as ex:
            _LOGGER.error(ex)
        
        return result

    async def async_get_health_raw(self, useCache = True):
        """Get CPU, RAM data"""

        healthRaw = {}
        now = datetime.utcnow()

        if (
            useCache
            and self._cacheHealthRawLast
            and self._cacheHealthRawTime > (now - self._cacheHealthRawLast).total_seconds()
        ):
            healthRaw = self._cacheHealthRaw
        else:
            request = await self.async_compile_request(["cpu_usage(appobj)", "memory_usage(appobj)"])
            healthRaw = await self.async_hook(request)

            self._cacheHealthRaw = healthRaw
            self._cacheHealthRawLast = now

        return healthRaw

    async def async_get_health(self, useCache = True):
        """Get CPU, RAM data"""

        health = {}
        now = datetime.utcnow()

        if (
            useCache
            and self._cacheHealthLast
            and self._cacheHealthTime > (now - self._cacheHealthLast).total_seconds()
        ):
            health = self._cacheHealth
        else:
            raw_0 = await self.async_get_health_raw(useCache = False)
            await asyncio.sleep(1)
            raw_1 = await self.async_get_health_raw(useCache = False)
            cpu_usage_0 = raw_0['cpu_usage']
            cpu_usage_1 = raw_1['cpu_usage']
            mem_usage = raw_1['memory_usage']
            for i in range(1,8):
                if (
                    "cpu{}_total".format(i) in cpu_usage_0
                    and "cpu{}_usage".format(i) in cpu_usage_0
                    and "cpu{}_total".format(i) in cpu_usage_1
                    and "cpu{}_usage".format(i) in cpu_usage_1
                ):
                    tmp_usage_0 = int(cpu_usage_0["cpu{}_usage".format(i)])
                    tmp_usage_1 = int(cpu_usage_1["cpu{}_usage".format(i)])
                    tmp_total_0 = int(cpu_usage_0["cpu{}_total".format(i)])
                    tmp_total_1 = int(cpu_usage_1["cpu{}_total".format(i)])
                    cpu_percent = (tmp_usage_1 - tmp_usage_0) / (tmp_total_1 - tmp_total_0) * 100
                    cpu_usage_1["cpu{}_percent".format(i)] = round(cpu_percent, 1)
                else:
                    break
            mem_percent = round(int(mem_usage['mem_used']) / int(mem_usage['mem_total']) * 100, 1)
            mem_usage['mem_percent'] = mem_percent

            health = cpu_usage_1
            health.update(mem_usage)

        return health

    async def async_get_nvram(self, groupList = None, useCache = True):
        """Get the NVRAM values for the specified group list"""

        nvram = {}
        now = datetime.utcnow()

        # If none groups were sent, will return all the known NVRAM values
        if groupList is None:
            groupList = [*NVRAM_LIST]

        # If only one group is sent
        if type(groupList) is not list:
            groupList = [groupList.upper()]

        if (
            useCache
            and self._cacheNvramLast
            and self._cacheNvramGroups
            and all([item in groupList for item in self._cacheNvramGroups])
            and self._cacheNvramTime > (now - self._cacheNvramLast).total_seconds()
        ):
            nvram = self._cacheNvram
        else:
            requests = []
            for group in groupList:
                group = group.upper()
                if group in NVRAM_LIST:
                    request = await self.async_compile_request_nvram(group)
                    requests.append(request)
                else:
                    _LOGGER.debug("There is no {} in known NVRAM groups".format(group))
            
            request = await self.async_compile_request(requests)
            result = await self.async_hook(request)
            for item in result:
                nvram[item] = result[item]

            self._cacheNvram = nvram
            self._cacheNvramGroups = groupList
            self._cacheNvramLast = now

        return nvram

    async def async_get_netstat_raw(self, useCache = True):
        """Get raw network statistics"""

        netstat_raw = {}
        now = datetime.utcnow()
        if (
            useCache
            and self._cacheNetstatRawLast
            and self._cacheNetstatRawTime > (now - self._cacheNetstatRawLast).total_seconds()
        ):
            netstat_raw = self._cacheNetstatRaw
        else:
            try:
                result = await self.async_hook("netdev(appobj);")
                netstat_raw = result['netdev']

                self._cacheNetstatRaw = netstat_raw
                self._cacheNetstatRawLast = now
            except KeyError:
                _LOGGER.error("Empty response on hook")

        return netstat_raw

    async def async_get_netstat(self, useCache = True):
        """Get network statistics"""

        netstat = {}
        now = datetime.utcnow()

        if (
            useCache
            and self._cacheNetstatLast
            and self._cacheNetstatTime > (now - self._cacheNetstatLast).total_seconds()
        ):
            netstat = self._cacheNetstat
        else:
            netstat_0 = await self.async_get_netstat_raw(useCache = False)
            await asyncio.sleep(1)
            netstat_1 = await self.async_get_netstat_raw(useCache = False)

            for item in netstat_1:
                # Traffic values in MB (MiB in reality, but this is how the original software does calculate and label values, so we should keep it consistent)
                value_0 = int(netstat_0[item], base = 16) / 1024 / 1024
                value_1 = int(netstat_1[item], base = 16) / 1024 / 1024
                # Speed in Mb/s
                speed = (value_1 - value_0) * 8
                netstat[item] = round(value_1, 3)
                netstat["{}_speed".format(item)] = round(speed, 3)

            self._cacheNetstat = netstat
            self._cacheNetstatLast = now

        return netstat

    async def async_find_cpu(self):
        """Return available CPU cores"""

        if self._device_cpu is not None:
            return self._device_cpu
        cores = []

        data = await self.async_get_health_raw(useCache = False)
        cpu = data['cpu_usage']
        
        for i in range(1,8):
            if (
                "cpu{}_total".format(i) in cpu
                and "cpu{}_usage".format(i) in cpu
            ):
                cores.append(i)
            else:
                break

        return cores
    
    async def async_find_interfaces(self):
        """Return available interfaces/type dictionary"""
        ports = {}

        data = await self.async_get_nvram("INTERFACES")
        
        if "wan_ifnames" in data:
            values = data['wan_ifnames'].split(" ")
            for item in values:
                ports[item] = "wan"

        if "wl_ifnames" in data:
            values = data['wl_ifnames'].split(" ")
            for item in values:
                ports[item] = "wlan"

        if "wl0_vifnames" in data:
            values = data['wl0_vifnames'].split(" ")
            for item in values:
                ports[item] = "g_wlan_2"
                
        if "wl1_vifnames" in data:
            values = data['wl1_vifnames'].split(" ")
            for item in values:
                ports[item] = "g_wlan_5"

        if "lan_ifnames" in data:
            values = data['lan_ifnames'].split(" ")
            for item in values:
                if not item in ports:
                    ports[item] = "lan"

        return ports