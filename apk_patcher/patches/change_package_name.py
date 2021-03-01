import os
from io import SEEK_SET

from lxml import etree

from apk_patcher.lib.patch import Patch


class ChangePackageName(Patch):
    new_package_name: str

    def config(self, new_package_name: str):
        self.new_package_name = new_package_name

    def apply(self, root_folder_path: str):
        manifest_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')

        self.restore_file(manifest_file_path)
        self.backup_file(manifest_file_path)

        xml = etree.parse(manifest_file_path)
        xml_root = xml.getroot()
        manifest_node = xml_root.xpath('.', namespaces=xml_root.nsmap)[0]
        old_package_name = manifest_node.attrib['package']

        with open(manifest_file_path, 'r+') as f:
            xml_data = f.read()
            f.seek(0, SEEK_SET)
            f.write(xml_data.replace(old_package_name, self.new_package_name))
            f.truncate()

    def unapply(self, root_folder_path: str):
        self.restore_file(os.path.join(root_folder_path, 'AndroidManifest.xml'))
