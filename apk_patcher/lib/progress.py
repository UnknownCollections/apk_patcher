from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, NewType, Optional


class ProgressStage(Enum):
    START = 1
    PROGRESS = 2
    STOP = 3
    RESET = 4


class ProgressType(Enum):
    DEFAULT = 1
    FILE = 2


@dataclass
class ProgressData:
    stage: ProgressStage
    type: ProgressType
    description: str
    current: int
    total: Optional[int]
    delta: int


class ProgressCancelled(Exception):
    pass


ProgressCallback = NewType('ProgressCallback', Callable[[Optional[Any], ProgressData], bool])
"""
    ProgressCallback = (user_var: Any, data: ProgressData) -> bool
    Return False to cancel
"""
