[![GitHub Release](https://img.shields.io/github/release/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=blue)](https://github.com/Vaskivskyi/asusrouter/releases) [![License](https://img.shields.io/github/license/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)](LICENSE)<br/>
![Downloads](https://img.shields.io/pypi/dm/asusrouter?style=for-the-badge&color=blue) ![Commit activity](https://img.shields.io/github/commit-activity/m/vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://asusrouter.vaskivskyi.com/BuyMeACoffee.png" alt="Buy Me A Coffee" style="height: 28px !important;" align="right" /></a>

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
                    cache_time = 5)                     #optional
```

## Supported devices

AsusRouter supports virtually every AsusWRT-powered device.

### WiFi 7 | 802.11be
|Model|Status|Tested firmware|Find it on Amazon[^amazon]|
|---|---|---|---|
|[GT-BE98](https://asusrouter.vaskivskyi.com/devices/GT-BE98.html)|💛 Expected to work||<a href="https://amzn.to/3vGztgz" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-BE96U](https://asusrouter.vaskivskyi.com/devices/RT-BE96U.html)|💛 Expected to work||<a href="https://amzn.to/3vJu8oD" rel="nofollow sponsored" target="_blank">find it</a>|

### WiFi 6e | 802.11axe
|Model|Status|Tested firmware|Find it on Amazon[^amazon]|
|---|---|---|---|
|[GT-AXE11000](https://asusrouter.vaskivskyi.com/devices/GT-AXE11000.html)|💛 Expected to work||<a href="https://amzn.to/3Gotj9R" rel="nofollow sponsored" target="_blank">find it</a>|
|[GT-AXE16000](https://asusrouter.vaskivskyi.com/devices/GT-AXE16000.html)|💚 Confirmed|Stock:<li>`3.0.0.4.388_21617-g1288c22`</li>|<a href="https://amzn.to/3vObLyZ" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AXE7800](https://asusrouter.vaskivskyi.com/devices/RT-AXE7800.html)|💛 Expected to work||<a href="https://amzn.to/3jUr2LU" rel="nofollow sponsored" target="_blank">find it</a>|
|[ZenWiFi Pro ET12](https://asusrouter.vaskivskyi.com/devices/ZenWiFiProET12.html)|💛 Expected to work||<a href="https://amzn.to/3GTz68P" rel="nofollow sponsored" target="_blank">find it</a>|

### WiFi 6 | 802.11ax
|Model|Status|Tested firmware|Find it on Amazon[^amazon]|
|---|---|---|---|
|[DSL-AX82U](https://asusrouter.vaskivskyi.com/devices/DSL-AX82U.html)|💚 Confirmed|Merlin:<li>`386.07_0-gnuton0_beta2`</li>|<a href="https://amzn.to/3G87vyR" rel="nofollow sponsored" target="_blank">find it</a>|
|[GT-AX11000](https://asusrouter.vaskivskyi.com/devices/GT-AX11000.html)|💚 Confirmed|Merlin:<li>`386.7_2`</li>|<a href="https://amzn.to/3WDzOMT" rel="nofollow sponsored" target="_blank">find it</a>|
|[GT-AX11000 Pro](https://asusrouter.vaskivskyi.com/devices/GT-AX11000Pro.html)|💛 Expected to work||<a href="https://amzn.to/3VUNbHl" rel="nofollow sponsored" target="_blank">find it</a>|
|[GT-AX6000](https://asusrouter.vaskivskyi.com/devices/GT-AX6000.html)|💛 Expected to work||<a href="https://amzn.to/3GrKHKG" rel="nofollow sponsored" target="_blank">find it</a>|
|[GT6](https://asusrouter.vaskivskyi.com/devices/GT6.html)|💛 Expected to work||<a href="https://amzn.to/3GmPCfR" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX55](https://asusrouter.vaskivskyi.com/devices/RT-AX55.html)|💚 Confirmed|Stock:<li>`3.0.0.4.386_50410`</li>|<a href="https://amzn.to/3Z2ath5" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX56U](https://asusrouter.vaskivskyi.com/devices/RT-AX56U.html)|💚 Confirmed|Merlin:<li>`386.7_2`</li>|<a href="https://amzn.to/3vrIeuz" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX57](https://asusrouter.vaskivskyi.com/devices/RT-AX57.html)|💛 Expected to work||<a href="https://amzn.to/3IWnZNx" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX58U](https://asusrouter.vaskivskyi.com/devices/RT-AX58U.html)|💚 Confirmed|Stock:<li>`386_49674`</li>Merlin:<li>`386.7_2`</li><li>`388.1_0`</li>|<a href="https://amzn.to/3jHri0L" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX59U](https://asusrouter.vaskivskyi.com/devices/RT-AX59U.html)|💛 Expected to work||<a href="https://amzn.to/3CVCVYO" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX68U](https://asusrouter.vaskivskyi.com/devices/RT-AX68U.html)|💚 Confirmed||<a href="https://amzn.to/3WzRwk5" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX82U](https://asusrouter.vaskivskyi.com/devices/RT-AX82U.html)|💚 Confirmed|Stock:<li>`386_48664`</li><li>`386.49674`</li>|<a href="https://amzn.to/3Gv2Bxi" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX86S](https://asusrouter.vaskivskyi.com/devices/RT-AX86S.html)|💚 Confirmed|Stock:<li>`386_49447`</li>|<a href="https://amzn.to/3GuKac5" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX86U](https://asusrouter.vaskivskyi.com/devices/RT-AX86U.html)|💚 Confirmed|Stock:<li>`386_46061`</li><li>`386_48260`</li>Merlin:<li>`386.7_2`</li>|<a href="https://amzn.to/3WCBcPO" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX86U Pro](https://asusrouter.vaskivskyi.com/devices/RT-AX86UPro.html)|💛 Expected to work||<a href="https://amzn.to/3ZDM41T" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX88U](https://asusrouter.vaskivskyi.com/devices/RT-AX88U.html)|💚 Confirmed|Stock:<li>`386_45934`</li><li>`386_48631`</li>Merlin:<li>`386.5_2`</li><li>`386.8_0`</li><li>`388.1_0`</li>|<a href="https://amzn.to/3i2VfYu" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX88U Pro](https://asusrouter.vaskivskyi.com/devices/RT-AX88UPro.html)|💛 Expected to work||<a href="https://amzn.to/3QNDpFZ" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX89X](https://asusrouter.vaskivskyi.com/devices/RT-AX89X.html)|💚 Confirmed||<a href="https://amzn.to/3i55b3S" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AX92U](https://asusrouter.vaskivskyi.com/devices/RT-AX92U.html)|💚 Confirmed|Stock:<li>`386_46061`</li>|<a href="https://amzn.to/3jJJgzt" rel="nofollow sponsored" target="_blank">find it</a>|
|[TUF-AX4200](https://asusrouter.vaskivskyi.com/devices/TUF-AX4200.html)|💛 Expected to work||<a href="https://amzn.to/3kexPjC" rel="nofollow sponsored" target="_blank">find it</a>|
|[TUF-AX5400](https://asusrouter.vaskivskyi.com/devices/TUF-AX5400.html)|💚 Confirmed|Stock:<li>`3.0.0.4.388_21224-g702a50f`</li>|<a href="https://amzn.to/3hXgzyQ" rel="nofollow sponsored" target="_blank">find it</a>|
|[TUF-AX6000](https://asusrouter.vaskivskyi.com/devices/TUF-AX6000.html)|💛 Expected to work||<a href="https://amzn.to/3CXqxaG" rel="nofollow sponsored" target="_blank">find it</a>|
|[ZenWiFi AX (XT8)](https://asusrouter.vaskivskyi.com/devices/ZenWiFiAX(XT8).html)|💚 Confirmed|Stock:<li>`386_48706`</li>Merlin:<li>`386.7_2-gnuton1`</li>|<a href="https://amzn.to/3GuvY2L" rel="nofollow sponsored" target="_blank">find it</a>|
|[ZenWiFi AX Mini (XD4)](https://asusrouter.vaskivskyi.com/devices/ZenWiFiAXMini(XD4).html)|💚 Confirmed|Stock:<li>`386_48790`</li><li>`386_49599`</li>|<a href="https://amzn.to/3hYGuGl" rel="nofollow sponsored" target="_blank">find it</a>|
|[ZenWiFi Pro XT12](https://asusrouter.vaskivskyi.com/devices/ZenWiFiProXT12.html)|💚 Confirmed||<a href="https://amzn.to/3im6UC5" rel="nofollow sponsored" target="_blank">find it</a>|

### WiFi 5 | 802.11ac
|Model|Status|Tested firmware|Find it on Amazon[^amazon]|
|---|---|---|---|
|[4G-AC55U](https://asusrouter.vaskivskyi.com/devices/4G-AC55U.html)|💚 Confirmed||<a href="https://amzn.to/3jIWQDu" rel="nofollow sponsored" target="_blank">find it</a>|
|[DSL-AC68U](https://asusrouter.vaskivskyi.com/devices/DSL-AC68U.html)|💚 Confirmed|Stock:<li>`386_47534`</li>Merlin:<li>`386.4-gnuton2`</li><li>`386.7_2-gnuton1`</li>|<a href="https://amzn.to/3Z5k32H" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC51U](https://asusrouter.vaskivskyi.com/devices/RT-AC51U.html)|💚 Confirmed|Stock:<li>`380_8591`</li>|<a href="https://amzn.to/3WMy2sq" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC52U B1](https://asusrouter.vaskivskyi.com/devices/RT-AC52UB1.html)|💚 Confirmed||<a href="https://amzn.to/3QcrCkk" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC5300](https://asusrouter.vaskivskyi.com/devices/RT-AC5300.html)|💚 Confirmed|Merlin:<li>`386.7_2`</li>|<a href="https://amzn.to/3ZcJQpY" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC57U V3](https://asusrouter.vaskivskyi.com/devices/RT-AC57UV3.html)|💚 Confirmed|Stock:<li>`386_21649`</li>|<a href="https://amzn.to/3VAxDbx" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC58U](https://asusrouter.vaskivskyi.com/devices/RT-AC58U.html)|💚 Confirmed||<a href="https://amzn.to/3G98Mpl" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC66U](https://asusrouter.vaskivskyi.com/devices/RT-AC66U.html)|💚 Confirmed|Merlin:<li>`380.70_0`</li>|<a href="https://amzn.to/3WTtTD8" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC66U B1](https://asusrouter.vaskivskyi.com/devices/RT-AC66UB1.html)|💚 Confirmed||<a href="https://amzn.to/3vtZ4Jm" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC68U](https://asusrouter.vaskivskyi.com/devices/RT-AC68U.html)|💚 Confirmed|Stock:<li>`3.0.0.4.386_49703`</li>Merlin:<li>`386.5_2`</li><li>`386.7_0`</li>|<a href="https://amzn.to/3i6dQTE" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC86U](https://asusrouter.vaskivskyi.com/devices/RT-AC86U.html)|💚 Confirmed|Stock:<li>`386_48260`</li>Merlin:<li>`386.7_0`</li><li>`386.7_2`</li>|<a href="https://amzn.to/3CbRarK" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC87U](https://asusrouter.vaskivskyi.com/devices/RT-AC87U.html)|💚 Confirmed|Merlin:<li>`384.13_10`</li>|<a href="https://amzn.to/3i4sUkE" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-AC88U](https://asusrouter.vaskivskyi.com/devices/RT-AC88U.html)|💚 Confirmed|Merlin:<li>`386.7_beta1`</li>|<a href="https://amzn.to/3FYRYBy" rel="nofollow sponsored" target="_blank">find it</a>|
|[RT-ACRH17](https://asusrouter.vaskivskyi.com/devices/RT-ACRH17.html)|💚 Confirmed|Stock:<li>`382.52517`</li>|<a href="https://amzn.to/3i6dWL0" rel="nofollow sponsored" target="_blank">find it</a>|

### WiFi 4 | 802.11n
|Model|Status|Tested firmware|Find it on Amazon[^amazon]|
|---|---|---|---|
|[RT-N66U](https://asusrouter.vaskivskyi.com/devices/RT-N66U.html)|💚 Confirmed||<a href="https://amzn.to/3i7eP5Z" rel="nofollow sponsored" target="_blank">find it</a>|

## Support the library

### Issues and Pull requests

If you have found an issue working with the library or just want to ask for a new feature, please fill in a new [issue](https://github.com/Vaskivskyi/asusrouter/issues).

You are also welcome to submit [pull requests](https://github.com/Vaskivskyi/asusrouter/pulls) to the repository!

### Check it with your device

Testing the library with different devices would help a lot in the development process. Unfortunately, currently, I have only one device available, so your help would be much appreciated.

### Other support

This library is a free-time project. If you like it, you can support me by buying a coffee.

<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://asusrouter.vaskivskyi.com/BuyMeACoffee.png" alt="Buy Me A Coffee" style="height: 60px !important;"></a>

[^amazon]: As an Amazon Associate I earn from qualifying purchases. Not like I ever got anything yet (:
