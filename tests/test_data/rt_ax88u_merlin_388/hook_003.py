"""Result of processing hook_003.content."""

from asusrouter import AsusData
from asusrouter.modules.parental_control import (
    AsusBlockAll,
    AsusParentalControl,
    ParentalControlRule,
)

expected_result = {
    AsusData.PARENTAL_CONTROL: {
        "block_all": AsusBlockAll.OFF,
        "state": AsusParentalControl.ON,
        "rules": {
            "00:00:00:00:00:01": ParentalControlRule(
                mac="00:00:00:00:00:01",
                name="FakeName001",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:02": ParentalControlRule(
                mac="00:00:00:00:00:02",
                name="FakeName002",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:03": ParentalControlRule(
                mac="00:00:00:00:00:03",
                name="FakeName003",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:04": ParentalControlRule(
                mac="00:00:00:00:00:04",
                name="FakeName004",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:05": ParentalControlRule(
                mac="00:00:00:00:00:05",
                name="FakeName005",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:06": ParentalControlRule(
                mac="00:00:00:00:00:06",
                name="FakeName006",
                type="block",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:07": ParentalControlRule(
                mac="00:00:00:00:00:07",
                name="FakeName007",
                type="disable",
                timemap="W03E21000700&#60W04122000800",
            ),
            "00:00:00:00:00:08": ParentalControlRule(
                mac="00:00:00:00:00:08",
                name="FakeName008",
                type="disable",
                timemap="W03E21000700&#60W04122000800",
            ),
        },
    }
}
