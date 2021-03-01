import os
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

import requests

from apk_patcher.lib.progress import ProgressCallback
from apk_patcher.lib.tool import Tool
from apk_patcher.lib.stream_download import DownloadMiddleware, stream_download_progress


class Downloader(Tool, metaclass=ABCMeta):
    @dataclass
    class Metadata:
        name: str
        version: str
        url: str
        content_type: Optional[str]
        size: Optional[int]
        hash: Optional[bytes]

    BUFFER_SIZE = 1024 * 1024  # 1mB

    version: str
    version_folder: str
    file_path: str
    working_dir: str

    def __init__(self, working_dir: str, version: str = 'latest'):
        self.working_dir = working_dir
        self.version = version
        if self.version == 'latest':
            self.version = self.latest_version

        self.version_folder = os.path.join(self.working_dir, self.version)
        self.file_path = os.path.join(self.version_folder, self.target_file_name)

    @property
    @abstractmethod
    def target_file_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def latest_version(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def download_url(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def download_size(self) -> Optional[int]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def download_middleware(self) -> Optional[DownloadMiddleware]:
        raise NotImplementedError()

    @abstractmethod
    def is_download_valid(self) -> bool:
        raise NotImplementedError()

    def is_ready(self) -> bool:
        if self.is_download_valid():
            try:
                self.test_download()
                return True
            except Exception:
                pass
        return False

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        self.download(on_progress, progress_user_var)

    def check_response(self, resp: requests.Response):
        if resp.status_code >= 400:
            raise Exception(f'HTTP request failed for {self.target_file_name}: {resp.status_code}\n{resp.request.url}')

    def download(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        """
        :raises Exception: unknown errors
        :raises AlreadyDownloaded: file is already downloaded
        :raises DownloadCancelled: progress callback returns False
        """
        os.makedirs(self.version_folder, 0o755, exist_ok=True)

        stream_download_progress(
            self.download_url,
            self.file_path,
            self.BUFFER_SIZE,
            self.download_size,
            self.download_middleware,
            on_progress,
            progress_user_var
        )

        if not self.is_download_valid():
            os.remove(self.file_path)
            raise Exception(f'\tIncomplete or corrupt download of {self.target_file_name} v{self.version}')

    @abstractmethod
    def test_download(self):
        raise NotImplementedError()


DownloaderType = TypeVar('DownloaderType', bound=Downloader)
