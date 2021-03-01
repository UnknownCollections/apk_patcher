import os
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Type

from cryptography.hazmat.primitives.hashes import HashAlgorithm

from apk_patcher.lib.progress import ProgressCallback
from apk_patcher.lib.tool import Tool
from apk_patcher.lib.util import hash_file


@dataclass
class APKInfo:
    provider: Type['APKProvider']
    package_name: str
    version_name: str
    version_code: int
    sdk_version: int
    available_abi: List[str]
    file_hash: Optional[bytes]
    file_hash_type: Optional[Type[HashAlgorithm]]
    file_size: Optional[int]


class APKProvider(Tool, metaclass=ABCMeta):
    COMMON_ABI = ['armeabi-v7a']
    COMMON_MIN_SDK = 21

    @abstractmethod
    def get_apk_info(self, package_name: str, sdk_version: int, available_abi: List[str]) -> APKInfo:
        raise NotImplementedError()

    @abstractmethod
    def download_apk(self, apk_info: APKInfo, output_file_path: str, on_progress: Optional[ProgressCallback],
                     progress_user_var: Optional[Any]):
        raise NotImplementedError()

    @staticmethod
    def is_download_valid(download_path: str, apk_info: APKInfo) -> bool:
        if apk_info.file_hash is not None and apk_info.file_hash_type is not None:
            return hash_file(download_path, apk_info.file_hash_type) == apk_info.file_hash

        if apk_info.file_size is not None:
            return os.path.getsize(download_path) == apk_info.file_size

        raise Exception('unable to validate apk download, no file hash or file size provided')
