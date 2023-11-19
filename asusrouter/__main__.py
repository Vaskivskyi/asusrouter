"""Starting point for the AsusRouter."""

from __future__ import annotations

import argparse
import asyncio
import logging

import aiohttp

from asusrouter import AsusRouter, AsusRouterDump, AsusRouterError
from asusrouter.modules.data import AsusData

_LOGGER = logging.getLogger(__name__)


async def _connect_and_dump(args: argparse.Namespace) -> None:
    """Connect to the router and dump the data."""

    _LOGGER.info("Starting dump...")

    with AsusRouterDump(args.output, args.dump, args.zip) as dump:
        async with aiohttp.ClientSession() as session:
            _LOGGER.debug("Created aiohttp session")

            # Create the router
            router = AsusRouter(
                hostname=args.host,
                username=args.username,
                password=args.password,
                use_ssl=args.ssl,
                session=session,
                dumpback=dump.dump,
            )
            _LOGGER.debug("Created router")

            # Connect to the router and gather identity data
            _LOGGER.debug("Connecting to the router...")
            await router.async_connect()

            if not router.connected:
                _LOGGER.error("Failed to connect to the router")
                return

            _LOGGER.debug("Connected and identified")

            _LOGGER.debug("Checking all known data...")

            for datatype in AsusData:
                await router.async_get_data(datatype)

            _LOGGER.debug("Finished checking all known data")

            # Disconnect from the router
            await router.async_disconnect()
            _LOGGER.debug("Disconnected")

    _LOGGER.info("Dump finished. Saved to: %s", args.output)


def main():
    """Run AsusRouter as a program."""

    parser = argparse.ArgumentParser(
        description="AsusRouter package command line interface."
    )
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="The output folder for the log."
    )
    parser.add_argument("--dump", action="store_true", help="Perform a full dump.")
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="The hostname / ip address of the router.",
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        default="admin",
        help="The username for the router. Default: `admin`.",
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default="admin",
        help="The password for the router. Default: `admin`.",
    )
    parser.add_argument(
        "-s",
        "--ssl",
        action="store_true",
        default=False,
        help="Use SSL for the connection.",
    )
    parser.add_argument(
        "-P",
        "--port",
        type=int,
        default=None,
        help="The port to connect to. Only when using non-default settings.\
            Default is 80 for HTTP and 443 for HTTPS.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "--zip", action="store_true", default=False, help="Zip the output."
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    )

    # Connect to the router and dump the data
    try:
        asyncio.run(_connect_and_dump(args))
    except AsusRouterError as ex:
        _LOGGER.error("AsusRouterError: %s", ex)


if __name__ == "__main__":
    main()
