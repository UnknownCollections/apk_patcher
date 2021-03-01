# APKPatcher

APKPatcher is a Python framework for applying patches to APKs in a reproducable way.

## Installation

Download repo and unpack to a directory. Install requirements by running:

```bash
pip install -r requirements.txt
```

## Simple Example

### Demo

```python
from apk_patcher import APKPatcher
from apk_patcher.patches.change_package_name import ChangePackageName
from apk_patcher.patches.network_security import AllowAllSSLCerts
from apk_patcher.tools.qooapp import QooApp

patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
patcher.unpack_apk(apk, clean=False)
patcher.apply_patch(apk, AllowAllSSLCerts)
patcher.apply_patch(apk, ChangePackageName, {
    'new_package_name': 'com.newtarget.newname'
})
patcher.pack_apk(apk, clean=False, debuggable=True)
patcher.sign_apk(apk)
```

### Getting APK Info

First you must choose an `APKProvider` class. These classes use different methods to obtain APK's. If one doesn't work, is out of date, try another.

Currently, the following `APKProvider` classes are available:

* `QooApp` - [https://www.qoo-app.com/](https://www.qoo-app.com/en)

```python
from apk_patcher import APKPatcher
from apk_patcher.tools.qooapp import QooApp

patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
```

### Downloading an APK

The `APKInfo` dataclass you get as a result from `APKPatcher.get_apk_info(...): ...` is passed directly to `APKPatcher.get_apk(...): ...`:

```python
from apk_patcher import APKPatcher
from apk_patcher.tools.qooapp import QooApp

patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
```

Calling `APKPatcher.get_apk(...): ...` will download the APK if it's not already present. If the file is already downloaded, it will verify the download using the information provided by `APKInfo`.

The return value of `APKPatcher.get_apk(...): ...` contains the `APKInfo` in addition to download, unpack, pack, and signing file paths.

### Unpacking APK

Before applying patches, you must unpack the APK:

```python
from apk_patcher import APKPatcher
from apk_patcher.tools.qooapp import QooApp

patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
patcher.unpack_apk(apk, clean=False)
```

If the `clean` parameter of `APKPatcher.unpack_apk(...): ...` is `True`, any existing unpacked files are deleted first.

### Applying Patches

Once the APK is unpacked, to apply a patch you pass the `Patch` class (just the class, not an instance of the class) to `APKPatcher.apply_patch(...): ...` in addition to the `APK` instance provided by `APKPatcher.get_apk(...): ...`.

```python
from apk_patcher import APKPatcher
from apk_patcher.patches.network_security import AllowAllSSLCerts
from apk_patcher.tools.qooapp import QooApp

patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
patcher.unpack_apk(apk, clean=False)
patcher.apply_patch(apk, AllowAllSSLCerts)
```

## Tools Required

These tools are automatically downloaded if necessary by `APKPatcher`.

* [Java Development Kit and Java Runtime Environment](https://github.com/AdoptOpenJDK/openjdk8-binaries/releases)
  * JRE for running other Java based tools
  * JDK for compiling custom Java classes for smali injection
* [APKTool](https://github.com/iBotPeaches/Apktool) - APK decompilation and rebuilding  
* [APKSigner](https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/30.0.2/+/refs/heads/master/lib/apksigner.jar) - Signing APK's for valid installation on Android devices
* [DX](https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/30.0.2/+/refs/heads/master/lib/dx.jar) - Converts compiled Java class files to Android dex files
* [Android.jar](https://android.googlesource.com/platform/prebuilts/fullsdk/platforms/android-30/+/refs/heads/master/android.jar) - Used as the class path for compiling custom Java classes
* [Baksmali](https://github.com/JesusFreke/smali) - Converts Android dex files to editable smali files

## Configuration

On first launch, `APKPatcher` will generate a `.env` file with the default configuration in your current working directory.
   
```
DIST_FOLDER=
APKTOOL_VERSION=
APKSIGNER_VERSION=
SIGN_KEY=
SIGN_CERT=
JAVA_VERSION=
ANDROIDJAR_VERSION=
DX_VERSION=
BAKSMALI_VERSION=
```

You are free to modify any of the configuration; which will take effect next launch. 
* `*_VERSION` has a special keyword `latest`. `APKPatcher` will attempt to update to the latest version of the tool at launch. If you want to version lock, you will need to manually edit the `.env` file.
* `JAVA_VERSION` has a special keyword `system`. Normally `APKPatcher` will download a fresh copy of the JRE and JDK version 8 using [AdoptOpenJDK](https://adoptopenjdk.net/). By specifying `system`, `APKPatcher` will attempt to use your system installed JRE and JDK as long as it's present in your PATH.
* While `APKPatcher` will create an APK signing key and certificate, you are free to provide your own by changing the path in `SIGN_KEY` and `SIGN_CERT`. JKS files are not supported, but you are able to convert from a JKS to Cert/Key.

## Documentation

The `APKPatcher` class has three main components:

1. `Tool` classes that download and execute tools
2. `Patch` classes that modify the unpacked APK assets
3. `APKProvider` classes (a subclass of `Tool`). Currenty only QooApp is supported. In the future, different APK repositories and local loading will be supported.

`Patches` can work without tools, or automatically have the proper `Tool` class instance be given using dependency injection.

### Custom Patches

```python
from apk_patcher.lib.patch import Patch

class MyPatch(Patch):
    
    def config(self):
        ...

    def apply(self, root_folder_path: str):
        ...

    def unapply(self, root_folder_path: str):
        ...
```

At a minimum, your `Patch` get's passed the root folder path that contains the unpacked APK assets. 

You make any modifications in `Patch.apply(...): ...` and you must be able to undo those modifications in `Patch.unapply(...): ...`. The reason for this is to allow repeatable rebuilds or rollbacks on errors.

The `Patch` abstract class gives you a few methods to help with backups:

* `Patch.backup_exists(file_path: str) -> bool: ...`
  * Returns `True` if there is already a version of `file_path` that is backed-up 
* `Patch.backup_file(file_path: str): ...`
  * Makes a copy of `file_path` in the same location. Appends `.{PATCH_NAME}.backup` to the file name.
  * In the example above, with `test.xml` as a `file_path`, the backup file name would be `text.xml.MyPatch.backup`. This allows for multiple patches to modify the same file and to still roll back changes if necessary.  
* `Patch.restore_file(file_path: str): ...`
  * Restores `file_path` using a backup made by `Patch.backup_file(...): ...`.
    
Continuing from the above demo, we want to edit `AndroidManifest.xml` and replace the word `chicken` with `beef`:

```python
class MyPatch(Patch):
    
    def config(self):
        ...

    def apply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')
        
        self.backup_file(target_file_path)
            
        with open(target_file_path, 'r+') as f:
            manifest_data = f.read()
            manifest_data = manifest_data.replace('chicken', 'beef')
            f.seek(0)
            f.write(manifest_data)
            f.truncate()

    def unapply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')
        self.restore_file(target_file_path)
```

How do we execute our patch? Just add it to the pipeline:

```python
patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
patcher.unpack_apk(apk, clean=False)
patcher.apply_patch(apk, MyPatch)
patcher.pack_apk(apk, clean=False, debuggable=True)
patcher.sign_apk(apk)
```

What if we want `chicken` and `beef` to be config options? Modify the `config` method to include your config.

```python
def config(self, word_a: str, word_b: str):
    self.word_a = word_a
    self.word_b = word_b
```

Passing that config looks like this:

```python
patcher.apply_patch(apk, MyPatch, {
    'word_a': 'pork',
    'word_b': 'tapeworm' # Google can go fuck itself...
})
```

What if we want access to one of the tools by-way of a `Tool` class? Add an `__init__` method to your `Patch` class with the proper type annotations. `APKPatcher` class will automatically pass the proper instances of the `Tool` when the `Patch` is executed.

```python
def __init__(self, java: Java):
    self.java = java
```

The simple example patch all together:

```python
class MyPatch(Patch):
    word_a: str
    word_b: str

    java: Java

    def __init__(self, java: Java):
        self.java = java

    def config(self, word_a: str, word_b: str):
        self.word_a = word_a
        self.word_b = word_b

    def apply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')

        self.backup_file(target_file_path)

        self.java.runtime.exec('java', ['-version'])

        with open(target_file_path, 'r+') as f:
            manifest_data = f.read()
            manifest_data = manifest_data.replace(self.word_a, self.word_b)
            f.seek(0)
            f.write(manifest_data)
            f.truncate()

    def unapply(self, root_folder_path: str):
        target_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')
        self.restore_file(target_file_path)


patcher = APKPatcher()
apk_info = patcher.get_apk_info(QooApp, 'com.target.packagename')
apk = patcher.get_apk(apk_info)
patcher.unpack_apk(apk, clean=False)
patcher.apply_patch(apk, MyPatch, {
    'word_a': 'pork',
    'word_b': 'tapeworm'
})
patcher.pack_apk(apk, clean=False, debuggable=True)
patcher.sign_apk(apk)
```

#### Built-in Patch Subclasses

The framework inclues some predefined subclasses to make patch building easier.

##### SmaliPatch

The `SmaliPatch` class simplifies the process of editing a single smali file in a find then replace scenario.

For example, let's say we have a smali file at `smali/com/company/test.smali`. That smali file has a method called 'update()' that we want to replace:

```python
from apk_patcher.lib.smali_patch import SmaliPatch

class MySmaliPatch(SmaliPatch):
    def config(self, **kwargs):
        pass

    @property
    def target_file(self) -> str:
        return os.path.join(
            'smali', 'com', 'company', 'test.smali'
        )

    @property
    def line_start(self) -> str:
        return 'update'

    @property
    def line_end(self) -> Optional[str]:
        return '.end method'

    def replace(self, original: str) -> str:
        return textwrap.dedent("""\
            .method static update()V
                .locals 0
                
                return-void
            .end method
        """)
```

Simple? Yup. `SmaliPatch.line_start(...): ...` and `SmaliPatch.line_end(...): ...` only have to contain a partial match. Regex to be supported in the future.

What if what you want to change is only one line? Make `line_end` return `None`:

```python
@property
def line_end(self) -> Optional[str]:
    return None
```

### Custom Tool

In this framework, a `Tool` is a general term for a class that performs a specific action but requires setup or initialization beforehand.

The most basic `Tool` looks like this:

```python
from typing import Any, Optional

from apk_patcher.lib.progress import ProgressCallback
from apk_patcher.lib.tool import Tool

class MyTool(Tool):
    
    def is_ready(self) -> bool:
        return True

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        ...
```

When `APKPatcher` registers a `Tool` it will call `Tool.is_ready()`. If the `Tool` is not ready, it will then call `Tool.setup(...)`.

Any other method you add to your `MyTool` class will be available to your `Patch` instance:

```python
class MyTool(Tool):
    
    def is_ready(self) -> bool:
        return True

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        ...

    def my_custom_method(self, a: int, b: int) -> int:
        return a + b
    
class MyPatch(Patch):
    my_tool: MyTool

    def __init__(self, my_tool: MyTool):
        self.my_tool = my_tool

    def config(self):
        ...

    def apply(self, root_folder_path: str):
        print(self.my_tool.my_custom_method(42, 30))
```

Making your `Tool` available to `APKPatcher`:

```python
patcher = APKPatcher()
patcher.register_tool(MyTool)
```

`APKPatcher.register_tool(...)` also returns the created instance of your tool, in case you need to do anything with it before it get's used during the patching process.

Adding configuration options to a `Tool` is similar to a `Patch`:

```python
class MyTool(Tool):
    config_a: str
    
    def __init__(self, config_a: str):
        self.config_a = config_a

patcher = APKPatcher()
patcher.register_tool(MyTool, config_a='test')
```

#### Built-in Tool Subclasses

The framework inclues some predefined subclasses to make tool downloading easier.

##### Downloader

The downloader subclass will help automatically download and verify downloads for a `Tool`. At the most basic level it looks like this:

```python
from apk_patcher.lib.downloader import Downloader
from apk_patcher.lib.stream_download import DownloadMiddleware

class MyTool(Downloader):
    @property
    def target_file_name(self) -> str:
        ...

    @property
    def latest_version(self) -> str:
        ...

    @property
    def download_url(self) -> str:
        ...

    @property
    def download_size(self) -> Optional[int]:
        ...

    @property
    def download_middleware(self) -> Optional[DownloadMiddleware]:
        ...

    def is_download_valid(self) -> bool:
        ...

    def test_download(self):
        ...
```

To use the `Downloader` subclass, just make sure all these methods and properties return the proper result.

* `target_file_name` - local file _name_ of the downloaded file 
* `latest_version` - determine the latest available version number for the tool
* `download_url` - the final download url for the selected version for the tool
* `download_size` - the download size, this will be used for on progress events. If you don't have one, return `None`, and the `Downloader` class will attempt to use the `Content-Length` response header. 
* `download_middleware` - an optional middleware for the downloaded content. Use to stream decrypt a file, or unzip, or base64 decode. Currently, only `stream_decode_response_base64` is available in the `apktool.lib.stream_download` module.
* `is_download_valid` - verify the integrity of the downloaded file. This can be done differently based on the metadata you have on the file. The simplest solution is to check to make sure the downloaded file has the right size. More complicated methods such as file hash verification are also possible here.
* `test_download` - test the tool to make sure it runs. Raise any exception here for failed runs.

##### GoogleSourceDownloader

The `GoogleSourceDownloader` class extends the `Downloader` class. Files at `https://googlesource.com/` can only be downloaded as base64 encoded data. 

There are fewer methods an inherited tool using `GoogleSourceDownloader` needs to complete, and they share the same documentation as `Downloader`. 

```python
from apk_patcher.lib.googlesource_downloader import GoogleSourceDownloader

class MyTool(GoogleSourceDownloader):
    @property
    def latest_version(self) -> str:
        ...

    @property
    def download_url(self) -> str:
        ...

    def test_download(self):
        ...

    @property
    def target_file_name(self) -> str:
        ...
```

##### APKProvider

`APKProvider` classes allow different methods of obtaining APKs. The basic outline of the class is:


```python
from apk_patcher.lib.apk_provider import APKProvider, APKInfo

class MyAPKProvider(APKProvider):
    def get_apk_info(self, package_name: str, sdk_version: int, available_abi: List[str]) -> APKInfo:
        ...

    def download_apk(self, apk_info: APKInfo, output_file_path: str, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        ...

    def is_ready(self) -> bool:
        ...

    def setup(self, on_progress: Optional[ProgressCallback], progress_user_var: Optional[Any]):
        ...
```

Since the `APKProvider` class is a subclass of the `Tool` class, the `is_ready` and `setup` methods are handled the same.

The two new methods each `APKProvider` must implement are `get_apk_info(...) -> APKInfo; ...` and `download_apk(...): ...`.

## License

[UNLICENSE](https://unlicense.org/)

## OSS Attribution

### [lxml](https://github.com/lxml/lxml) by **Infrae**  
_Licensed Under: [BSD 3-Clause License](https://github.com/lxml/lxml/blob/master/LICENSE.txt)_

### [psf/requests](https://github.com/psf/requests) by **Kenneth Reitz**  
_Licensed Under: [Apache-2.0 License](https://github.com/psf/requests/blob/master/LICENSE)_

### [pyca/cryptography](https://github.com/psf/requests) by **Individual contributors**  
_Licensed Under: [Apache-2.0 License](https://github.com/psf/requests/blob/master/LICENSE)_

### [tqdm/tqdm](https://github.com/tqdm/tqdm) by **Individual contributors**  
_Licensed Under: [Various Licenses](https://github.com/tqdm/tqdm/blob/master/LICENCE)_

### [python-dotenv](https://github.com/theskumar/python-dotenv) by **Saurabh Kumar**  
_Licensed Under: [BSD 3-Clause License](https://github.com/theskumar/python-dotenv/blob/master/LICENSE)_

### [iBotPeaches/Apktool](https://github.com/iBotPeaches/Apktool) by **Ryszard Wiśniewski & Connor Tumbleson**
_Licensed Under: [Apache-2.0 License](https://github.com/iBotPeaches/Apktool/blob/master/LICENSE)_

### [JesusFreke/smali](https://github.com/iBotPeaches/Apktool) by **Ben Gruver**
_Licensed Under: [Various Licenses](https://github.com/JesusFreke/smali/blob/master/NOTICE)_