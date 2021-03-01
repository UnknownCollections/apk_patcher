import os
import shutil
from abc import abstractmethod
from io import SEEK_SET, StringIO
from typing import Optional

from apk_patcher.lib.patch import IncompletePatch, Patch


class SmaliPatch(Patch):
    @property
    @abstractmethod
    def target_file(self) -> str:
        pass

    @property
    @abstractmethod
    def line_start(self) -> str:
        pass

    @property
    @abstractmethod
    def line_end(self) -> Optional[str]:
        pass

    @abstractmethod
    def replace(self, original: str) -> str:
        pass

    def backup_file_path(self, target_file_path: str) -> str:
        return f'{target_file_path}.{type(self).__name__}.backup'

    def apply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, self.target_file)
        backup_file_path = self.backup_file_path(target_file_path)

        if not os.path.exists(target_file_path):
            raise IncompletePatch(type(self).__name__, f'unable to find {os.path.basename(target_file_path)}')

        if not os.path.exists(backup_file_path):
            shutil.copy2(target_file_path, backup_file_path)
        else:
            self.unapply(root_folder_path)

        with open(target_file_path, 'r+') as f:
            start_line_pos = None
            end_line_pos = None
            data = f.read()

            with StringIO(data) as content:
                current_pos = content.tell()
                for line in content:
                    if self.line_start in line:
                        start_line_pos = current_pos
                        break
                    current_pos = content.tell()
                if self.line_end is None:
                    end_line_pos = content.tell()
                else:
                    for line in content:
                        if self.line_end in line:
                            end_line_pos = content.tell()
                            break

            if start_line_pos is None or end_line_pos is None:
                raise IncompletePatch(type(self).__name__, f'unable to locate `{self.line_start}`')

            original_data = data[start_line_pos:end_line_pos]
            data = data[:start_line_pos] + self.replace(original_data) + data[end_line_pos:]
            f.seek(0, SEEK_SET)
            f.write(data)
            f.truncate()

    def unapply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, self.target_file)
        backup_file_path = self.backup_file_path(target_file_path)
        if not os.path.exists(target_file_path) or not os.path.exists(backup_file_path):
            return
        os.remove(target_file_path)
        shutil.copy2(backup_file_path, target_file_path)
