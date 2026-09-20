"""Bounded, pre-PostgreSQL Authority Service protocol slice.

This package is deliberately not the production Authority Service.  It contains
the v1 internal protocol, a deterministic verifier seam, an in-memory
test-only Token Service, and a loopback mTLS HTTP adapter for Gate 1 Task 2
evidence.  PostgreSQL replay/RLS/audit and Task 5 signing/JWKS isolation are
explicitly outside this slice.
"""

from .protocol import (
    AuthorityProtocolError,
    MintRequest,
    MintResponse,
    ResolutionRequest,
    ResolutionResponse,
    VerifiedIdentity,
    canonical_webhook_fingerprint,
)
from .service import (
    AuditIntentRecorder,
    DeterministicSurfaceVerifier,
    SurfaceVerifier,
    TestOnlyOpaqueTokenService,
)
from .transport import AuthorityIntegrationServer

__all__ = [
    "AuditIntentRecorder",
    "AuthorityIntegrationServer",
    "AuthorityProtocolError",
    "DeterministicSurfaceVerifier",
    "MintRequest",
    "MintResponse",
    "ResolutionRequest",
    "ResolutionResponse",
    "SurfaceVerifier",
    "TestOnlyOpaqueTokenService",
    "VerifiedIdentity",
    "canonical_webhook_fingerprint",
]
