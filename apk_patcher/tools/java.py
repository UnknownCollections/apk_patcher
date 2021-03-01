import os
import platform
import sys
from abc import ABCMeta, abstractmethod
from functools import cached_property
from subprocess import DEVNULL, Popen
from typing import Any, List, Optional

import requests

from apk_patcher.lib.archive import Archive
from apk_patcher.lib.downloader import Downloader
from apk_patcher.lib.progress import ProgressCallback
from apk_patcher.lib.tool import Tool
from apk_patcher.lib.stream_download import DownloadMiddleware


def java_arch_str() -> str:
    op_sys = str(platform.system()).lower()
    machine = str(platform.machine())
    if op_sys == 'windows':
        arch = 'x64' if sys.maxsize > 2 ** 32 else 'x86-32'
    elif op_sys == 'linux':
        if machine.startswith('arm'):
            arch = 'arm'
        elif machine == 'aarch64':
            arch = 'aarch64'
        else:
            arch = 'x64'
    elif op_sys == 'darwin':
        op_sys = 'mac'
        arch = 'x64'
    else:
        raise Exception(f'Unsupported platform: {platform.platform()}')
    return f'{arch}_{op_sys}'


class JavaBase(Downloader, metaclass=ABCMeta):
    UNWANTED_MIME_TYPES = [
        'application/x-msi',
        'application/octet-stream',
        'application/json',
        'text/plain'
    ]  # .msi, .pkg, .json, .txt

    @property
    @abstractmethod
    def env(self) -> str:
        raise NotImplementedError()

    @cached_property
    def metadata(self) -> Downloader.Metadata:
        if self.version == 'latest':
            url = f'https://api.github.com/repos/AdoptOpenJDK/openjdk8-binaries/releases/latest'
        else:
            url = f'https://api.github.com/repos/AdoptOpenJDK/openjdk8-binaries/releases/tags/{self.version}'
        resp = requests.get(url)
        self.check_response(resp)
        metadata = resp.json()
        for asset in metadata['assets']:
            if asset['name'].startswith(f'OpenJDK8U-{self.env}_{java_arch_str()}') and asset['content_type'] not in self.UNWANTED_MIME_TYPES:
                return Downloader.Metadata(
                    name=asset['name'],
                    version=metadata['tag_name'],
                    url=asset['browser_download_url'],
                    content_type=asset['content_type'],
                    size=asset['size'],
                    hash=None
                )
        raise Exception(f'Unable to get metadata for {self.env}, missing asset from latest github release')

    @property
    def target_file_name(self) -> str:
        return self.metadata.name

    @property
    def latest_version(self) -> str:
        return self.metadata.version

    @property
    def download_url(self) -> str:
        return self.metadata.url

    @property
    def download_size(self) -> Optional[int]:
        return self.metadata.size

    @property
    def download_middleware(self) -> Optional[DownloadMiddleware]:
        return None

    def is_download_valid(self) -> bool:
        if self.version == 'system':
            return True
        return os.path.exists(self.file_path) and os.path.getsize(self.file_path) == self.download_size

    def download(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        super(JavaBase, self).download(on_progress, progress_user_var)
        Archive(self.file_path).extract_all(self.version_folder, on_progress, progress_user_var)

    def exec(self, binary: str, args: Optional[List[str]] = None, **kwargs) -> Popen:
        if self.version != 'system':
            binary = os.path.join(self.version_folder, 'bin', binary)
        if platform.system() == 'Windows':
            binary = f'{binary}.exe'
        return Popen(args=[binary, *args], **kwargs)


class JRE(JavaBase):
    @property
    def env(self) -> str:
        return 'jre'

    def test_download(self):
        proc = self.exec('java', ['-version'], stdout=DEVNULL, stderr=DEVNULL)
        return proc.wait() == 0


class JDK(JavaBase):
    @property
    def env(self) -> str:
        return 'jdk'

    def test_download(self):
        proc = self.exec('javac', ['-version'], stdout=DEVNULL, stderr=DEVNULL)
        return proc.wait() == 0


class Java(Tool):
    runtime: JRE
    dev: JDK

    def __init__(self, jre_working_dir: str, jdk_working_dir: str, version: str = 'latest'):
        self.runtime = JRE(jre_working_dir, version)
        self.dev = JDK(jdk_working_dir, version)

    def is_ready(self) -> bool:
        return self.runtime.is_ready() and self.dev.is_ready()

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        self.runtime.download(on_progress, progress_user_var)
        self.dev.download(on_progress, progress_user_var)
