"""Dataclass module for AsusRouter"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime

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


@dataclass
class Monitor(dict):
    """
    Monitor class

    In general this is dict with additions

    Properties
    -----
    `active`: bool flag of monitor being active

    `time`: datetime object showing the last time monitor was updated

    `ready`: bool flag if monitor was ever loaded

    Methods
    -----
    `start`: set `active` to True

    `stop`: set `active` to False

    `reset`: set `time` to utcnow()

    `finish`: set `ready` to True
    """

    active : bool = False
    time : datetime | None = None
    ready : bool = False

    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()

    def start(self) -> None:
        """Set to active"""

        self.active = True


    def stop(self) -> None:
        """Set to not-active"""

        self.active = False


    def reset(self) -> None:
        """Reset time to utcnow"""

        self.time = datetime.utcnow()


    def finish(self) -> None:
        """Set ready status to True"""

        self.ready = True


