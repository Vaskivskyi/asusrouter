"""Dump tools for AsusRouter.

This module contains all needed to dump the raw data from the router
for the following analysis and testing."""

from __future__ import annotations

import asyncio
import json
import os
import zipfile
from datetime import datetime, timezone
from typing import Any

from asusrouter.modules.endpoint import Endpoint


class AsusRouterDump:
    """AsusRouter Dumper."""

    _endpoint: Endpoint
    _datetime: str

    def __init__(
        self, output_folder: str, full_dump: bool = False, archive: bool = True
    ) -> None:
        """Initialize."""

        self.log: dict[str, str] = {}

        self._output_folder = output_folder
        self.full_dump = full_dump
        self.zip = archive

        self._init_datetime = datetime.now(timezone.utc)

        if self.zip:
            self._zipfile = zipfile.ZipFile(
                os.path.join(
                    self._output_folder,
                    f"AsusRouter-{self._init_datetime.isoformat().replace(':', '-')}.zip",
                ),
                "w",
            )
        else:
            # Create subfolder for the dump
            self._output_folder = os.path.join(
                output_folder,
                f"AsusRouter-{self._init_datetime.isoformat().replace(':', '-')}",
            )
            os.makedirs(self._output_folder)

    def __enter__(self):
        """Enter the runtime context related to this object."""

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context and save the log."""

        if self.zip:
            # Write the log data to the zip file
            self._zipfile.writestr("log.json", json.dumps(self.log, default=str))
            self._zipfile.close()
        else:
            log_filename = os.path.join(self._output_folder, "log.json")
            with open(log_filename, "w", encoding="utf-8") as f:
                json.dump(self.log, f, default=str)

    async def dump(
        self,
        endpoint: Endpoint,
        payload: dict[str, Any],
        resp_status: int,
        resp_headers: dict[str, Any],
        resp_content: bytes,
    ):
        """Dump the data."""

        self._endpoint = endpoint
        self._datetime = datetime.now(timezone.utc).isoformat().replace(":", "-")

        self.log[self._datetime] = f"Endpoint.{endpoint.name}"

        # Write the response content to a file
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_content, resp_content)

        # Write the metadata to a file
        metadata = {
            "endpoint": endpoint,
            "payload": payload,
            "resp_status": resp_status,
            "resp_headers": resp_headers,
        }
        await loop.run_in_executor(None, self._write_metadata, metadata)

    def _write_content(self, content: str):
        """Write the content to a file."""

        if self.full_dump:
            filename = f"{self._datetime}-{self._endpoint}.content"
            if self.zip:
                self._zipfile.writestr(filename, content)
            else:
                with open(
                    os.path.join(self._output_folder, filename), "w", encoding="utf-8"
                ) as f:
                    f.write(content)

    def _write_metadata(self, metadata: dict[str, Any]):
        """Write the metadata to a file."""

        if self.full_dump:
            filename = f"{self._datetime}-{self._endpoint}.json"
            if self.zip:
                self._zipfile.writestr(filename, json.dumps(metadata, default=str))
            else:
                with open(
                    os.path.join(self._output_folder, filename), "w", encoding="utf-8"
                ) as f:
                    json.dump(metadata, f, default=str)
