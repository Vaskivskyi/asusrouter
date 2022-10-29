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

This list provides only the models tested by me or other users.

<table>

<tr><th>Group</th><th>Devices</th><th>Firmware</th><th>Limitation</th></tr>

<tr><td>Full support</td><td>

**802.11ax**:<br/>
`DSL-AX82U` (<a href="https://amzn.to/3rXo7md" target="_blank">link*</a>)<br/>
`GT-AX11000` (<a href="https://amzn.to/3VpWgJa" target="_blank">link</a>)<br/>
`RT-AX55` (<a href="https://amzn.to/3MwlBwP" target="_blank">link</a>)<br/>
`RT-AX58U` (<a href="https://amzn.to/3Mrpu6a" target="_blank">link</a>)<br/>
`RT-AX68U` (<a href="https://amzn.to/3rS2jZy" target="_blank">link</a>)<br/>
`RT-AX82U` (<a href="https://amzn.to/3MslCC0" target="_blank">link</a>)<br/>
`RT-AX86U` (<a href="https://amzn.to/3CxEGdk" target="_blank">link</a>)<br/>
`RT-AX86S` (reported as `RT-AX86U`) (<a href="https://amzn.to/3g2YPAK" target="_blank">link</a>)<br/>
`RT-AX88U` (<a href="https://amzn.to/3RVEoTh" target="_blank">link</a>)<br/>
`RT-AX89X` (<a href="https://amzn.to/3fRXXi3" target="_blank">link</a>)<br/>
`RT-AX92U` (<a href="https://amzn.to/3EFz57O" target="_blank">link</a>)<br/>
`TUF-AX5400` (<a href="https://amzn.to/3MtthzR" target="_blank">link</a>)<br/>
`ZenWiFi AX (XT8)` (<a href="https://amzn.to/3Cn8tW4" target="_blank">link</a>)<br/>
`ZenWiFi AX Mini (XD4)` (<a href="https://amzn.to/3CTveTf" target="_blank">link</a>)<br/><br/>
**802.11ac**:<br/>
`4G-AC55U`<br/>
`DSL-AC68U` (<a href="https://amzn.to/3CQ77oq" target="_blank">link</a>)<br/>
`RT-AC5300`<br/>
`RT-AC86U` (<a href="https://amzn.to/3VgJ60S" target="_blank">link</a>)<br/>
`RT-AC88U` (<a href="https://amzn.to/3NhQOEE" target="_blank">link</a>)<br/>
`RT-ACRH13`

</td><td><b>Stock</b>: Any<br/><b>Merlin</b>: Any</td><td></td></tr>

<tr><td>Limited support</td><td>

**802.11ac**:<br/>
`RT-AC51U` (<a href="https://amzn.to/3VooPGF" target="_blank">link</a>)<br/>
`RT-AC66U` (<a href="https://amzn.to/3yBeldp" target="_blank">link</a>)<br/>
`RT-ACRH17` (reported as `RT-AC82U`)<br/><br/>
**802.11n**:<br/>
`RT-N66U`

</td><td><b>Stock</b>: Latest available<b><br/>Merlin</b>: 380.70+</td><td>no LED control</td></tr>

<tr><td>Non-Asus devices</td><td>

**Netgear**:<br/>
`R6300V2`,<br/>
`R7000`

</td><td><b>Merlin</b>: 380.70+</td><td></td></tr>

<tr><td><b>Not supported</b></td><td>

`DSL-AC68VG` (non-compatible FW)

</td><td></td><td></td></tr>

</table>
* As an Amazon Associate I earn from qualifying purchases. Not like I ever got anything yet (:

## Support the library

### Issues and Pull requests

If you have found an issue working with the library or just want to ask for a new feature, please fill in a new [issue](https://github.com/Vaskivskyi/asusrouter/issues).

You are also welcome to submit [pull requests](https://github.com/Vaskivskyi/asusrouter/pulls) to the repository!

### Check it with your device

Testing the library with different devices would help a lot in the development process. Unfortunately, currently, I have only one device available, so your help would be much appreciated.

### Other support

This library is a free-time project. If you like it, you can support me by buying a coffee.

<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;"></a>


