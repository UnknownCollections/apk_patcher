import math
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from tqdm import tqdm

from apk_patcher.lib.apk_provider import APKInfo, APKProvider
from apk_patcher.lib.certificate import Certificate
from apk_patcher.lib.di import di_class_init
from apk_patcher.lib.patch import Patch
from apk_patcher.lib.progress import ProgressData, ProgressStage, ProgressType
from apk_patcher.lib.tool import ToolType
from apk_patcher.lib.util import dotenv_get_set, print_subprocess_output
from apk_patcher.tools.android_jar import AndroidJar
from apk_patcher.tools.apksigner import APKSigner
from apk_patcher.tools.apktool import APKTool
from apk_patcher.tools.baksmali import Baksmali
from apk_patcher.tools.dx import DX
from apk_patcher.tools.java import Java
from apk_patcher.tools.qooapp import QooApp


@dataclass
class APK:
    info: APKInfo
    file_path: str
    loaded_at: datetime
    unpack_folder_path: str
    pack_file_path: str
    signed_file_path: str


class APKPatcher:
    DIST_FOLDER: str = dotenv_get_set('DIST_FOLDER', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dist')))
    JAVA_FOLDER: str = os.path.join(DIST_FOLDER, 'java')
    JRE_FOLDER: str = os.path.join(JAVA_FOLDER, 'jre')
    JDK_FOLDER: str = os.path.join(JAVA_FOLDER, 'jdk')
    APKTOOL_FOLDER: str = os.path.join(DIST_FOLDER, 'apktool')
    APKSIGNER_FOLDER: str = os.path.join(DIST_FOLDER, 'apksigner')
    ANDROIDJAR_FOLDER: str = os.path.join(DIST_FOLDER, 'android_jar')
    DX_FOLDER: str = os.path.join(DIST_FOLDER, 'dx')
    BAKSMALI_FOLDER: str = os.path.join(DIST_FOLDER, 'baksmali')
    APK_FOLDER: str = os.path.join(DIST_FOLDER, 'apks')
    JAVA_VERSION: str = dotenv_get_set('JAVA_VERSION', 'latest')
    APKTOOL_VERSION: str = dotenv_get_set('APKTOOL_VERSION', 'latest')
    APKSIGNER_VERSION: str = dotenv_get_set('APKSIGNER_VERSION', 'latest')
    ANDROIDJAR_VERSION: str = dotenv_get_set('ANDROIDJAR_VERSION', 'latest')
    DX_VERSION: str = dotenv_get_set('DX_VERSION', 'latest')
    BAKSMALI_VERSION: str = dotenv_get_set('BAKSMALI_VERSION', 'latest')
    QOOAPP_TOKEN: Optional[str] = dotenv_get_set('QOOAPP_TOKEN', None)
    QOOAPP_DEVICE_ID: Optional[str] = dotenv_get_set('QOOAPP_DEVICE_ID', None)
    KEY_SIZE = 2048
    SIGN_KEY: str = dotenv_get_set('SIGN_KEY', os.path.join(APKSIGNER_FOLDER, 'key.pk8'))
    SIGN_CERT: str = dotenv_get_set('SIGN_CERT', os.path.join(APKSIGNER_FOLDER, 'cert.x509.pem'))

    java: Java
    apktool: APKTool
    apksigner: APKSigner
    android_jar: AndroidJar
    dx: DX
    baksmali: Baksmali
    qooapp: QooApp
    tools: Dict[Type[ToolType], ToolType]

    progressbar: tqdm

    def __init__(self):
        self.tools = {}
        self.java = self.register_tool(Java, self.JRE_FOLDER, self.JDK_FOLDER, self.JAVA_VERSION)
        self.apktool = self.register_tool(APKTool, self.java, self.APKTOOL_FOLDER, self.APKTOOL_VERSION)
        self.apksigner = self.register_tool(APKSigner, self.java, self.APKSIGNER_FOLDER, self.APKSIGNER_VERSION)
        self.android_jar = self.register_tool(AndroidJar, self.ANDROIDJAR_FOLDER, self.ANDROIDJAR_VERSION)
        self.dx = self.register_tool(DX, self.java, self.DX_FOLDER, self.DX_VERSION)
        self.baksmali = self.register_tool(Baksmali, self.java, self.BAKSMALI_FOLDER, self.BAKSMALI_VERSION)
        self.qooapp = self.register_tool(QooApp, self.QOOAPP_DEVICE_ID, self.QOOAPP_TOKEN)
        if self.QOOAPP_TOKEN is None or self.QOOAPP_DEVICE_ID is None:
            dotenv_get_set('QOOAPP_DEVICE_ID', self.qooapp.device_id)
            dotenv_get_set('QOOAPP_TOKEN', self.qooapp.token)
        self.init_sign_key()

    def register_tool(self, tool: Type[ToolType], *args, **kwargs) -> ToolType:
        print(f'Initializing {tool.__name__}...')
        p = tool(*args, **kwargs)
        if not p.is_ready():
            p.setup(APKPatcher.on_progress, self)
        print(f'Initializing {tool.__name__}...done')
        self.tools[tool] = p
        return p

    def on_progress(self, progress: ProgressData) -> bool:
        if progress.stage == ProgressStage.START or progress.stage == ProgressStage.RESET:
            if hasattr(self, 'progressbar'):
                self.progressbar.close()
            config = {
                'desc': progress.description
            }
            if progress.type == ProgressType.FILE:
                config['unit'] = 'B'
                config['unit_scale'] = True
            self.progressbar = tqdm(**config)
            self.progressbar.update()
        elif progress.stage == ProgressStage.PROGRESS:
            self.progressbar.total = progress.total
            self.progressbar.update(progress.delta)
        elif progress.stage == ProgressStage.STOP:
            self.progressbar.update(progress.total - progress.current)
            self.progressbar.close()
        return True

    def init_sign_key(self):
        print('Initializing signing keys...', end='')

        if os.path.exists(self.SIGN_KEY) and os.path.exists(self.SIGN_CERT):
            print('done')
            return

        if os.path.exists(self.SIGN_KEY) != os.path.exists(self.SIGN_CERT):
            raise Exception(f'Missing sign key or cert! Delete the remaining one to regenerate.')

        Certificate(self.KEY_SIZE).save(self.SIGN_KEY, self.SIGN_CERT)
        print('done')

    def get_apk_info(self, provider: Type[APKProvider], package_name: str,
                     min_sdk_version: int = APKProvider.COMMON_MIN_SDK,
                     available_abi: List[str] = APKProvider.COMMON_ABI) -> APKInfo:
        if provider not in self.tools:
            raise Exception(f'APK provider {provider.__name__} not registered')

        apk_provider: APKProvider = self.tools[provider]

        return apk_provider.get_apk_info(package_name, min_sdk_version, available_abi)

    def get_apk(self, apk_info: APKInfo) -> APK:
        print(f'Loading latest version of {apk_info.package_name}...', end='')

        apk_version_folder = os.path.join(self.APK_FOLDER, apk_info.package_name, apk_info.version_name)
        apk_unpack_folder_path = os.path.join(apk_version_folder, f'{apk_info.package_name}')
        apk_download_path = os.path.join(apk_version_folder, f'{apk_info.package_name}.apk')

        apk_provider: APKProvider = self.tools[apk_info.provider]

        if not os.path.exists(apk_download_path):
            apk_provider.download_apk(apk_info, apk_download_path, APKPatcher.on_progress, self)

        if not apk_provider.is_download_valid(apk_download_path, apk_info):
            raise Exception('downloaded apk is invalid')

        load_time = datetime.utcnow()

        apk_version_folder = os.path.join(self.APK_FOLDER, apk_info.package_name, apk_info.version_name)
        apk_pack_file_name = f'{apk_info.package_name}-{apk_info.version_name}-{math.trunc(load_time.timestamp())}'
        apk_pack_file_path = os.path.join(apk_version_folder, f'{apk_pack_file_name}.apk')
        apk_sign_file_path = os.path.join(apk_version_folder, f'{apk_pack_file_name}.signed.apk')

        print('done')
        return APK(
            apk_info,
            apk_download_path,
            load_time,
            apk_unpack_folder_path,
            apk_pack_file_path,
            apk_sign_file_path
        )

    def unpack_apk(self, apk: APK, clean: bool = False):
        print('Unpacking apk...', end='')
        if os.path.exists(apk.unpack_folder_path):
            if clean:
                print('Deleting existing data...')
                shutil.rmtree(apk.unpack_folder_path)
            else:
                print('done')
                return
        print('')
        proc = self.apktool.unpack_apk(apk.file_path, apk.unpack_folder_path)
        print_subprocess_output(proc)
        print('Unpacking apk...done')

    def apply_patch(self, apk: APK, patch: Type[Patch], config: Optional[Dict[str, Any]] = None):
        print(f'Applying {patch.__name__} patch...', end='')
        if not os.path.exists(apk.unpack_folder_path):
            raise Exception('Unable to apply patch, APK has not been unpacked')
        p = di_class_init(patch, self.tools)
        if config is not None and len(config) > 0:
            p.config(**config)
        p.apply(apk.unpack_folder_path)
        print('done')

    def pack_apk(self, apk: APK, debuggable: bool = False, clean: bool = False):
        print('Packing apk...')
        options = None
        if debuggable:
            options = [
                '--debug'
            ]
        proc = self.apktool.pack_apk(apk.unpack_folder_path, apk.pack_file_path, clean, options)
        print_subprocess_output(proc)
        print('Packing apk...done')

    def sign_apk(self, apk: APK):
        print('Signing apk...', end='')
        proc = self.apksigner.sign_apk(apk.pack_file_path, apk.signed_file_path, self.SIGN_KEY, self.SIGN_CERT)
        print_subprocess_output(proc)
        print('...done')
