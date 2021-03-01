from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


class Certificate:
    __private_key: RSAPrivateKey

    def __init__(self, key_size: int):
        self.__private_key = rsa.generate_private_key(65537, key_size)
        self.cert = self.__build_cert()

    def __build_cert(self) -> x509.Certificate:
        now = datetime.utcnow()
        subject = x509.Name([
            x509.NameAttribute(x509.NameOID.COMMON_NAME, u'n/a'),
        ])

        builder = x509.CertificateBuilder(
            issuer_name=subject,
            subject_name=subject,
            not_valid_before=now,
            not_valid_after=now + timedelta(days=20000),
            public_key=self.__private_key.public_key(),
            serial_number=x509.random_serial_number()
        )
        return builder.sign(self.__private_key, hashes.SHA256())

    def save(self, key_path: str, cert_path: str):
        with open(key_path, 'wb+') as f:
            f.write(self.__private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, 'wb+') as f:
            f.write(self.cert.public_bytes(serialization.Encoding.PEM))
