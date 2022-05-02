"""Dataclass module for AsusRouter"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass
class Key:
    """Key class"""

    value : str
    value_to_use : str = ""

    def __str__(self) -> str:
        """Return only `value` as default string"""

        return self.value

    def get(self) -> str:
        """
        Get the proper value
        
        Returns
        -----
        `value_to_use` if exists, `value` otherwise
        """

        if self.value_to_use != "":
            return self.value_to_use

        return self.value


