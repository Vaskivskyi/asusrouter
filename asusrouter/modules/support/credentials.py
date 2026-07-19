"""Supported login credentials."""

from __future__ import annotations

from asusrouter.modules.support.flag import ARSupportValue
from asusrouter.modules.support.helpers import (
    make_bool_translator,
    make_int_translator,
)

translate_http_username_max_length = make_int_translator(
    ARSupportValue.HTTP_USERNAME_MAX_LENGTH.value
)

translate_http_password_max_length = make_int_translator(
    ARSupportValue.HTTP_PASSWORD_MAX_LENGTH.value
)

# Absent on legacy firmware, which changes the login via nvram apply instead
translate_chpass = make_bool_translator(ARSupportValue.CHPASS.value)

translate_secure_default = make_bool_translator(
    ARSupportValue.SECURE_DEFAULT.value
)
