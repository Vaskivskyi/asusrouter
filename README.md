[![GitHub Release](https://img.shields.io/github/release/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=blue)](https://github.com/Vaskivskyi/asusrouter/releases) [![License](https://img.shields.io/github/license/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)](LICENSE)

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

802.11 AC models:
`RT-AC66U`, `RT-AC86U`, `RT-ACRH13`

802.11 AX models:
`RT-AX55`,`RT-AX58U`, `RT-AX68U`, `RT-AX86U`, `RT-AX88U`, `RT-AX89X`, `RT-AX92U`, `ZenWiFi AX (XT8)`

## Support the library

### Issues and Pull requests

If you have found an issue working with the library or just want to ask for a new feature, please fill in a new [issue](https://github.com/Vaskivskyi/asusrouter/issues).

You are also welcome to submit [pull requests](https://github.com/Vaskivskyi/asusrouter/pulls) to the repository!

### Check it with your device

Testing the library with different devices would help a lot in the development process. Unfortunately, currently, I have only one device available, so your help would be much appreciated.

### Other support

This library is a free-time project. If you like it, you can support me by buying a coffee.

<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 40px !important;"></a>


