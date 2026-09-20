"""Generate disposable mTLS certificates for tests, never repository files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import CertificatePublicKeyTypes
from cryptography.x509.oid import NameOID


@dataclass(frozen=True, slots=True)
class CertificateMaterial:
    ca_file: Path
    server_file: Path
    server_key_file: Path
    client_file: Path
    client_key_file: Path
    ca_key_file: Path


def _key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _certificate(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: CertificatePublicKeyTypes,
    issuer_key: rsa.RSAPrivateKey,
    *,
    ca: bool,
    not_before: datetime,
    not_after: datetime,
    san: list[x509.GeneralName] | None = None,
) -> x509.Certificate:
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=1 if ca else None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=not ca,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=ca,
                crl_sign=ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()),
            critical=False,
        )
    )
    if san is not None:
        builder = builder.add_extension(x509.SubjectAlternativeName(san), critical=False)
    return builder.sign(issuer_key, hashes.SHA256())


def _write_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )


def _write_cert(path: Path, certificate: x509.Certificate) -> None:
    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


def create_certificates(
    directory: Path,
    *,
    client_common_name: str = "harness-api",
    client_trusted: bool = True,
    client_expired: bool = False,
) -> CertificateMaterial:
    """Create a server and client chain entirely inside ``directory``."""

    directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    root_key = _key()
    root_name = _name("authority-test-root")
    root_cert = _certificate(
        root_name,
        root_name,
        root_key.public_key(),
        root_key,
        ca=True,
        not_before=now - timedelta(days=1),
        not_after=now + timedelta(days=2),
    )
    server_key = _key()
    server_cert = _certificate(
        _name("localhost"),
        root_name,
        server_key.public_key(),
        root_key,
        ca=False,
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(days=1),
        san=[x509.DNSName("localhost"), x509.IPAddress(IPv4Address("127.0.0.1"))],
    )

    issuer_key = root_key
    issuer_name = root_name
    if not client_trusted:
        issuer_key = _key()
        issuer_name = _name("untrusted-client-root")
        untrusted_root = _certificate(
            issuer_name,
            issuer_name,
            issuer_key.public_key(),
            issuer_key,
            ca=True,
            not_before=now - timedelta(days=1),
            not_after=now + timedelta(days=2),
        )
        (directory / "untrusted-client-ca.pem").write_bytes(
            untrusted_root.public_bytes(serialization.Encoding.PEM)
        )
    client_key = _key()
    client_cert = _certificate(
        _name(client_common_name),
        issuer_name,
        client_key.public_key(),
        issuer_key,
        ca=False,
        not_before=now - timedelta(days=2),
        not_after=now - timedelta(seconds=1) if client_expired else now + timedelta(days=1),
        san=[x509.DNSName(client_common_name)],
    )

    ca_file = directory / "ca.pem"
    server_file = directory / "server.pem"
    server_key_file = directory / "server-key.pem"
    client_file = directory / "client.pem"
    client_key_file = directory / "client-key.pem"
    ca_key_file = directory / "ca-key.pem"
    _write_cert(ca_file, root_cert)
    _write_cert(server_file, server_cert)
    _write_key(server_key_file, server_key)
    _write_cert(client_file, client_cert)
    _write_key(client_key_file, client_key)
    _write_key(ca_key_file, root_key)
    return CertificateMaterial(
        ca_file, server_file, server_key_file, client_file, client_key_file, ca_key_file
    )


def create_additional_client_certificate(
    directory: Path, *, trusted_ca: CertificateMaterial, common_name: str
) -> tuple[Path, Path]:
    """Create another client identity signed by an existing test CA."""

    directory.mkdir(parents=True, exist_ok=True)
    ca_certificate = x509.load_pem_x509_certificate(trusted_ca.ca_file.read_bytes())
    ca_key = serialization.load_pem_private_key(trusted_ca.ca_key_file.read_bytes(), password=None)
    if not isinstance(ca_key, rsa.RSAPrivateKey):
        raise TypeError("test CA key is not RSA")
    now = datetime.now(UTC)
    client_key = _key()
    client_certificate = _certificate(
        _name(common_name),
        ca_certificate.subject,
        client_key.public_key(),
        ca_key,
        ca=False,
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(days=1),
        san=[x509.DNSName(common_name)],
    )
    certificate_file = directory / "client.pem"
    key_file = directory / "client-key.pem"
    _write_cert(certificate_file, client_certificate)
    _write_key(key_file, client_key)
    return certificate_file, key_file
