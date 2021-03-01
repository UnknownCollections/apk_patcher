import os
import shutil
from abc import ABCMeta, abstractmethod


class IncompletePatch(Exception):
    def init(self, patch: str, error: str):
        super().__init__(f'{patch}: {error}')


class Patch(metaclass=ABCMeta):
    @abstractmethod
    def config(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def apply(self, root_folder_path: str):
        raise NotImplementedError()

    @abstractmethod
    def unapply(self, root_folder_path: str):
        raise NotImplementedError()

    def __backup_file_path(self, file_path: str) -> str:
        return f'{file_path}.{type(self).__name__}.backup'

    def backup_exists(self, file_path: str) -> bool:
        return os.path.exists(self.__backup_file_path(file_path))

    def backup_file(self, file_path: str):
        if not self.backup_exists(file_path):
            shutil.copy2(file_path, self.__backup_file_path(file_path))

    def restore_file(self, file_path):
        if not self.backup_exists(file_path):
            return
        shutil.copy2(self.__backup_file_path(file_path), file_path)
