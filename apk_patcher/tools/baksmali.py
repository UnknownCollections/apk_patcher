import os
import re
from functools import cached_property
from subprocess import DEVNULL, PIPE, Popen, STDOUT
from typing import List, Optional

import requests

from apk_patcher.lib.downloader import Downloader
from apk_patcher.lib.stream_download import DownloadMiddleware
from apk_patcher.tools.java import Java

class MyTool(Downloader):
    @property
    def target_file_name(self) -> str:
        pass

    @property
    def latest_version(self) -> str:
        pass

    @property
    def download_url(self) -> str:
        pass

    @property
    def download_size(self) -> Optional[int]:
        pass

    @property
    def download_middleware(self) -> Optional[DownloadMiddleware]:
        pass

    def is_download_valid(self) -> bool:
        pass

    def test_download(self):
        pass


class Baksmali(Downloader):
    RE_PARSE_VERSION = re.compile(r'^baksmali-(\d+.\d+.\d+)\.jar$')

    java: Java

    def __init__(self, java: Java, working_dir: str, version: str = 'latest'):
        super().__init__(working_dir, version)
        self.java = java

    @cached_property
    def metadata(self) -> Downloader.Metadata:
        resp = requests.get('https://api.bitbucket.org/2.0/repositories/JesusFreke/smali/downloads/')
        self.check_response(resp)
        data = resp.json()
        if 'values' not in data or len(data['values']) == 0:
            raise Exception('Unable to get metadata for baksmali downloads')
        for value in data['values']:
            if value['name'].startswith('baksmali'):
                return Downloader.Metadata(
                    name=value['name'],
                    url=value['links']['self']['href'],
                    version=self.RE_PARSE_VERSION.fullmatch(value['name']).group(1),
                    content_type=None,
                    size=value['size'],
                    hash=None
                )

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
        return os.path.exists(self.file_path) and os.path.getsize(self.file_path) == self.download_size

    def test_download(self):
        proc = self.java.runtime.exec('java', ['-jar', self.file_path, '--version'], stdout=DEVNULL, stderr=DEVNULL)
        if proc.wait() != 0:
            raise Exception(f'Error testing {self.target_file_name}: {proc.returncode}')

    def disassemble(self, dex_file_path: str, output_folder_path: str, options: Optional[List[str]] = None) -> Popen:
        cmd_line = [
            '-jar', self.file_path,
            'disassemble', '--output', output_folder_path
        ]
        if options is not None:
            cmd_line.extend(options)
        cmd_line.append(dex_file_path)
        return self.java.runtime.exec('java', cmd_line, stdout=PIPE, stderr=STDOUT)
