from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TypeVar

from apk_patcher.lib.progress import ProgressCallback


class Tool(metaclass=ABCMeta):

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        raise NotImplementedError()


ToolType = TypeVar('ToolType', bound=Tool)
