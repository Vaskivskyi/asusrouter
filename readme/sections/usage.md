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
