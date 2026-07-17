<!-- This file is generated from `readme/` by `scripts/build_readme.py`. Do not edit it directly. -->

[![GitHub Release](https://img.shields.io/github/release/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=blue)](https://github.com/Vaskivskyi/asusrouter/releases) [![License](https://img.shields.io/github/license/Vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)](https://github.com/Vaskivskyi/asusrouter/blob/main/LICENSE)<br/>
![Downloads](https://img.shields.io/pypi/dm/asusrouter?style=for-the-badge&color=blue) ![Commit activity](https://img.shields.io/github/commit-activity/m/vaskivskyi/asusrouter.svg?style=for-the-badge&color=yellow)<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://asusrouter.vaskivskyi.com/BuyMeACoffee.png" alt="Buy Me A Coffee" height="28" align="right" /></a>

<div align=center><img src="https://asusrouter.vaskivskyi.com/logo.svg" width="300px"></div>

## AsusRouter

**AsusRouter** is an API wrapper for communication with ASUSWRT-powered routers using HTTP(S) protocols. The library supports both the stock AsusWRT firmware and AsusWRT-Merlin.

Up till now, it is mostly used for the [custom AsusRouter Home Assistant integration](https://github.com/Vaskivskyi/ha-asusrouter) and from recently by the core Home Assistant AsusWRT integration. But I am always open to making it suitable for any other use.

## Installation

AsusRouter requires Python 3.11 or newer. Installation of the latest release is available from PyPI:

```
pip install asusrouter
```

## Usage

Once installed, you can import the `AsusRouter` class and connect to your device. The example below uses the async context manager, which connects on entry and cleans up on exit. Only `hostname`, `username` and `password` are required.

```python
import asyncio

from asusrouter import AsusRouter
from asusrouter.modules.system_status import ARSystemStatusSourceUniversal


async def main() -> None:
    router = AsusRouter(
        hostname="router.my.address",  # required, both IP and URL supported
        username="admin",              # required
        password="password",           # required
        use_ssl=True,                  # optional
    )

    # Connects on enter, disconnects and closes the session on exit
    async with router:
        # Fetch data from the device
        data = await router.async_fetch_data(ARSystemStatusSourceUniversal)
        print(data)


asyncio.run(main())
```

Each data domain (system status, clients, network, WiFi, ...) exposes its own source object under `asusrouter.modules.*`. Pass one - or a list of them - to `async_fetch_data`.

To change something on the device, build the matching action object and pass it to `async_run_action`. For example, to turn the LED off:

```python
from asusrouter.modules.led import ARLedAction

async with router:
    await router.async_run_action(ARLedAction(state=False))
```

See the [documentation](https://asusrouter.vaskivskyi.com) for the full list of sources and actions.

## Supported devices

AsusRouter supports virtually every AsusWRT-powered device. Each model links to its page; the **find it** links point to Amazon[^amazon].

> [!TIP]  
> Version `388.10` of AsusWRT-Merlin firmware is officially **NOT supported** due to the issues with HTTP daemon crashes. Use versions `>=388.10_2` or `<=388.9_2`.

<details>
<summary><b>WiFi 7 | 802.11be</b> — 13 devices</summary>

**💚 Confirmed:** [GT-BE98](https://asusrouter.vaskivskyi.com/devices/GT-BE98.md) ([find it](https://amzn.to/3vGztgz))

**💛 Expected to work:** [GT-BE19000](https://asusrouter.vaskivskyi.com/devices/GT-BE19000.md) ([find it](https://amzn.to/3yGFU7U)), [GT-BE98 Pro](https://asusrouter.vaskivskyi.com/devices/GT-BE98Pro.md) ([find it](https://amzn.to/3uoSjeR)), [RT-BE58U](https://asusrouter.vaskivskyi.com/devices/RT-BE58U.md) ([find it](https://amzn.to/4bHsdo4)), [RT-BE88U](https://asusrouter.vaskivskyi.com/devices/RT-BE88U.md) ([find it](https://amzn.to/3TAGCKY)), [RT-BE92U](https://asusrouter.vaskivskyi.com/devices/RT-BE92U.md) ([find it](https://amzn.to/4c1E8gg)), [RT-BE96U](https://asusrouter.vaskivskyi.com/devices/RT-BE96U.md) ([find it](https://amzn.to/3vJu8oD)), [TUF-BE3600](https://asusrouter.vaskivskyi.com/devices/TUF-BE3600.md) ([find it](https://amzn.to/3VhHoyt)), [TUF-BE6500](https://asusrouter.vaskivskyi.com/devices/TUF-BE6500.md) ([find it](https://amzn.to/3X3Xltv)), [ZenWiFi BD4](https://asusrouter.vaskivskyi.com/devices/ZenWiFiBD4.md) ([find it](https://amzn.to/3Kfulr1)), [ZenWiFi BQ16](https://asusrouter.vaskivskyi.com/devices/ZenWiFiBQ16.md) ([find it](https://amzn.to/4bgVvdo)), [ZenWiFi BQ16 Pro](https://asusrouter.vaskivskyi.com/devices/ZenWiFiBQ16Pro.md) ([find it](https://amzn.to/3MNcw48)), [ZenWiFi BT10](https://asusrouter.vaskivskyi.com/devices/ZenWiFiBT10.md) ([find it](https://amzn.to/48F5wiB))

</details>

<details>
<summary><b>WiFi 6e | 802.11axe</b> — 6 devices</summary>

**💚 Confirmed:** [GT-AXE16000](https://asusrouter.vaskivskyi.com/devices/GT-AXE16000.md) ([find it](https://amzn.to/3vObLyZ)), [RT-AXE7800](https://asusrouter.vaskivskyi.com/devices/RT-AXE7800.md) ([find it](https://amzn.to/3jUr2LU)), [ZenWiFi ET8](https://asusrouter.vaskivskyi.com/devices/ZenWiFiET8.md) ([find it](https://amzn.to/3Iks0La)), [ZenWiFi Pro ET12](https://asusrouter.vaskivskyi.com/devices/ZenWiFiProET12.md) ([find it](https://amzn.to/3GTz68P))

**💛 Expected to work:** [GT-AXE11000](https://asusrouter.vaskivskyi.com/devices/GT-AXE11000.md) ([find it](https://amzn.to/3Gotj9R)), [ZenWiFi ET9](https://asusrouter.vaskivskyi.com/devices/ZenWiFiET9.md) ([find it](https://amzn.to/3RbMKJa))

</details>

<details>
<summary><b>WiFi 6 | 802.11ax</b> — 40 devices</summary>

**💚 Confirmed:** [DSL-AX82U](https://asusrouter.vaskivskyi.com/devices/DSL-AX82U.md) ([find it](https://amzn.to/3G87vyR)), [GT-AX11000](https://asusrouter.vaskivskyi.com/devices/GT-AX11000.md) ([find it](https://amzn.to/3WDzOMT)), [GT-AX11000 Pro](https://asusrouter.vaskivskyi.com/devices/GT-AX11000Pro.md) ([find it](https://amzn.to/3VUNbHl)), [RP-AX56](https://asusrouter.vaskivskyi.com/devices/RP-AX56.md) ([find it](https://amzn.to/3MpZSY8)), [RT-AX53U](https://asusrouter.vaskivskyi.com/devices/RT-AX53U.md) ([find it](https://amzn.to/49jEgqO)), [RT-AX55](https://asusrouter.vaskivskyi.com/devices/RT-AX55.md) ([find it](https://amzn.to/3Z2ath5)), [RT-AX56U](https://asusrouter.vaskivskyi.com/devices/RT-AX56U.md) ([find it](https://amzn.to/3vrIeuz)), [RT-AX58U](https://asusrouter.vaskivskyi.com/devices/RT-AX58U.md) ([find it](https://amzn.to/3jHri0L)), [RT-AX68U](https://asusrouter.vaskivskyi.com/devices/RT-AX68U.md) ([find it](https://amzn.to/3WzRwk5)), [RT-AX82U](https://asusrouter.vaskivskyi.com/devices/RT-AX82U.md) ([find it](https://amzn.to/3Gv2Bxi)), [RT-AX86S](https://asusrouter.vaskivskyi.com/devices/RT-AX86S.md) ([find it](https://amzn.to/3GuKac5)), [RT-AX86U](https://asusrouter.vaskivskyi.com/devices/RT-AX86U.md) ([find it](https://amzn.to/3WCBcPO)), [RT-AX86U Pro](https://asusrouter.vaskivskyi.com/devices/RT-AX86UPro.md) ([find it](https://amzn.to/3ZDM41T)), [RT-AX88U](https://asusrouter.vaskivskyi.com/devices/RT-AX88U.md) ([find it](https://amzn.to/3i2VfYu)), [RT-AX88U Pro](https://asusrouter.vaskivskyi.com/devices/RT-AX88UPro.md) ([find it](https://amzn.to/3QNDpFZ)), [RT-AX89X](https://asusrouter.vaskivskyi.com/devices/RT-AX89X.md) ([find it](https://amzn.to/3i55b3S)), [RT-AX92U](https://asusrouter.vaskivskyi.com/devices/RT-AX92U.md) ([find it](https://amzn.to/3jJJgzt)), [TUF-AX3000 V2](https://asusrouter.vaskivskyi.com/devices/TUF-AX3000V2.md) ([find it](https://amzn.to/3QzzD4C)), [TUF-AX5400](https://asusrouter.vaskivskyi.com/devices/TUF-AX5400.md) ([find it](https://amzn.to/3hXgzyQ)), [TUF-AX6000](https://asusrouter.vaskivskyi.com/devices/TUF-AX6000.md) ([find it](https://amzn.to/3CXqxaG)), [ZenWiFi AX (XT8)](<https://asusrouter.vaskivskyi.com/devices/ZenWiFiAX(XT8).md>) ([find it](https://amzn.to/3GuvY2L)), [ZenWiFi AX Mini (XD4)](<https://asusrouter.vaskivskyi.com/devices/ZenWiFiAXMini(XD4).md>) ([find it](https://amzn.to/3hYGuGl)), [ZenWiFi Pro XT12](https://asusrouter.vaskivskyi.com/devices/ZenWiFiProXT12.md) ([find it](https://amzn.to/3im6UC5)), [ZenWiFi XD5](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXD5.md) ([find it](https://amzn.to/3YrhgjM)), [ZenWiFi XD6](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXD6.md) ([find it](https://amzn.to/3jW23s4)), [ZenWiFi XD6S](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXD6S.md) ([find it](https://amzn.to/3YMbyIZ)), [ZenWiFi XT9](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXT9.md) ([find it](https://amzn.to/3JZOgLF))

**💛 Expected to work:** [GT-AX6000](https://asusrouter.vaskivskyi.com/devices/GT-AX6000.md) ([find it](https://amzn.to/3GrKHKG)), [GT6](https://asusrouter.vaskivskyi.com/devices/GT6.md) ([find it](https://amzn.to/3GmPCfR)), [RT-AX3000P](https://asusrouter.vaskivskyi.com/devices/RT-AX3000P.md) ([find it](https://amzn.to/3RPa2UO)), [RT-AX52](https://asusrouter.vaskivskyi.com/devices/RT-AX52.md) ([find it](https://amzn.to/40Ph3sO)), [RT-AX5400](https://asusrouter.vaskivskyi.com/devices/RT-AX5400.md) ([find it](https://amzn.to/4aCdvyu)), [RT-AX57](https://asusrouter.vaskivskyi.com/devices/RT-AX57.md) ([find it](https://amzn.to/3IWnZNx)), [RT-AX57 Go](https://asusrouter.vaskivskyi.com/devices/RT-AX57Go.md) ([find it](https://amzn.to/47kE9db)), [RT-AX57M](https://asusrouter.vaskivskyi.com/devices/RT-AX57M.md) ([find it](https://amzn.to/3vbVl6k)), [RT-AX59U](https://asusrouter.vaskivskyi.com/devices/RT-AX59U.md) ([find it](https://amzn.to/3CVCVYO)), [TUF-AX4200](https://asusrouter.vaskivskyi.com/devices/TUF-AX4200.md) ([find it](https://amzn.to/3kexPjC)), [ZenWiFi AX Hybrid (XP4)](<https://asusrouter.vaskivskyi.com/devices/ZenWiFiAXHybrid(XP4).md>) ([find it](https://amzn.to/3Itxnbb)), [ZenWiFi XD4 Plus](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXD4Plus.md) ([find it](https://amzn.to/3XtYOWp)), [ZenWiFi XD4S](https://asusrouter.vaskivskyi.com/devices/ZenWiFiXD4S.md) ([find it](https://amzn.to/3E341xI))

</details>

<details>
<summary><b>WiFi 5 | 802.11ac</b> — 17 devices</summary>

**💚 Confirmed:** [4G-AC55U](https://asusrouter.vaskivskyi.com/devices/4G-AC55U.md) ([find it](https://amzn.to/3jIWQDu)), [BRT-AC828](https://asusrouter.vaskivskyi.com/devices/BRT-AC828.md) ([find it](https://amzn.to/3X2wSL5)), [DSL-AC68U](https://asusrouter.vaskivskyi.com/devices/DSL-AC68U.md) ([find it](https://amzn.to/3Z5k32H)), [RT-AC51U](https://asusrouter.vaskivskyi.com/devices/RT-AC51U.md) ([find it](https://amzn.to/3WMy2sq)), [RT-AC52U B1](https://asusrouter.vaskivskyi.com/devices/RT-AC52UB1.md) ([find it](https://amzn.to/3QcrCkk)), [RT-AC5300](https://asusrouter.vaskivskyi.com/devices/RT-AC5300.md) ([find it](https://amzn.to/3ZcJQpY)), [RT-AC57U V3](https://asusrouter.vaskivskyi.com/devices/RT-AC57UV3.md) ([find it](https://amzn.to/3VAxDbx)), [RT-AC58U](https://asusrouter.vaskivskyi.com/devices/RT-AC58U.md) ([find it](https://amzn.to/3G98Mpl)), [RT-AC66U](https://asusrouter.vaskivskyi.com/devices/RT-AC66U.md) ([find it](https://amzn.to/3WTtTD8)), [RT-AC66U B1](https://asusrouter.vaskivskyi.com/devices/RT-AC66UB1.md) ([find it](https://amzn.to/3vtZ4Jm)), [RT-AC68U](https://asusrouter.vaskivskyi.com/devices/RT-AC68U.md) ([find it](https://amzn.to/3i6dQTE)), [RT-AC85P](https://asusrouter.vaskivskyi.com/devices/RT-AC85P.md) ([find it](https://amzn.to/3kMiDdU)), [RT-AC86U](https://asusrouter.vaskivskyi.com/devices/RT-AC86U.md) ([find it](https://amzn.to/3CbRarK)), [RT-AC87U](https://asusrouter.vaskivskyi.com/devices/RT-AC87U.md) ([find it](https://amzn.to/3i4sUkE)), [RT-AC88U](https://asusrouter.vaskivskyi.com/devices/RT-AC88U.md) ([find it](https://amzn.to/3FYRYBy)), [RT-ACRH17](https://asusrouter.vaskivskyi.com/devices/RT-ACRH17.md) ([find it](https://amzn.to/3i6dWL0))

**💛 Expected to work:** [ZenWiFi AC Mini(CD6)](<https://asusrouter.vaskivskyi.com/devices/ZenWiFiACMini(CD6).md>) ([find it](https://amzn.to/3RU7vrL))

</details>

<details>
<summary><b>WiFi 4 | 802.11n</b> — 1 devices</summary>

**💚 Confirmed:** [RT-N66U](https://asusrouter.vaskivskyi.com/devices/RT-N66U.md) ([find it](https://amzn.to/3i7eP5Z))

</details>

## Support the library

### Issues and Pull requests

If you have found an issue working with the library or just want to ask for a new feature, please fill in a new [issue](https://github.com/Vaskivskyi/asusrouter/issues).

You are also welcome to submit [pull requests](https://github.com/Vaskivskyi/asusrouter/pulls) to the repository!

### Check it with your device

Testing the library with different devices would help a lot in the development process. Unfortunately, currently, I have only one device available, so your help would be much appreciated.

### Other support

This library is a free-time project. If you like it, you can support me by buying a coffee.

<a href="https://www.buymeacoffee.com/vaskivskyi" target="_blank"><img src="https://asusrouter.vaskivskyi.com/BuyMeACoffee.png" alt="Buy Me A Coffee" height="60"></a>

[^amazon]: As an Amazon Associate I earn from qualifying purchases. Not like I ever got anything yet (:
