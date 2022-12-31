[![GitHub Release](https://img.shields.io/github/release/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=blue)](https://github.com/Vaskivskyi/asusrouter/releases) [![License](https://img.shields.io/github/license/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)](LICENSE)<br/>
![Downloads](https://img.shields.io/pypi/dm/asusrouter?style=for-the-badge&color=blue) ![Commit activity](https://img.shields.io/github/commit-activity/m/vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 28px !important;" align="right" /></a>

## AsusRouter

**AsusRouter** is an API wrapper for communication with ASUSWRT-powered routers using HTTP(S) protocols. The library supports both the stock AsusWRT firmware and AsusWRT-Merlin.

Up till now, it is only used for the [custom AsusRouter Home Assistant integrartion](https://github.com/Vaskivskyi/ha-asusrouter). But I am always open to making it suitable for any other use.

## Installation

Installation of the latest release is available from PyPI:

```
pip install asusrouter
```

## Usage

Once installed, you can import the `AsusRouter` class from the module. Example shows the default parameters except for `host`, `username` and `password`.

```python
from asusrouter import AsusRouter

router = AsusRouter(host = "router.my.address",         #required - both IP and URL supported
                    username = "admin",                 #required
                    password = "password",              #required
                    port = None,                        #optional - default port would be selected based on use_ssl parameter
                    use_ssl = False,                    #optional
                    cert_check = True,                  #optional
                    cert_path = "",                     #optional
                    cache_time = 5,                     #optional
                    enable_monitor = True,              #optional
                    enable_control = False)             #optional
```

The module has the initialization method to load all the known data (all the monitors and methods from the next section, require `enable_monitor` to be `True`):

```python
router.async_initialize()
```

#### Monitors and additional methods

Most of the values, obtained from the router are grouped in several monitor methods to decrease the amount of data sent between the library and the device. All of them require the `enable_monitor` parameter of `AsusRouter` to be set to `True`.

```python
async_monitor_main()
async_monitor_nvram()
async_monitor_misc()
async_monitor_devices()
```

A detailed description of monitors and monitoring methods is available here (*in work*).

#### Commands

`AsusRouter` class supports sending commands to the device using the `async_command` method. Sending commands requires the `enable_command` parameter of `AsusRrouter` to be set to `True`.

For example, to reboot the device:

```python
# This command will REBOOT your device if connected!
router.async_command(commands = {"rc_service": "reboot"}, action_mode = "apply")
```

Commands to the method should be sent as a `dict` of `command: value`. Please, refer to the Command List (*in work*) for a detailed explanation of the available commands.

## Supported devices

AsusRouter supports virtually every AsusWRT-powered device.

All the devices which were tested (also by the integration users) are explicitly marked as so, as well as the firmware type(s) / version(s).

### Tested

#### 802.11ax

|                                                                                              Model|Stock|Merlin / GNUton|Find it on Amazon[^amazon]|
|---------------------------------------------------------------------------------------------------|-----|---------------|------------------|
|[DSL-AX82U](https://asusrouter.vaskivskyi.com/devices/tested/DSL-AX82U.md)                         | |`386.07_0-gnuton0_beta2`|<a href="https://amzn.to/3G87vyR" rel="nofollow sponsored" target="_blank">link</a>|
|[GT-AX11000](https://asusrouter.vaskivskyi.com/devices/tested/GT-AX11000.md)                       | |`386.7_2`|<a href="https://amzn.to/3WDzOMT" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX55](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX55.md)                             | | |<a href="https://amzn.to/3Z2ath5" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX56U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX56U.md)                           | |`386.7_2`|<a href="https://amzn.to/3vrIeuz" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX58U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX58U.md)                           |`386_49674`|`386.7_2`|<a href="https://amzn.to/3jHri0L" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX68U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX68U.md)                           | | |<a href="https://amzn.to/3WzRwk5" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX82U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX82U.md)                           |`386_48664`, `386.49674`| |<a href="https://amzn.to/3Gv2Bxi" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX86S](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX86S.md)                           |`386_49447`| |<a href="https://amzn.to/3GuKac5" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX86U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX86U.md)                           |`386_46061`, `386_48260`|`386.7_2`|<a href="https://amzn.to/3WCBcPO" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX88U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX88U.md) (testing device)          |`386_45934`, `386_48631`|`386.5_2`|<a href="https://amzn.to/3i2VfYu" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX89X](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX89X.md)                           | | |<a href="https://amzn.to/3i55b3S" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AX92U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AX92U.md)                           |`386_46061`| |<a href="https://amzn.to/3jJJgzt" rel="nofollow sponsored" target="_blank">link</a>|
|[TUF-AX5400](https://asusrouter.vaskivskyi.com/devices/tested/TUF-AX5400.md)                       | | |<a href="https://amzn.to/3hXgzyQ" rel="nofollow sponsored" target="_blank">link</a>|
|[ZenWiFi AX (XT8)](https://asusrouter.vaskivskyi.com/devices/tested/ZenWiFiAX(XT8).md)             |`386_48706`|`386.07_2-gnuton1`|<a href="https://amzn.to/3GuvY2L" rel="nofollow sponsored" target="_blank">link</a>|
|[ZenWiFi AX Mini (XD4)](https://asusrouter.vaskivskyi.com/devices/tested/ZenWiFiAXMini(XD4).md)    |`386_48790`, `386_49599`| |<a href="https://amzn.to/3hYGuGl" rel="nofollow sponsored" target="_blank">link</a>|

#### 802.11ac

|                                                                                Model|Stock|Merlin / GNUton|Find it on Amazon[^amazon]|
|-------------------------------------------------------------------------------------|-----|---------------|------------------|
|[4G-AC55U](https://asusrouter.vaskivskyi.com/devices/tested/4G-AC55U.md)             | | |<a href="https://amzn.to/3jIWQDu" rel="nofollow sponsored" target="_blank">link</a>|
|[DSL-AC68U](https://asusrouter.vaskivskyi.com/devices/tested/DSL-AC68U.md)           |`386_47534`|`386.04-gnuton2`|<a href="https://amzn.to/3Z5k32H" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC51U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC51U.md)             |`380_8591`| |<a href="https://amzn.to/3WMy2sq" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC52U B1](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC52UB1.md)        | | |<a href="https://amzn.to/3QcrCkk" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC5300](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC5300.md)           | |`386.7_2`|<a href="https://amzn.to/3ZcJQpY" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC57U V3](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC57UV3.md)        |`386_21649`| |<a href="https://amzn.to/3VAxDbx" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC58U / RT-ACRH13](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC58U.md) | | |<a href="https://amzn.to/3G98Mpl" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC66R / RT-AC66U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC66U.md)  | |`380.70_0`|<a href="https://amzn.to/3WTtTD8" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC66U B1](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC66UB1.md)        | | |<a href="https://amzn.to/3vtZ4Jm" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC68U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC68U.md)             | |`386.5_2`, `386.7_0`|<a href="https://amzn.to/3i6dQTE" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC86U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC86U.md)             |`386_48260`|`386.7_0`, `386.7_2`|<a href="https://amzn.to/3CbRarK" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC87U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC87U.md)             | |`384.13_10`|<a href="https://amzn.to/3i4sUkE" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-AC88U](https://asusrouter.vaskivskyi.com/devices/tested/RT-AC88U.md)             | |`386.7_beta1`|<a href="https://amzn.to/3FYRYBy" rel="nofollow sponsored" target="_blank">link</a>|
|[RT-ACRH17](https://asusrouter.vaskivskyi.com/devices/tested/RT-ACRH17.md)           |`382.52517`| |<a href="https://amzn.to/3i6dWL0" rel="nofollow sponsored" target="_blank">link</a>|

#### 802.11n

|                                                                  Model|Stock|Merlin / GNUton|Find it on Amazon[^amazon]|
|-----------------------------------------------------------------------|-----|---------------|------------------|
|[RT-N66U](https://asusrouter.vaskivskyi.com/devices/tested/RT-N66U.md) | | |<a href="https://amzn.to/3i7eP5Z" rel="nofollow sponsored" target="_blank">link</a>|

#### Else

**Usage of AsusWRT-Merlin on non-Asus devices is ILLEGAL**
As stated by developers of Merlin ([link](https://www.snbforums.com/threads/announcement-running-asuswrt-merlin-and-forks-on-non-asus-devices-is-illegal.44636/))

|          Model|Merlin / GNUton|
|---------------|---------------|
|Netgear R6300V2|`380.70`|
|Netgear R7000  |`386.2_4`, `380.70_0-X7.9`|

## Support the library

### Issues and Pull requests

If you have found an issue working with the library or just want to ask for a new feature, please fill in a new [issue](https://github.com/Vaskivskyi/asusrouter/issues).

You are also welcome to submit [pull requests](https://github.com/Vaskivskyi/asusrouter/pulls) to the repository!

### Check it with your device

Testing the library with different devices would help a lot in the development process. Unfortunately, currently, I have only one device available, so your help would be much appreciated.

### Other support

This library is a free-time project. If you like it, you can support me by buying a coffee.

<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;"></a>

[^amazon]: As an Amazon Associate I earn from qualifying purchases. Not like I ever got anything yet (:
