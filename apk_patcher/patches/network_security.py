import os
import shutil
import textwrap

from lxml import etree

from apk_patcher.lib.patch import Patch


class AllowAllSSLCerts(Patch):
    xml_file_path = os.path.join(
        'res', 'xml', 'network_security_config.xml'
    )

    def config(self, **kwargs):
        pass

    def create_network_config(self, root_folder_path: str):
        xml_file_path = os.path.join(root_folder_path, self.xml_file_path)
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        with open(os.path.join(root_folder_path, self.xml_file_path), 'w+') as f:
            f.write(textwrap.dedent("""\
                <?xml version="1.0" encoding="utf-8"?>
                <network-security-config>
                    <base-config cleartextTrafficPermitted="true">
                        <trust-anchors>
                            <certificates src="system" overridePins="true" />
                            <certificates src="user" overridePins="true" />
                        </trust-anchors>
                    </base-config>
                </network-security-config>
            """))

    def delete_network_config(self, root_folder_path: str):
        xml_file_path = os.path.join(root_folder_path, self.xml_file_path)
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

    def update_android_manifest(self, root_folder_path: str):
        manifest_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')

        self.restore_file(manifest_file_path)
        self.backup_file(manifest_file_path)

        xml = etree.parse(manifest_file_path)
        xml_root = xml.getroot()
        application_node = xml_root.xpath('./application', namespaces=xml_root.nsmap)[0]
        application_node.attrib['{http://schemas.android.com/apk/res/android}networkSecurityConfig'] = '@xml/network_security_config'
        xml.write(
            manifest_file_path,
            xml_declaration=True,
            encoding='utf-8',
            standalone=False
        )

    def remove_manifest_changes(self, root_folder_path: str):
        manifest_file_path = os.path.join(root_folder_path, 'AndroidManifest.xml')
        self.restore_file(manifest_file_path)

    def apply(self, root_folder_path: str):
        self.create_network_config(root_folder_path)
        self.update_android_manifest(root_folder_path)

    def unapply(self, root_folder_path: str):
        self.delete_network_config(root_folder_path)
        self.remove_manifest_changes(root_folder_path)
