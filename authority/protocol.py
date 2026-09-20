"""Strict v1 wire values and canonical webhook fingerprinting."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

AUTHORITY_SCHEMA_VERSION = "v1"
ENVELOPE_VERSION = "v1"
SURFACES = frozenset({"grafana", "slack", "webhook", "schedule", "api"})
INITIATION_MODES = frozenset({"user_initiated", "system_initiated"})
_MISSING = object()


class AuthorityProtocolError(ValueError):
    """A request or response value violates the closed authority contract."""

    def __init__(self, message: str, *, code: str = "contract_violation") -> None:
        super().__init__(message)
        self.code = code


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityProtocolError(f"{name} must be an object")
    return value


def _closed_object(value: Any, name: str, required: set[str]) -> dict[str, Any]:
    result = _object(value, name)
    if set(result) != required:
        missing = sorted(required - set(result))
        extra = sorted(set(result) - required)
        detail = f"missing={missing}" if missing else f"extra={extra}"
        raise AuthorityProtocolError(f"{name} has an invalid closed shape ({detail})")
    return result


def _string(value: Any, name: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise AuthorityProtocolError(f"{name} must be a non-empty string")
    return value


def _nullable_string(value: Any, name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise AuthorityProtocolError(f"{name} must be a string or null")
    return value


def _string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise AuthorityProtocolError(f"{name} must be a list of non-empty strings")
    return tuple(value)


def _json_value(value: Any, name: str) -> None:
    """Reject non-JSON values without normalising semantic event data."""

    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise AuthorityProtocolError(f"{name} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{name}[{index}]")
        return
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise AuthorityProtocolError(f"{name} contains a non-string object key")
        for key, item in value.items():
            _json_value(item, f"{name}.{key}")
        return
    raise AuthorityProtocolError(f"{name} contains a non-JSON value")


def validate_webhook_envelope(value: Any) -> dict[str, Any]:
    """Validate and return the closed v1 semantic webhook envelope."""

    envelope = _closed_object(
        value,
        "graft_webhook_envelope",
        {"graft_envelope_version", "graft_source", "graft_event", "graft_delivery", "graft_alert"},
    )
    if envelope["graft_envelope_version"] != ENVELOPE_VERSION:
        raise AuthorityProtocolError("unsupported webhook envelope version")
    source = _closed_object(
        envelope["graft_source"],
        "graft_source",
        {"graft_source_ref", "graft_source_type"},
    )
    event = _closed_object(
        envelope["graft_event"],
        "graft_event",
        {"graft_event_ref", "graft_event_type"},
    )
    delivery = _closed_object(
        envelope["graft_delivery"],
        "graft_delivery",
        {"graft_delivery_ref", "graft_delivery_sequence"},
    )
    alert = _closed_object(
        envelope["graft_alert"],
        "graft_alert",
        {"graft_alert_name", "graft_alert_status", "graft_alert_labels", "graft_alert_annotations"},
    )
    for group, fields in (
        (source, ("graft_source_ref", "graft_source_type")),
        (event, ("graft_event_ref", "graft_event_type")),
        (delivery, ("graft_delivery_ref",)),
        (alert, ("graft_alert_name", "graft_alert_status")),
    ):
        for field in fields:
            _string(group[field], field)
    _nullable_string(delivery["graft_delivery_sequence"], "graft_delivery_sequence")
    for field in ("graft_alert_labels", "graft_alert_annotations"):
        if not isinstance(alert[field], dict):
            raise AuthorityProtocolError(f"{field} must be an object")
        _json_value(alert[field], field)
    _json_value(envelope, "graft_webhook_envelope")
    return envelope


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    return value


def canonical_webhook_bytes(envelope: Mapping[str, Any]) -> bytes:
    """Return compact UTF-8 canonical bytes for a validated envelope."""

    validated = validate_webhook_envelope(dict(envelope))
    return json.dumps(
        _canonical_value(validated),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_webhook_fingerprint(envelope: Mapping[str, Any]) -> str:
    """Return the v1 semantic webhook fingerprint."""

    return "sha256:" + hashlib.sha256(canonical_webhook_bytes(envelope)).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditActor:
    graft_principal_id: str | None
    graft_tenant_id: str
    graft_role_ids: tuple[str, ...]
    graft_surface: str
    graft_initiation_mode: str
    graft_trust_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "graft_principal_id": self.graft_principal_id,
            "graft_tenant_id": self.graft_tenant_id,
            "graft_role_ids": list(self.graft_role_ids),
            "graft_surface": self.graft_surface,
            "graft_initiation_mode": self.graft_initiation_mode,
            "graft_trust_mode": self.graft_trust_mode,
        }


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    graft_principal_id: str | None
    graft_tenant_id: str
    graft_role_ids: tuple[str, ...]
    graft_initiation_mode: Literal["user_initiated", "system_initiated"]
    graft_service_identity: str
    graft_audit_actor: AuditActor

    def __post_init__(self) -> None:
        if not self.graft_tenant_id or not self.graft_service_identity:
            raise ValueError("verified Tenant and service identity are required")
        if self.graft_initiation_mode not in INITIATION_MODES:
            raise ValueError("invalid initiation mode")
        if not self.graft_role_ids:
            raise ValueError("at least one effective Role is required")
        if self.graft_audit_actor.graft_tenant_id != self.graft_tenant_id:
            raise ValueError("audit actor Tenant mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "graft_principal_id": self.graft_principal_id,
            "graft_tenant_id": self.graft_tenant_id,
            "graft_role_ids": list(self.graft_role_ids),
            "graft_initiation_mode": self.graft_initiation_mode,
            "graft_service_identity": self.graft_service_identity,
            "graft_audit_actor": self.graft_audit_actor.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> VerifiedIdentity:
        item = _closed_object(
            value,
            "graft_verified_identity",
            {
                "graft_principal_id",
                "graft_tenant_id",
                "graft_role_ids",
                "graft_initiation_mode",
                "graft_service_identity",
                "graft_audit_actor",
            },
        )
        mode = _string(item["graft_initiation_mode"], "graft_initiation_mode")
        if mode not in INITIATION_MODES:
            raise AuthorityProtocolError("invalid initiation mode")
        actor = _closed_object(
            item["graft_audit_actor"],
            "graft_audit_actor",
            {
                "graft_principal_id",
                "graft_tenant_id",
                "graft_role_ids",
                "graft_surface",
                "graft_initiation_mode",
                "graft_trust_mode",
            },
        )
        actor_mode = _string(
            actor["graft_initiation_mode"], "graft_audit_actor.graft_initiation_mode"
        )
        if actor_mode not in INITIATION_MODES:
            raise AuthorityProtocolError("invalid audit actor initiation mode")
        return cls(
            _nullable_string(item["graft_principal_id"], "graft_principal_id"),
            _string(item["graft_tenant_id"], "graft_tenant_id"),
            _string_list(item["graft_role_ids"], "graft_role_ids"),
            mode,  # type: ignore[arg-type]
            _string(item["graft_service_identity"], "graft_service_identity"),
            AuditActor(
                _nullable_string(actor["graft_principal_id"], "audit principal"),
                _string(actor["graft_tenant_id"], "audit Tenant"),
                _string_list(actor["graft_role_ids"], "audit Roles"),
                _string(actor["graft_surface"], "audit surface"),
                actor_mode,
                _string(actor["graft_trust_mode"], "audit trust mode"),
            ),
        )


def _check_common_request(item: dict[str, Any], required: set[str]) -> None:
    if not required <= set(item):
        raise AuthorityProtocolError("authority request has a closed-shape violation")
    if set(item) - required:
        allowed_optional = {"graft_webhook_envelope"}
        if set(item) - required > allowed_optional:
            raise AuthorityProtocolError("authority request has a closed-shape violation")
    if item.get("graft_authority_schema_version") != AUTHORITY_SCHEMA_VERSION:
        raise AuthorityProtocolError(
            "unsupported authority schema version", code="unsupported_version"
        )
    surface = _string(item.get("graft_surface"), "graft_surface")
    if surface not in SURFACES:
        raise AuthorityProtocolError("unsupported surface", code="unsupported_surface")
    _string(item.get("graft_surface_credential"), "graft_surface_credential")
    _string(item.get("graft_request_correlation_id"), "graft_request_correlation_id")
    envelope = item.get("graft_webhook_envelope", _MISSING)
    if surface == "webhook" and envelope is _MISSING:
        raise AuthorityProtocolError("webhook envelope is required", code="malformed_envelope")
    if surface != "webhook" and envelope is not _MISSING:
        raise AuthorityProtocolError(
            "non-webhook cannot carry an envelope", code="malformed_envelope"
        )
    if surface == "webhook":
        validate_webhook_envelope(envelope)


@dataclass(frozen=True, slots=True)
class ResolutionRequest:
    graft_surface: str
    graft_surface_credential: str
    graft_webhook_envelope: dict[str, Any] | None
    graft_request_correlation_id: str

    def __post_init__(self) -> None:
        item: dict[str, Any] = {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_surface": self.graft_surface,
            "graft_surface_credential": self.graft_surface_credential,
            "graft_request_correlation_id": self.graft_request_correlation_id,
        }
        if self.graft_webhook_envelope is not None:
            item["graft_webhook_envelope"] = self.graft_webhook_envelope
        _check_common_request(
            item,
            {
                "graft_authority_schema_version",
                "graft_surface",
                "graft_surface_credential",
                "graft_request_correlation_id",
            },
        )
        if self.graft_surface == "webhook":
            if self.graft_webhook_envelope is None:
                raise AuthorityProtocolError(
                    "webhook envelope is required", code="malformed_envelope"
                )
            validate_webhook_envelope(self.graft_webhook_envelope)
        elif self.graft_webhook_envelope is not None:
            raise AuthorityProtocolError(
                "non-webhook cannot carry an envelope", code="malformed_envelope"
            )

    @classmethod
    def from_dict(cls, value: Any) -> ResolutionRequest:
        item = _object(value, "resolution request")
        _check_common_request(
            item,
            {
                "graft_authority_schema_version",
                "graft_surface",
                "graft_surface_credential",
                "graft_request_correlation_id",
            },
        )
        return cls(
            item["graft_surface"],
            item["graft_surface_credential"],
            None
            if "graft_webhook_envelope" not in item
            else validate_webhook_envelope(item["graft_webhook_envelope"]),
            item["graft_request_correlation_id"],
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_surface": self.graft_surface,
            "graft_surface_credential": self.graft_surface_credential,
            "graft_request_correlation_id": self.graft_request_correlation_id,
        }
        if self.graft_webhook_envelope is not None:
            result["graft_webhook_envelope"] = self.graft_webhook_envelope
        return result


@dataclass(frozen=True, slots=True)
class ResolutionResponse:
    decision: Literal["allow", "deny"]
    correlation_id: str
    identity: VerifiedIdentity | None = None
    event_fingerprint: str | None = None
    expires_at: str | None = None
    verifier_revision: str | None = None
    deny_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.decision == "deny":
            return {
                "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
                "graft_decision": "deny",
                "graft_deny_code": self.deny_code or "credential_invalid",
                "graft_request_correlation_id": self.correlation_id,
            }
        if self.identity is None or self.expires_at is None or self.verifier_revision is None:
            raise ValueError("allow response is incomplete")
        return {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_decision": "allow",
            "graft_verified_identity": self.identity.to_dict(),
            "graft_event_fingerprint": self.event_fingerprint,
            "graft_resolution_expires_at": self.expires_at,
            "graft_verifier_revision": self.verifier_revision,
            "graft_request_correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> ResolutionResponse:
        item = _object(value, "resolution response")
        if item.get("graft_authority_schema_version") != AUTHORITY_SCHEMA_VERSION:
            raise AuthorityProtocolError(
                "unsupported authority schema version", code="unsupported_version"
            )
        decision = _string(item.get("graft_decision"), "graft_decision")
        correlation = _string(item.get("graft_request_correlation_id"), "correlation")
        if decision == "deny":
            _closed_object(
                item,
                "deny response",
                {
                    "graft_authority_schema_version",
                    "graft_decision",
                    "graft_deny_code",
                    "graft_request_correlation_id",
                },
            )
            return cls("deny", correlation, deny_code=_string(item["graft_deny_code"], "deny code"))
        if decision != "allow":
            raise AuthorityProtocolError("invalid resolution decision")
        _closed_object(
            item,
            "allow response",
            {
                "graft_authority_schema_version",
                "graft_decision",
                "graft_verified_identity",
                "graft_event_fingerprint",
                "graft_resolution_expires_at",
                "graft_verifier_revision",
                "graft_request_correlation_id",
            },
        )
        fingerprint = _nullable_string(item["graft_event_fingerprint"], "event fingerprint")
        if fingerprint is not None and not fingerprint.startswith("sha256:"):
            raise AuthorityProtocolError("invalid event fingerprint")
        return cls(
            "allow",
            correlation,
            VerifiedIdentity.from_dict(item["graft_verified_identity"]),
            fingerprint,
            _string(item["graft_resolution_expires_at"], "resolution expiry"),
            _string(item["graft_verifier_revision"], "verifier revision"),
        )


@dataclass(frozen=True, slots=True)
class FirstResolution:
    expires_at: str
    verifier_revision: str
    event_fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "graft_resolution_expires_at": self.expires_at,
            "graft_verifier_revision": self.verifier_revision,
            "graft_event_fingerprint": self.event_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class MintRequest:
    graft_surface: str
    graft_surface_credential: str
    graft_webhook_envelope: dict[str, Any] | None
    graft_run_id: str
    graft_first_resolution: FirstResolution
    graft_request_correlation_id: str

    def __post_init__(self) -> None:
        item: dict[str, Any] = {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_surface": self.graft_surface,
            "graft_surface_credential": self.graft_surface_credential,
            "graft_run_id": self.graft_run_id,
            "graft_first_resolution": self.graft_first_resolution.to_dict(),
            "graft_request_correlation_id": self.graft_request_correlation_id,
        }
        if self.graft_webhook_envelope is not None:
            item["graft_webhook_envelope"] = self.graft_webhook_envelope
        _check_common_request(
            item,
            {
                "graft_authority_schema_version",
                "graft_surface",
                "graft_surface_credential",
                "graft_run_id",
                "graft_first_resolution",
                "graft_request_correlation_id",
            },
        )
        _string(self.graft_run_id, "graft_run_id")

    @classmethod
    def from_dict(cls, value: Any) -> MintRequest:
        item = _object(value, "mint request")
        _check_common_request(
            item,
            {
                "graft_authority_schema_version",
                "graft_surface",
                "graft_surface_credential",
                "graft_run_id",
                "graft_first_resolution",
                "graft_request_correlation_id",
            },
        )
        first = _closed_object(
            item["graft_first_resolution"],
            "graft_first_resolution",
            {
                "graft_resolution_expires_at",
                "graft_verifier_revision",
                "graft_event_fingerprint",
            },
        )
        fingerprint = _nullable_string(first["graft_event_fingerprint"], "first fingerprint")
        if fingerprint is not None and not fingerprint.startswith("sha256:"):
            raise AuthorityProtocolError("invalid first fingerprint")
        return cls(
            item["graft_surface"],
            item["graft_surface_credential"],
            None
            if "graft_webhook_envelope" not in item
            else validate_webhook_envelope(item["graft_webhook_envelope"]),
            _string(item["graft_run_id"], "graft_run_id"),
            FirstResolution(
                _string(first["graft_resolution_expires_at"], "first expiry"),
                _string(first["graft_verifier_revision"], "first revision"),
                fingerprint,
            ),
            item["graft_request_correlation_id"],
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_surface": self.graft_surface,
            "graft_surface_credential": self.graft_surface_credential,
            "graft_run_id": self.graft_run_id,
            "graft_first_resolution": self.graft_first_resolution.to_dict(),
            "graft_request_correlation_id": self.graft_request_correlation_id,
        }
        if self.graft_webhook_envelope is not None:
            result["graft_webhook_envelope"] = self.graft_webhook_envelope
        return result


@dataclass(frozen=True, slots=True)
class MintResponse:
    decision: Literal["allow", "deny"]
    correlation_id: str
    identity: VerifiedIdentity | None = None
    event_fingerprint: str | None = None
    graft_run_id: str | None = None
    capability_token: str | None = None
    deny_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.decision == "deny":
            return {
                "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
                "graft_mint_decision": "deny",
                "graft_deny_code": self.deny_code or "credential_invalid",
                "graft_request_correlation_id": self.correlation_id,
            }
        if self.identity is None or self.graft_run_id is None or self.capability_token is None:
            raise ValueError("allow mint response is incomplete")
        return {
            "graft_authority_schema_version": AUTHORITY_SCHEMA_VERSION,
            "graft_mint_decision": "allow",
            "graft_verified_identity": self.identity.to_dict(),
            "graft_event_fingerprint": self.event_fingerprint,
            "graft_run_id": self.graft_run_id,
            "graft_capability_token": self.capability_token,
            "graft_request_correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> MintResponse:
        item = _object(value, "mint response")
        if item.get("graft_authority_schema_version") != AUTHORITY_SCHEMA_VERSION:
            raise AuthorityProtocolError(
                "unsupported authority schema version", code="unsupported_version"
            )
        decision = _string(item.get("graft_mint_decision"), "graft_mint_decision")
        correlation = _string(item.get("graft_request_correlation_id"), "correlation")
        if decision == "deny":
            _closed_object(
                item,
                "mint deny response",
                {
                    "graft_authority_schema_version",
                    "graft_mint_decision",
                    "graft_deny_code",
                    "graft_request_correlation_id",
                },
            )
            return cls("deny", correlation, deny_code=_string(item["graft_deny_code"], "deny code"))
        if decision != "allow":
            raise AuthorityProtocolError("invalid mint decision")
        _closed_object(
            item,
            "mint allow response",
            {
                "graft_authority_schema_version",
                "graft_mint_decision",
                "graft_verified_identity",
                "graft_event_fingerprint",
                "graft_run_id",
                "graft_capability_token",
                "graft_request_correlation_id",
            },
        )
        return cls(
            "allow",
            correlation,
            VerifiedIdentity.from_dict(item["graft_verified_identity"]),
            _nullable_string(item["graft_event_fingerprint"], "event fingerprint"),
            _string(item["graft_run_id"], "graft_run_id"),
            _string(item["graft_capability_token"], "capability token"),
        )
