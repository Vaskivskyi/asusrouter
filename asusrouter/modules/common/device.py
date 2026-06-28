"""Common device module for AsusRouter."""

from __future__ import annotations

from enum import IntEnum

from asusrouter.const import UNKNOWN_MEMBER
from asusrouter.tools.enum import FromIntMixin


class ARDeviceType(FromIntMixin, IntEnum):
    """A device category, by its Asus client-type code."""

    UNKNOWN = UNKNOWN_MEMBER

    # Android
    ANDROID_DEVICE = 31
    ANDROID_PHONE = 9
    ANDROID_TABLET = 20

    # Apple
    APPLE_DEVICE = 32
    APPLE_HOMEPOD = 45
    APPLE_TV = 11
    IMAC = 14
    IPAD = 21
    IPHONE = 10
    MACBOOK = 6

    # ASUS
    ASUS_DEVICE = 42
    ASUS_NOTEBOOK = 38
    ASUS_PAD = 29
    ASUS_SMARTPHONE = 28
    ROG_DEVICE = 15

    # Game consoles
    GAME_CONSOLE = 7
    PLAYSTATION = 74
    PLAYSTATION_4 = 75
    XBOX = 76
    XBOX_ONE = 77

    # Linux
    LINUX_DESKTOP = 72
    LINUX_DEVICE = 22

    # Home devices & smart home
    AIR_CONDITIONER = 49
    AIR_PURIFIER = 54
    AMAZON_ALEXA = 44
    CAMERA = 41
    CHROMECAST = 27
    CLEANING_ROBOT = 61
    DEHUMIDIFIER = 56
    ELECTRIC_KETTLE = 59
    ELECTRIC_POT = 52
    FAN = 55
    GOOGLE_HOME = 43
    HOME_CINEMA = 47
    IP_CAM = 5
    MICROWAVE_OVEN = 53
    REFRIGERATOR = 50
    ROBOT = 71
    SMART_BULB = 60
    SMART_DOOR_LOCK = 67
    SMART_LOCK = 63
    SMART_PLUG = 70
    SMART_TV = 23
    TEMPERATURE_HUMIDITY_SENSOR = 68
    WALL_SWITCH = 66
    WASHING_MACHINE = 57
    WATER_HEATER = 58
    WEIGHT_SCALE = 51

    # PC and electronics
    DESKTOP = 34
    KINDLE = 25
    NAS_SERVER = 4
    NOTEBOOK = 37
    PRINTER = 18
    REPEATER = 24
    ROUTER = 2
    SCANNER = 26
    SD_CARD = 39
    SMARTPHONE = 33
    USB = 40
    WIRELESS_HEADPHONE = 48

    # Wearables
    BODY_SENSOR = 69
    SMART_BRACELET = 64
    WATCH = 65

    # Windows
    WINDOWS_DESKTOP = 1
    WINDOWS_DEVICE = 30
    WINDOWS_NB = 35
    WINDOWS_PHONE = 19

    # Other
    DEVICE = 0
    DLINA = 46
    PAD = 73
    SEISMOGRAPH = 62
    SET_TOP_BOX = 12
