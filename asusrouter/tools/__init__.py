"""Tools module"""


def get_enum_key_by_value(enum, value, default=None):
    """Get the enum key by value"""

    for key, enum_value in enum.__members__.items():
        if enum_value.value == value:
            return enum[key]

    return default
