"""Tests for asusrouter.modules.ports.common."""

from __future__ import annotations

import logging

import pytest

from asusrouter.modules.ports import common


class TestWarnUnknownPort:
    """Tests for warn_unknown_port."""

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        """Clear the reported-values cache before each test."""

        common._reported_unknown_ports.clear()

    def test_warns_on_first_occurrence(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A new unknown value is logged once."""

        with caplog.at_level(logging.WARNING, logger=common._LOGGER.name):
            common.warn_unknown_port("ZZ9")

        assert sum("ZZ9" in r.getMessage() for r in caplog.records) == 1

    def test_does_not_repeat_same_value(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The same value is logged only once across calls."""

        with caplog.at_level(logging.WARNING, logger=common._LOGGER.name):
            common.warn_unknown_port("ZZ9")
            common.warn_unknown_port("ZZ9")

        assert sum("ZZ9" in r.getMessage() for r in caplog.records) == 1

    def test_warns_each_distinct_value(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Distinct unknown values are each logged once."""

        with caplog.at_level(logging.WARNING, logger=common._LOGGER.name):
            common.warn_unknown_port("ZZ9")
            common.warn_unknown_port("YY8")

        messages = [r.getMessage() for r in caplog.records]
        assert sum("ZZ9" in m for m in messages) == 1
        assert sum("YY8" in m for m in messages) == 1
