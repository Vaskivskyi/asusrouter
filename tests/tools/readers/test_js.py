"""Tests for the JS-variable readers."""

from __future__ import annotations

from typing import Any

import pytest

from asusrouter.tools.readers.js import read_js_section, read_js_variables


@pytest.mark.parametrize(
    ("data", "key", "expected"),
    [
        ({"a": [{"x": 1}]}, "a", {"x": 1}),
        ({"a": [[1, 2]]}, "a", [1, 2]),
        ({"a": []}, "a", None),
        ({"a": "x"}, "a", None),
        ({}, "a", None),
        ("not-a-dict", "a", None),
    ],
    ids=["dict", "list", "empty", "not_list", "absent", "not_dict"],
)
def test_read_js_section(data: Any, key: str, expected: Any) -> None:
    """The first element of a list-cover section is returned, else None."""

    assert read_js_section(data, key) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        # JS from the active temperature sensors
        (
            'curr_coreTmp_wl0_raw = "44&deg;C";',
            {"curr_coreTmp_wl0_raw": "44&deg;C"},
        ),
        # JS from the disabled temperature sensors
        (
            'curr_coreTmp_wl2_raw = "<i>disabled</i>";',
            {"curr_coreTmp_wl2_raw": "<i>disabled</i>"},
        ),
        # JS from the VPN
        ('vpn_client1_status = "None";', {"vpn_client1_status": "None"}),
        # JSON variables
        (
            "get_onboardinglist = [{}][0];",
            {"get_onboardinglist": [{}]},
        ),
        # Value with array index, fallback to string
        ("arr = value[0];", {"arr": "value"}),
        # Quoted string, not valid JSON or Python literal
        ("foo = 'bar';", {"foo": "bar"}),
        ('baz = "qux";', {"baz": "qux"}),
        # Unquoted string, not valid JSON or Python literal
        ("plain = not_json;", {"plain": "not_json"}),
        # Extra quotes
        ('extra = ""quoted"";', {"extra": '"quoted"'}),
        # Multi-line variable
        (
            (
                "multi_line = {\n"
                '    "key1": "value1",\n'
                "    \n"
                '    "key2": "value2"\n'
                "};"
            ),
            {
                "multi_line": {
                    "key1": "value1",
                    "key2": "value2",
                }
            },
        ),
        (
            ('if (true) {\n    conditional = "value";\n};'),
            {"conditional": "value"},
        ),
        # Weird formatting
        (("something var=42;"), {"var": 42}),
        (("something var='4;2';"), {"var": "4;2"}),
        (('var="val42";'), {"var": "val42"}),
        (('var="val;42";'), {"var": "val;42"}),
        (('if(True){var="val42";}'), {"var": "val42"}),
        ('if(True){ var="value;amp"; }', {"var": "value;amp"}),
        (
            ('if(True){var="val;42";}'),
            {"var": "val;42"},
        ),
        # Other cases
        ('var="val\\"42";', {"var": 'val"42'}),
        ("var=42; // comment", {"var": 42}),
        ('var="foo"; /* block comment */', {"var": "foo"}),
        ("a=1; b=2;", {"a": 1, "b": 2}),
        ('   var =   "foo"   ;   ', {"var": "foo"}),
        ("var=;", {"var": ""}),
        # Non-string values
        ("num=123;", {"num": 123}),
        ("flag=true;", {"flag": True}),
    ],
)
def test_read_js_variables(content: str, expected: dict[str, Any]) -> None:
    """Test read_js_variables."""

    assert read_js_variables(content) == expected
