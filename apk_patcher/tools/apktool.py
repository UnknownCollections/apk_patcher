import os
from functools import cached_property
from subprocess import DEVNULL, PIPE, Popen, STDOUT
from typing import List, Optional

import requests

from apk_patcher.lib.downloader import Downloader
from apk_patcher.lib.tool import Tool
from apk_patcher.lib.stream_download import DownloadMiddleware
from apk_patcher.tools.java import Java


class APKTool(Downloader, Tool):
    java: Java

    def __init__(self, java: Java, working_dir: str, version: str = 'latest'):
        super().__init__(working_dir, version)
        self.java = java

    @cached_property
    def metadata(self) -> Downloader.Metadata:
        if self.version == 'latest':
            url = f'https://api.github.com/repos/iBotPeaches/Apktool/releases/latest'
        else:
            url = f'https://api.github.com/repos/iBotPeaches/Apktool/releases/tags/{self.version}'
        resp = requests.get(url)
        self.check_response(resp)
        metadata = resp.json()
        for asset in metadata['assets']:
            if asset['content_type'] == 'application/x-java-archive':
                return Downloader.Metadata(
                    name=asset['name'],
                    version=metadata['tag_name'],
                    url=asset['browser_download_url'],
                    content_type=asset['content_type'],
                    size=asset['size'],
                    hash=None
                )
        raise Exception('Unable to get metadata for apktool, missing jar asset from latest github release')

    @property
    def target_file_name(self) -> str:
        return self.metadata.name

    @cached_property
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
        return os.path.exists(self.file_path) and os.path.getsize(self.file_path) == self.download_size

    def test_download(self):
        proc = self.java.runtime.exec('java', ['-jar', self.file_path, '--version'], stdout=DEVNULL, stderr=DEVNULL)
        if proc.wait() != 0:
            raise Exception(f'Error testing {self.target_file_name}: {proc.returncode}')

    def unpack_apk(self, apk_file_path: str, output_folder_path: str, options: Optional[List[str]] = None) -> Popen:
        cmd_line = [
            '-jar', self.file_path,
            'd', '--output', output_folder_path,
            '--no-debug-info', '--force'
        ]
        if options is not None:
            cmd_line.extend(options)
        cmd_line.append(apk_file_path)
        return self.java.runtime.exec('java', cmd_line, stdout=PIPE, stderr=STDOUT)

    def pack_apk(self, input_folder_path: str, output_apk_path: str, rebuild: bool = False, options: Optional[List[str]] = None) -> Popen:
        cmd_line = [
            '-jar', self.file_path,
            'b', '--output', output_apk_path,
            '--use-aapt2'
        ]
        if rebuild:
            cmd_line.append('--force-all')
        if options is not None:
            cmd_line.extend(options)
        cmd_line.append(input_folder_path)
        return self.java.runtime.exec('java', cmd_line, stdout=PIPE, stderr=STDOUT)
