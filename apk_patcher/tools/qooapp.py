import binascii
import os
from typing import Any, Dict, List, Optional

import requests
from cryptography.hazmat.primitives.hashes import MD5

from apk_patcher.lib.apk_provider import APKInfo, APKProvider
from apk_patcher.lib.progress import ProgressCallback
from apk_patcher.lib.stream_download import stream_download_progress


class QooApp(APKProvider):
    VERSION_STR = '8.1.6'
    VERSION_CODE = 316
    BUFFER_SIZE = 1024 * 1024  # 1mB

    device_id: Optional[str]
    token: Optional[str]

    def __init__(self, device_id: Optional[str] = None, token: Optional[str] = None):
        self.device_id = device_id
        self.token = token

    def is_ready(self) -> bool:
        return self.device_id is not None and self.token is not None

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        if self.device_id is None:
            self.device_id = self.generate_device_id()
        if self.token is None:
            self.token = self.generate_token()

    @staticmethod
    def generate_device_id() -> str:
        return binascii.b2a_hex(os.urandom(8)).decode()

    def build_headers(self) -> Dict[str, Any]:
        return {
            'User-Agent': f'QooApp {self.VERSION_STR}',
            'Device-Id': self.device_id
        }

    def generate_token(self) -> str:
        url = 'https://api.qoo-app.com/v6/users'
        query_params = {
            'version_code': self.VERSION_CODE,
        }
        data_params = {
            'device_id': self.device_id,
            'platform_access_token': self.device_id,
            'type': 4,
            'email': 'null',
            'version_code': self.VERSION_CODE
        }
        token_resp = requests.post(url, params=query_params, data=data_params, headers=self.build_headers())
        if token_resp.status_code >= 400:
            raise Exception(f'Unable to generate QooApp token: {token_resp}')

        return token_resp.json()['token']

    def get_apk_info(self, package_name: str, sdk_version: int, available_abi: List[str]) -> APKInfo:
        url = f'https://api.qoo-app.com/v10/apps/{package_name}'
        query_params = {
            'supported_abis': ','.join(available_abi),
            'sdk_version': sdk_version,
            'version_code': self.VERSION_CODE,
        }
        headers = {
            'X-User-Token': self.token,
            **self.build_headers()
        }
        info_resp = requests.get(url, params=query_params, headers=headers)
        if info_resp.status_code >= 400:
            raise Exception(f'Unable to get info for {package_name}: {info_resp}')

        if 'data' not in info_resp.json():
            raise Exception(f'Unable to get info for {package_name}: {info_resp}')

        data = info_resp.json()['data']

        if 'apk' in data and data['apk'] is not None and data['apk']['dl_compatibility'] is not None:
            raise Exception('apk is not compatible with your selected sdk version and/or abis')

        if not data['is_apk_ready']:
            raise Exception('apk is not available for download')

        if data['apk']['data_pack_needed'] or data['apk']['obb'] is not None:
            raise Exception('split apks are not supported')

        return APKInfo(
            type(self),
            package_name,
            data['apk']['version_name'],
            data['apk']['version_code'],
            sdk_version,
            available_abi,
            file_hash=binascii.unhexlify(data['apk']['base_apk_md5']),
            file_hash_type=MD5,
            file_size=None
        )

    def download_apk(self, apk_info: APKInfo, output_file_path: str,
                     on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        url = f'https://api.qoo-app.com/v6/apps/{apk_info.package_name}/download'
        query_params = {
            'supported_abis': ','.join(apk_info.available_abi),
            'sdk_version': apk_info.sdk_version,
            'version_code': self.VERSION_CODE,
            'base_apk_version': 0
        }

        stream_download_progress(
            url,
            output_file_path,
            self.BUFFER_SIZE,
            None,
            None,
            on_progress,
            progress_user_var,
            params=query_params,
            headers=self.build_headers()
        )
