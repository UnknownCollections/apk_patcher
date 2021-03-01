import requests

from apk_patcher.lib.googlesource_downloader import GoogleSourceDownloader


class AndroidJar(GoogleSourceDownloader):
    @staticmethod
    def blocked_versions(version) -> bool:
        return version not in ['android-system-29']

    @property
    def latest_version(self) -> str:
        resp = requests.get('https://android.googlesource.com/platform/prebuilts/fullsdk/platforms/?format=JSON')
        self.check_response(resp)
        versions = GoogleSourceDownloader.gs_json_loads(resp.text)
        latest_version = sorted(filter(self.blocked_versions, list(versions.keys())))[-1]
        return latest_version

    @property
    def download_url(self) -> str:
        return f'https://android.googlesource.com/platform/prebuilts/fullsdk/platforms/{self.version}/+/refs/heads/master/android.jar?format=TEXT'

    def test_download(self):
        pass

    @property
    def target_file_name(self) -> str:
        return 'android.jar'
