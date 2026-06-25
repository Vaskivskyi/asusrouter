"""Tests for the region module."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.modules.common import region as region_module
from asusrouter.modules.common.region import ARRegion, translate_region


class TestTranslateRegion:
    """Tests for translate_region."""

    def test_known_region(self) -> None:
        """A known territory code resolves to region + area."""

        assert translate_region("US/01") == (ARRegion.US, 1)
        assert translate_region("EU/02") == (ARRegion.EU, 2)

    @pytest.mark.parametrize(
        ("code", "region"),
        [
            ("AA", ARRegion.AA),
            ("CN", ARRegion.CN),
            ("KR", ARRegion.KR),
            ("RU", ARRegion.RU),
            ("TW", ARRegion.TW),
            ("UA", ARRegion.UA),
        ],
    )
    def test_territory_codes(self, code: str, region: ARRegion) -> None:
        """All ASUS territory codes resolve."""

        assert translate_region(f"{code}/01") == (region, 1)

    def test_no_area(self) -> None:
        """A code without an area yields None area."""

        assert translate_region("US") == (ARRegion.US, None)

    @pytest.mark.parametrize(
        "value",
        [None, "", 5],
        ids=["none", "empty", "not_str"],
    )
    def test_unusable(self, value: Any) -> None:
        """Empty or non-string input yields UNKNOWN."""

        assert translate_region(value) == (ARRegion.UNKNOWN, None)

    def test_unknown_warns_once(self) -> None:
        """An unknown code warns exactly once per distinct value."""

        region_module._reported_unknown_regions.clear()

        with pytest.MonkeyPatch.context() as mp:
            warned: list[str] = []
            mp.setattr(
                region_module._LOGGER,
                "warning",
                lambda *args, **kwargs: warned.append(args[1]),
            )
            assert translate_region("ZZ/01") == (ARRegion.UNKNOWN, 1)
            translate_region("ZZ/01")
            translate_region("XX/01")

        assert warned == ["ZZ/01", "XX/01"]
