from __future__ import annotations

import http.client
import socket
import ssl
from collections.abc import Generator
from pathlib import Path

import pytest

from authority.protocol import (
    AuditActor,
    FirstResolution,
    MintRequest,
    ResolutionRequest,
    VerifiedIdentity,
)
from authority.service import (
    DeterministicSurfaceVerifier,
)
from authority.service import (
    TestOnlyOpaqueTokenService as OpaqueTokenService,
)
from authority.transport import AuthorityIntegrationServer, create_mtls_client_context
from harness.authority_client import MtlsAuthorityClient
from tests.fixtures.authority.certificates import (
    CertificateMaterial,
    create_additional_client_certificate,
    create_certificates,
)


def identity() -> VerifiedIdentity:
    actor = AuditActor(
        "principal-transport", "tenant-transport", ("role-reader",), "api", "user_initiated", "test"
    )
    return VerifiedIdentity(
        "principal-transport",
        "tenant-transport",
        ("role-reader",),
        "user_initiated",
        "authority",
        actor,
    )


def client_context(material: CertificateMaterial) -> ssl.SSLContext:
    # The fixture is intentionally a small dataclass; use attributes here to
    # keep the certificate-generation helper's public shape obvious.
    return create_mtls_client_context(
        ca_file=str(material.ca_file),
        certificate_file=str(material.client_file),
        private_key_file=str(material.client_key_file),
    )


@pytest.fixture
def running_authority(
    tmp_path: Path,
) -> Generator[tuple[AuthorityIntegrationServer, CertificateMaterial], None, None]:
    material = create_certificates(tmp_path / "valid")
    credential = "transport credential  \u03bb"
    service = OpaqueTokenService(DeterministicSurfaceVerifier({("api", credential): identity()}))
    server = AuthorityIntegrationServer(
        service,
        certificate_file=str(material.server_file),
        private_key_file=str(material.server_key_file),
        trust_bundle_file=str(material.ca_file),
    )
    server.start()
    try:
        yield server, material
    finally:
        server.stop()


@pytest.mark.contract
def test_valid_mtls_peer_can_complete_both_calls(
    running_authority: tuple[AuthorityIntegrationServer, CertificateMaterial],
) -> None:
    server, material = running_authority
    client = MtlsAuthorityClient(*server.address, client_context(material))
    request = ResolutionRequest("api", "transport credential  \u03bb", None, "transport-1")
    response = client.resolve(request)
    assert response.decision == "allow"
    assert response.expires_at is not None
    assert response.verifier_revision is not None
    mint = client.mint(
        MintRequest(
            "api",
            "transport credential  \u03bb",
            None,
            "graft_run_transport",
            FirstResolution(response.expires_at, response.verifier_revision, None),
            "transport-2",
        )
    )
    assert mint.decision == "allow"
    assert client.raw_requests == ["transport credential  \u03bb"] * 2


@pytest.mark.contract
def test_missing_untrusted_and_expired_certificates_fail_tls_without_app_response(
    tmp_path: Path, running_authority: tuple[AuthorityIntegrationServer, CertificateMaterial]
) -> None:
    server, _ = running_authority
    host, port = server.address
    for name, _kwargs in (
        ("missing", None),
        ("untrusted", {"client_trusted": False}),
        ("expired", {"client_expired": True}),
    ):
        if name == "untrusted":
            material = create_certificates(tmp_path / name, client_trusted=False)
        elif name == "expired":
            material = create_certificates(tmp_path / name, client_expired=True)
        else:
            material = create_certificates(tmp_path / name)
        if name == "missing":
            context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH, cafile=str(material.ca_file)
            )
            context.check_hostname = True
        else:
            context = client_context(material)
        with pytest.raises((ssl.SSLError, ConnectionError, TimeoutError, OSError)):
            connection = http.client.HTTPSConnection(host, port, context=context, timeout=1)
            connection.request("POST", "/internal/authority/v1/surface-resolution", body=b"{}")
            connection.getresponse()


@pytest.mark.contract
def test_valid_tls_wrong_peer_is_typed_deny_and_no_bearer_or_plain_http_fallback(
    tmp_path: Path, running_authority: tuple[AuthorityIntegrationServer, CertificateMaterial]
) -> None:
    server, _ = running_authority
    wrong_client, wrong_key = create_additional_client_certificate(
        tmp_path / "wrong", trusted_ca=running_authority[1], common_name="other-service"
    )
    wrong_context = create_mtls_client_context(
        ca_file=str(running_authority[1].ca_file),
        certificate_file=str(wrong_client),
        private_key_file=str(wrong_key),
    )
    client = MtlsAuthorityClient(*server.address, wrong_context)
    response = client.resolve(
        ResolutionRequest("api", "transport credential  \u03bb", None, "wrong-peer")
    )
    assert response.decision == "deny"
    assert response.deny_code == "mtls_peer_not_allowlisted"

    context = wrong_context
    connection = http.client.HTTPSConnection(*server.address, context=context, timeout=1)
    connection.request(
        "POST",
        "/internal/authority/v1/surface-resolution",
        body=b"{}",
        headers={"Authorization": "Bearer not-used"},
    )
    assert connection.getresponse().status == 403
    connection.close()

    raw = socket.create_connection(server.address, timeout=1)
    try:
        raw.sendall(
            b"POST /internal/authority/v1/surface-resolution HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        with pytest.raises((ConnectionError, OSError, TimeoutError, socket.timeout)):
            raw.recv(1)
    finally:
        raw.close()
