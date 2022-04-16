## AsusRouter

**AsusRouter** is an API wrapper for communication with ASUSWRT-powered routers using HTTP or HTTPS protocols. This version is not final yet and has some issues. Please, consider them.


## Supported features

- **Monitoring data** when `enable_monitor` parameter of `AsusRrouter` is set to `True` (default)
- **Sending commands** to the device when `enable_control` is set to `True` (default is `False`)
- SSL server certificates on the device side (including certificate check on the connection from Trusted Root Certificates or your own specified certificate file)s


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

`AsusRouter` class has 3 monitors to load a large part of useful data from the device. All of them require the `enable_monitor` parameter of `AsusRrouter` to be set to `True`. The following methods can be used:

```python
router.async_monitor_main()

router.async_monitor_nvram()

router.async_monitor_misc()
```

Moreover, some additional methods are also available (that could partially rely on one of the monitors):

```python
router.async_find_interfaces()
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


## Supported devices and firmware

Currently, **AsusRouter** is tested on my only router model. If you wish to help me make it better, feel free to open a [Pull Request](https://github.com/Vaskivskyi/asusrouter/pulls) with your model name and firmware (if everything works well). Chances are much higher that some problems may occur on other devices, so [Issues](https://github.com/Vaskivskyi/asusrouter/issues) are waiting for a new one.


### Devices

|Model|Support level|
|---|---|
|RT-AC66U|Complete|


### Firmware

|Version|Build|Extended|Support level|
|-------|-----|--------|-------------|
|3.0.0.4|382|52287-g798e87f|Complete|

