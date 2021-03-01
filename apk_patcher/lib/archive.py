import os
import shutil
import tarfile
import zipfile
from enum import Enum
from typing import Any, IO, List, NewType, Optional, Union

from apk_patcher.lib.progress import ProgressCallback, ProgressCancelled, ProgressData, ProgressStage, ProgressType


class UnsupportedArchive(Exception):
    def __init__(self):
        super().__init__('unsupported archive type')


ArchiveType = NewType('ArchiveType', Union[zipfile.ZipFile, tarfile.TarFile])
ArchiveMemberType = NewType('ArchiveMemberType', Union[zipfile.ZipInfo, tarfile.TarInfo])


class Archive:
    class Type(Enum):
        ZIP = 1
        TAR = 2

    type: Type
    file_path: str

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.type = self.get_archive_type()

    def get_archive_type(self):
        if zipfile.is_zipfile(self.file_path):
            return Archive.Type.ZIP
        elif tarfile.is_tarfile(self.file_path):
            return Archive.Type.TAR
        else:
            raise UnsupportedArchive()

    def open_archive(self) -> ArchiveType:
        if self.type == Archive.Type.ZIP:
            return zipfile.ZipFile(self.file_path, 'r')
        elif self.type == Archive.Type.TAR:
            return tarfile.TarFile.open(self.file_path, 'r:*')

    def get_members(self, archive: ArchiveType) -> List[ArchiveMemberType]:
        if self.type == Archive.Type.ZIP:
            return archive.infolist()
        elif self.type == Archive.Type.TAR:
            return archive.getmembers()

    def get_names(self, archive: ArchiveType) -> List[str]:
        if self.type == Archive.Type.ZIP:
            return archive.namelist()
        elif self.type == Archive.Type.TAR:
            return archive.getnames()

    @staticmethod
    def is_archive_wrapped(names: List[str]) -> bool:
        if len(names) < 2:
            return False
        wrapper = names[0]
        for member in names:
            if not member.startswith(wrapper):
                return False
        return True

    def is_member_dir(self, member: ArchiveMemberType) -> bool:
        if self.type == Archive.Type.ZIP:
            return member.is_dir()
        elif self.type == Archive.Type.TAR:
            return member.isdir()

    def get_member_filename(self, member: ArchiveMemberType) -> str:
        if self.type == Archive.Type.ZIP:
            return member.filename
        elif self.type == Archive.Type.TAR:
            return member.name

    def open_member(self, archive: ArchiveType, member: ArchiveMemberType) -> IO[bytes]:
        if self.type == Archive.Type.ZIP:
            return archive.open(member)
        elif self.type == Archive.Type.TAR:
            return archive.extractfile(member)

    def extract_all(self, output_folder_path: str, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        with self.open_archive() as f:
            members = self.get_members(f)
            total_members = len(members)
            if total_members == 0:
                return

            if on_progress is not None:
                desc = f'unpacking {os.path.basename(self.file_path)}'
                progress = ProgressData(ProgressStage.START, ProgressType.DEFAULT, desc, 0, total_members, 0)
                if not on_progress(progress_user_var, progress):
                    raise ProgressCancelled()

            inital_subfolder = self.get_member_filename(members[0]) if self.is_archive_wrapped(self.get_names(f)) else None

            for member in members:
                if self.is_member_dir(member):
                    continue
                if inital_subfolder is not None:
                    extract_file_path = os.path.relpath(self.get_member_filename(member), inital_subfolder)
                else:
                    extract_file_path = self.get_member_filename(member)
                extract_path = os.path.join(output_folder_path, extract_file_path)
                os.makedirs(os.path.dirname(extract_path), exist_ok=True)

                source = self.open_member(f, member)
                if source is None:
                    continue
                with open(extract_path, 'wb') as target:
                    shutil.copyfileobj(source, target)

                if on_progress is not None:
                    # noinspection PyUnboundLocalVariable
                    progress.delta = 1
                    progress.current += 1
                    progress.stage = ProgressStage.PROGRESS
                    if not on_progress(progress_user_var, progress):
                        raise ProgressCancelled()

            if on_progress is not None:
                progress.stage = ProgressStage.STOP
                on_progress(progress_user_var, progress)
