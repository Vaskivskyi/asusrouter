"""Test AsusRouter with real devices data."""

import importlib
import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from asusrouter import AsusData
from asusrouter.modules.endpoint import (
    Endpoint,
    EndpointControl,
    EndpointService,
    EndpointTools,
    EndpointType,
    process,
    read,
)

# Create a logger
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


class FileExtensions(Enum):
    CONTENT = ".content"
    PYTHON = ".py"


@dataclass
class DataItem:
    """A class used to represent a test item."""

    content: str
    result: Dict[AsusData, Any]
    endpoint: EndpointType
    label: str

    def __repr__(self):
        return self.label


@contextmanager
def log_test_data_loading():
    """Log the start and end of loading test data."""

    _LOGGER.info("Starting to load test data")
    yield
    _LOGGER.info("Finished loading test data")


def load_content_data(device_path: Path, module_name: str) -> str:
    """Load content data from a file."""

    content_file = device_path / f"{module_name}{FileExtensions.CONTENT.value}"
    with content_file.open("r", encoding="utf-8") as f:
        return f.read()


def load_expected_result(device_path: Path, module_name: str) -> Any:
    """Load expected result from a module."""

    result_module = importlib.import_module(
        f".test_data.{'.'.join([device_path.name, module_name])}",
        package="tests",
    )
    return result_module.expected_result


def load_test_item(device_path: Path, module_name: str) -> Optional[DataItem]:
    """Load a single test item."""

    try:
        endpoint_name = re.match(r"(.*)_\d+", module_name).group(1)

        endpoint = None
        for EndpointEnum in [Endpoint, EndpointControl, EndpointService, EndpointTools]:
            try:
                endpoint = EndpointEnum[endpoint_name.upper()]
                break
            except KeyError:
                continue

        if endpoint is None:
            raise ValueError("Failed to load test item ", module_name)

        content_data = load_content_data(device_path, module_name)
        expected_result = load_expected_result(device_path, module_name)

        return DataItem(
            content=content_data,
            result=expected_result,
            endpoint=endpoint,
            label=f"{device_path.name}_{module_name}",
        )
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.error("Failed to load test item %s: %s", module_name, ex)
        return None


def load_test_data() -> list[DataItem]:
    """Load the test data."""

    with log_test_data_loading():
        test_data_path = Path(__file__).resolve().parent / "test_data"
        data = []

        for device_path in test_data_path.iterdir():
            if device_path.is_dir():
                device_test_count = 0
                for content_file in device_path.glob("*.content"):
                    module_name = content_file.stem

                    # Check if both .content and .py files exist
                    if (
                        not (device_path / f"{module_name}.content").exists()
                        or not (device_path / f"{module_name}.py").exists()
                    ):
                        continue

                    item = load_test_item(device_path, module_name)
                    data.append(item)
                    device_test_count += 1

                _LOGGER.info(
                    "Found %s test items for device: %s",
                    device_test_count,
                    device_path.name,
                )

        _LOGGER.info("Total test items found: %s", len(data))
        return data


# Load the test data only once
test_data = load_test_data()

# Create a list of ids for the test data
test_ids = [item.label for item in test_data]


@pytest.fixture(params=test_data, ids=test_ids)
def test_item(request):
    """Yield each item in the test data."""

    return request.param


def test_asusrouter(test_item: DataItem):  # pylint: disable=redefined-outer-name
    """
    Test the asusrouter module with the given test item.

    Args:
        test_item (DataItem): The test item to use for the test.

    Raises:
        AssertionError: If the actual processed data does not match the expected result.
    """

    actual_read = read(test_item.endpoint, test_item.content)
    actual_processed = process(test_item.endpoint, actual_read)

    assert actual_processed == test_item.result, print(actual_processed)
