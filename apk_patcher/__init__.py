import sys

if sys.hexversion < 0x03080000:
    raise Exception('python 3.8 or newer required')

from apk_patcher.apk_patcher import APKPatcher
