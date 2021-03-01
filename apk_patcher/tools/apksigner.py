from distutils.version import StrictVersion
from subprocess import DEVNULL, PIPE, Popen, STDOUT

import requests

from apk_patcher.lib.googlesource_downloader import GoogleSourceDownloader
from apk_patcher.tools.java import Java


class APKSigner(GoogleSourceDownloader):
    java: Java

    def __init__(self, java: Java, working_dir: str, version: str = 'latest'):
        super().__init__(working_dir, version)
        self.java = java

    @property
    def latest_version(self) -> str:
        resp = requests.get('https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/?format=JSON')
        self.check_response(resp)
        versions = GoogleSourceDownloader.gs_json_loads(resp.text)
        latest_version = sorted(list(versions.keys()), key=StrictVersion)[-1]
        return latest_version

    @property
    def download_url(self) -> str:
        return f'https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/{self.version}/+/refs/heads/master/lib/apksigner.jar?format=TEXT'

    def test_download(self):
        proc = self.java.runtime.exec('java', ['-jar', self.file_path, '--version'], stdout=DEVNULL, stderr=DEVNULL)
        if proc.wait() != 0:
            raise Exception(f'Error testing {self.target_file_name}: {proc.returncode}')

    @property
    def target_file_name(self) -> str:
        return 'apksigner.jar'

    def sign_apk(self, in_apk_file_path: str, out_apk_file_path: str, key_path: str, cert_path: str) -> Popen:
        return self.java.runtime.exec('java', [
            '-jar', self.file_path,
            'sign', '--key', key_path, '--cert', cert_path,
            '--v4-signing-enabled', 'false',
            '--in', in_apk_file_path,
            '--out', out_apk_file_path
        ], stdout=PIPE, stderr=STDOUT)
