import binascii
import json
import os
import re
from abc import ABCMeta
from typing import Any, Optional

import requests

from apk_patcher.lib.downloader import Downloader
from apk_patcher.lib.stream_download import DownloadMiddleware, stream_decode_response_base64
from apk_patcher.lib.util import change_url_query_param, git_hash_file


class GoogleSourceDownloader(Downloader, metaclass=ABCMeta):
    RE_PARSE_SIZE = re.compile(r'(\d+)-byte')

    @staticmethod
    def gs_json_loads(text: str) -> Any:
        # Strip first 5 bytes from response, intended
        # See: https://github.com/google/gitiles/issues/22#issuecomment-264333316
        return json.loads(text[5:])

    @property
    def download_size(self) -> Optional[int]:
        page_url = change_url_query_param(self.download_url, 'format', '')
        resp = requests.get(page_url)
        self.check_response(resp)
        match = self.RE_PARSE_SIZE.search(resp.text)
        if match is None:
            raise Exception(f'unable to parse {self.target_file_name} size')
        return int(match.group(1))

    @property
    def download_middleware(self) -> Optional[DownloadMiddleware]:
        return stream_decode_response_base64

    def is_download_valid(self) -> bool:
        if not os.path.exists(self.file_path):
            return False
        metadata_url = change_url_query_param(self.download_url, 'format', 'JSON')
        metadata_resp = requests.get(metadata_url)
        self.check_response(metadata_resp)
        metadata = self.gs_json_loads(metadata_resp.text)
        valid_sha1 = binascii.unhexlify(metadata['id'])

        return git_hash_file(self.file_path) == valid_sha1
