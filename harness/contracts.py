"""Transport-independent Phase 1 harness contract models.

The JSON artefacts in :mod:`contracts` are the wire authority.  This module is
the small, dependency-free provider-side representation used by the reference
implementation and by contract tests.  ``RunCreateRequest`` is an internal
composition object: its identity fields are deliberately absent from every
canonical REST and MCP serialisation.  A future Authority Service (or the
explicit test identity seam in :mod:`harness.http_api`) supplies those fields
out of band.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeAlias

CONTRACT_VERSION = "v1"
EVENT_VERSION = 1
RUN_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_RUN_ID_RE = re.compile(RUN_ID_PATTERN)

RUN_STATUSES = frozenset(
    {
        "queued",
        "running",
        "completed",
        "cancelled",
        "failed",
        "cancellation_requested",
    }
)
TERMINAL_OUTCOMES = frozenset({"finding", "no_finding", "cancelled", "failed", "timed_out"})
CANCEL_OUTCOMES = frozenset({"accepted", "already_requested", "already_terminal"})

EVENT_TYPES = frozenset(
    {
        "status",
        "token",
        "agent_thought",
        "plan_updated",
        "tool_call_start",
        "tool_call_result",
        "evidence_added",
        "hypothesis_updated",
        "confidence_changed",
        "action_proposed",
        "action_confirmed",
        "action_executed",
        "sub_agent_spawned",
        "hitl_required",
        "budget_consumed",
        "budget_warning",
        "error",
        "done",
    }
)

ERROR_CODES = frozenset(
    {
        "authentication_required",
        "authentication_failed",
        "authorisation_denied",
        "invalid_request",
        "unsupported_contract_version",
        "not_found",
        "idempotency_conflict",
        "state_conflict",
        "cursor_invalid",
        "replay_cursor_expired",
        "throttled",
        "request_timeout",
        "service_unavailable",
        "internal_error",
    }
)


class ContractValidationError(ValueError):
    """Raised when a known contract object is not semantically valid."""


class UnsupportedContractVersion(ContractValidationError):
    """Raised when a request names a contract version this provider cannot serve."""


@dataclass(frozen=True, slots=True)
class ExternalReference:
    """A pointer to an external object; raw customer data is never inline."""

    graft_ref_kind: str
    graft_uri: str
    graft_sha256: str | None = None
    graft_content_type: str | None = None
    graft_byte_length: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.graft_ref_kind, str) or not isinstance(self.graft_uri, str):
            raise ContractValidationError("external references need string fields")
        if not self.graft_ref_kind or not self.graft_uri:
            raise ContractValidationError("external references need a kind and URI")
        if not (self.graft_uri.startswith("graft://") or self.graft_uri.startswith("https://")):
            raise ContractValidationError("external reference URI must be graft:// or https://")
        if self.graft_byte_length is not None and not isinstance(self.graft_byte_length, int):
            raise ContractValidationError("external reference byte length must be an integer")
        if self.graft_byte_length is not None and self.graft_byte_length < 0:
            raise ContractValidationError("external reference byte length cannot be negative")
        if self.graft_sha256 is not None and not isinstance(self.graft_sha256, str):
            raise ContractValidationError("external reference SHA-256 must be a string")
        if self.graft_content_type is not None and not isinstance(self.graft_content_type, str):
            raise ContractValidationError("external reference content type must be a string")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            key: value
            for key, value in {
                "graft_ref_kind": self.graft_ref_kind,
                "graft_uri": self.graft_uri,
                "graft_sha256": self.graft_sha256,
                "graft_content_type": self.graft_content_type,
                "graft_byte_length": self.graft_byte_length,
            }.items()
            if value is not None
        }


REFERENCE_FIELDS = frozenset(
    {
        "graft_ref_kind",
        "graft_uri",
        "graft_sha256",
        "graft_content_type",
        "graft_byte_length",
    }
)

POINTER_METADATA_FIELDS = frozenset({"graft_label", "graft_origin"})


@dataclass(frozen=True, slots=True)
class PointerMetadata:
    """Bounded, non-content metadata allowed beside an external pointer."""

    graft_label: str | None = None
    graft_origin: str | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        for field_name, value in (
            ("graft_label", self.graft_label),
            ("graft_origin", self.graft_origin),
        ):
            if value is not None and (not isinstance(value, str) or len(value) > 256):
                raise ContractValidationError(
                    f"{field_name} must be a string of at most 256 characters"
                )

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            key: value
            for key, value in {
                "graft_label": self.graft_label,
                "graft_origin": self.graft_origin,
            }.items()
            if value is not None
        }


def validate_pointer_metadata_dict(value: object, field: str) -> None:
    """Validate the explicitly extension-safe pointer metadata object."""

    if not isinstance(value, dict):
        raise ContractValidationError(f"{field} must be pointer metadata")
    unknown = sorted(set(value) - POINTER_METADATA_FIELDS)
    if unknown:
        raise ContractValidationError(f"{field} contains unsupported fields: {', '.join(unknown)}")
    try:
        PointerMetadata(
            graft_label=value.get("graft_label"),
            graft_origin=value.get("graft_origin"),
        )
    except (TypeError, ValueError) as exc:
        raise ContractValidationError(f"{field} must be pointer metadata") from exc


def _pointer_metadata_from_dict(value: object, field: str) -> PointerMetadata | None:
    if value is None:
        return None
    validate_pointer_metadata_dict(value, field)
    if not isinstance(value, dict):  # pragma: no cover - narrowed by the validator above
        return None
    return PointerMetadata(
        graft_label=value.get("graft_label"),
        graft_origin=value.get("graft_origin"),
    )


def validate_reference_dict(value: object, field: str) -> None:
    """Validate a serialised pointer without permitting hidden inline fields."""

    if not isinstance(value, dict):
        raise ContractValidationError(f"{field} must be an external reference")
    unknown = sorted(set(value) - REFERENCE_FIELDS)
    if unknown:
        raise ContractValidationError(f"{field} contains unsupported fields: {', '.join(unknown)}")
    try:
        reference = ExternalReference(
            graft_ref_kind=value["graft_ref_kind"],
            graft_uri=value["graft_uri"],
            graft_sha256=value.get("graft_sha256"),
            graft_content_type=value.get("graft_content_type"),
            graft_byte_length=value.get("graft_byte_length"),
        )
        reference.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractValidationError(f"{field} must be an external reference") from exc


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_run_id(value: object, field: str = "graft_run_id") -> None:
    """Validate the canonical bounded Run identifier shape."""

    if not isinstance(value, str) or _RUN_ID_RE.fullmatch(value) is None:
        raise ContractValidationError(f"{field} does not match the contract pattern")


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    code: str
    message: str
    graft_request_id: str
    details: dict[str, Any] = field(default_factory=dict)
    contract_version: str = CONTRACT_VERSION

    @property
    def request_id(self) -> str:
        """Compatibility alias for the old WSGI prototype."""

        return self.graft_request_id

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES and self.code != "unauthenticated":
            raise ContractValidationError(f"unsupported error code: {self.code}")
        if not self.message or not self.graft_request_id:
            raise ContractValidationError("error message and graft_request_id are required")
        if not isinstance(self.details, dict):
            raise ContractValidationError("error details must be an object")
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_contract_dict(), "code": self.to_contract_dict()["graft_code"]}

    def to_contract_dict(self) -> dict[str, Any]:
        """Return the canonical graft-prefixed wire representation."""

        wire_code = "authentication_required" if self.code == "unauthenticated" else self.code
        return {
            "graft_code": wire_code,
            "graft_message": self.message,
            "graft_request_id": self.graft_request_id,
            "graft_details": dict(self.details),
            "graft_contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class AlertTrigger:
    source: str
    alert_id: str
    summary: str
    fingerprint: str
    labels: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.source or not self.alert_id or not self.fingerprint:
            raise ValueError("source, alert_id, and fingerprint are required")
        if len(self.summary) > 4096:
            raise ValueError("summary exceeds the contract limit")

    def to_contract_dict(self) -> dict[str, Any]:
        """Return the canonical, graft-prefixed request representation."""

        self.validate()
        return {
            "graft_source": self.source,
            "graft_alert_id": self.alert_id,
            "graft_summary": self.summary,
            "graft_fingerprint": self.fingerprint,
            "graft_labels": dict(self.labels),
        }


@dataclass(frozen=True, slots=True)
class RunCreateRequest:
    graft_tenant_id: str
    trigger: AlertTrigger
    idempotency_key: str
    graft_principal_id: str
    trigger_kind: str = "system_initiated"
    visibility: str = "private"
    tool_classes: tuple[str, ...] = ("read",)
    contract_version: str = CONTRACT_VERSION

    def validate(self) -> None:
        self.trigger.validate()
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")
        if self.trigger_kind != "system_initiated" or self.visibility != "private":
            raise ValueError("Phase 1 webhook Runs must be private system Runs")
        if self.tool_classes != ("read",):
            raise ValueError("system-initiated Runs may only have the read ToolClass")
        if not self.graft_tenant_id or not self.graft_principal_id or not self.idempotency_key:
            raise ValueError("Tenant, Principal, and idempotency key are required")

    def to_contract_dict(self) -> dict[str, Any]:
        """Return the canonical request without the out-of-band identity.

        The internal request retains verified identity so the reference service
        can exercise Tenant scoping.  It must never be serialised onto the
        REST or MCP input wire.
        """

        self.validate()
        return {
            "graft_trigger": self.trigger.to_contract_dict(),
            "graft_trigger_kind": self.trigger_kind,
            "graft_visibility": self.visibility,
            "graft_tool_classes": list(self.tool_classes),
            "graft_contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class Run:
    graft_run_id: str
    graft_tenant_id: str
    graft_principal_id: str
    status: str
    terminal_outcome: str | None
    finding: str | None
    tool_classes: tuple[str, ...]
    created_at: str
    updated_at: str
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        validate_run_id(self.graft_run_id)
        if not self.graft_tenant_id or not self.graft_principal_id:
            raise ContractValidationError("Run Tenant and Principal are required")
        if self.status not in RUN_STATUSES:
            raise ContractValidationError(f"unsupported Run status: {self.status}")
        if self.terminal_outcome is not None and self.terminal_outcome not in TERMINAL_OUTCOMES:
            raise ContractValidationError(f"unsupported terminal outcome: {self.terminal_outcome}")
        if not isinstance(self.tool_classes, tuple) or not all(
            tool_class in {"read", "write", "destructive"} for tool_class in self.tool_classes
        ):
            raise ContractValidationError("unsupported ToolClass")
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_contract_dict(), "status": self.status}

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "graft_run_id": self.graft_run_id,
            "graft_tenant_id": self.graft_tenant_id,
            "graft_principal_id": self.graft_principal_id,
            "graft_status": self.status,
            "graft_terminal_outcome": self.terminal_outcome,
            "graft_finding_ref": (
                {
                    "graft_ref_kind": "finding",
                    "graft_uri": f"graft://runs/{self.graft_run_id}/finding",
                    "graft_content_type": "text/plain",
                }
                if self.finding is not None
                else None
            ),
            "graft_tool_classes": list(self.tool_classes),
            "graft_created_at": self.created_at,
            "graft_updated_at": self.updated_at,
            "graft_contract_version": self.contract_version,
            "graft_identity_source": "authority_service",
        }


@dataclass(frozen=True, slots=True)
class RunEvent:
    graft_event_id: int
    graft_run_id: str
    graft_tenant_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str
    event_version: int = EVENT_VERSION
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.graft_event_id < 1:
            raise ContractValidationError("event id must be positive")
        validate_run_id(self.graft_run_id)
        if not self.graft_tenant_id:
            raise ContractValidationError("event Tenant is required")
        if not self.event_type:
            raise ContractValidationError("event_type is required")
        if self.event_version != EVENT_VERSION:
            raise ContractValidationError("unsupported event version")
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")
        validate_event_payload(self.event_type, self.payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "graft_event_type": self.event_type,
            "graft_event_version": self.event_version,
            "graft_payload": dict(self.payload),
            "graft_created_at": self.created_at,
            "graft_contract_version": self.contract_version,
        }

    def to_contract_dict(self) -> dict[str, Any]:
        canonical_payload = dict(self.payload)
        scalar_aliases = {
            "status": "graft_status",
            "text": "graft_text",
            "confidence": "graft_confidence",
            "consumed": "graft_consumed",
            "limit": "graft_limit",
            "code": "graft_code",
            "message": "graft_message",
            "outcome": "graft_outcome",
        }
        for legacy_name, canonical_name in scalar_aliases.items():
            if legacy_name in canonical_payload and canonical_name not in canonical_payload:
                canonical_payload[canonical_name] = canonical_payload.pop(legacy_name)
        return {
            "graft_event_id": self.graft_event_id,
            "graft_run_id": self.graft_run_id,
            "graft_tenant_id": self.graft_tenant_id,
            "graft_event_type": self.event_type,
            "graft_event_version": self.event_version,
            "graft_payload": canonical_payload,
            "graft_created_at": self.created_at,
            "graft_contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class EventReplayPage:
    """A bounded, exclusive-cursor replay response."""

    graft_run_id: str
    events: tuple[RunEvent, ...]
    next_after_event_id: int
    has_more: bool
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        validate_run_id(self.graft_run_id)
        if not self.graft_run_id or self.next_after_event_id < 0:
            raise ContractValidationError("replay page identifiers are invalid")
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")
        if any(event.graft_run_id != self.graft_run_id for event in self.events):
            raise ContractValidationError("replay page contains an event from another Run")
        if self.events and self.next_after_event_id != self.events[-1].graft_event_id:
            raise ContractValidationError("replay cursor must point at the last returned event")

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "graft_run_id": self.graft_run_id,
            "graft_events": [event.to_contract_dict() for event in self.events],
            "graft_next_after_event_id": self.next_after_event_id,
            "graft_has_more": self.has_more,
            "graft_contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class CancelOutcome:
    graft_run_id: str
    outcome: str
    status: str
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        validate_run_id(self.graft_run_id)
        if self.outcome not in CANCEL_OUTCOMES:
            raise ContractValidationError(f"unsupported cancellation outcome: {self.outcome}")
        if self.status not in RUN_STATUSES:
            raise ContractValidationError(f"unsupported Run status: {self.status}")
        if self.contract_version != CONTRACT_VERSION:
            raise UnsupportedContractVersion("unsupported contract version")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "graft_outcome": self.outcome,
            "graft_status": self.status,
            "graft_contract_version": self.contract_version,
        }

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "graft_run_id": self.graft_run_id,
            "graft_outcome": self.outcome,
            "graft_status": self.status,
            "graft_contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class StatusPayload:
    graft_status: str


@dataclass(frozen=True, slots=True)
class NarrativePayload:
    graft_text: str


@dataclass(frozen=True, slots=True)
class ToolCallStartPayload:
    graft_tool_call_id: str
    graft_tool_name: str
    graft_arguments_sha256: str


@dataclass(frozen=True, slots=True)
class ToolCallResultPayload:
    graft_tool_call_id: str
    graft_artifact_ref: ExternalReference
    graft_pointer_metadata: PointerMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.graft_tool_call_id, str) or not self.graft_tool_call_id:
            raise ContractValidationError("tool-call result needs a tool-call identifier")
        if not isinstance(self.graft_artifact_ref, ExternalReference):
            raise ContractValidationError("tool-call result needs an external artifact pointer")
        if self.graft_pointer_metadata is not None and not isinstance(
            self.graft_pointer_metadata, PointerMetadata
        ):
            raise ContractValidationError("tool-call result metadata must be safe pointer metadata")


@dataclass(frozen=True, slots=True)
class PointerPayload:
    graft_ref: ExternalReference
    graft_pointer_metadata: PointerMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.graft_ref, ExternalReference):
            raise ContractValidationError("pointer payload needs an external reference")
        if self.graft_pointer_metadata is not None and not isinstance(
            self.graft_pointer_metadata, PointerMetadata
        ):
            raise ContractValidationError("pointer payload metadata must be safe pointer metadata")


@dataclass(frozen=True, slots=True)
class EvidencePayload:
    graft_evidence_id: str
    graft_external_ref: ExternalReference | None = None
    graft_pointer_metadata: PointerMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.graft_evidence_id, str) or not self.graft_evidence_id:
            raise ContractValidationError("evidence needs an identifier")
        if self.graft_external_ref is not None and not isinstance(
            self.graft_external_ref, ExternalReference
        ):
            raise ContractValidationError("evidence reference must be an external reference")
        if self.graft_pointer_metadata is not None and not isinstance(
            self.graft_pointer_metadata, PointerMetadata
        ):
            raise ContractValidationError("evidence metadata must be safe pointer metadata")


@dataclass(frozen=True, slots=True)
class ConfidencePayload:
    graft_confidence: float


@dataclass(frozen=True, slots=True)
class BudgetPayload:
    graft_budget_kind: str
    graft_consumed: float
    graft_limit: float


@dataclass(frozen=True, slots=True)
class DonePayload:
    graft_outcome: str


EventPayload: TypeAlias = (
    StatusPayload
    | NarrativePayload
    | ToolCallStartPayload
    | ToolCallResultPayload
    | PointerPayload
    | EvidencePayload
    | ConfidencePayload
    | BudgetPayload
    | DonePayload
)


def is_known_event_type(event_type: str) -> bool:
    """Return whether an event belongs to the current fixed v1 taxonomy."""

    return event_type in EVENT_TYPES


def validate_event_payload(event_type: str, payload: dict[str, Any]) -> None:
    """Validate the stable portion of a payload while allowing additive fields.

    Unknown event types are intentionally accepted as extension events.  A
    consumer can therefore replay a newer stream without dropping the entire
    response.  Known event types have required fields and pointer-only rules
    for externally stored data.
    """

    if not isinstance(payload, dict):
        raise ContractValidationError("event payload must be an object")
    required: dict[str, tuple[str, ...]] = {
        "status": ("graft_status",),
        "token": ("graft_text",),
        "agent_thought": ("graft_text",),
        "plan_updated": ("graft_ref",),
        "tool_call_start": (
            "graft_tool_call_id",
            "graft_tool_name",
            "graft_arguments_sha256",
        ),
        "tool_call_result": ("graft_tool_call_id",),
        "evidence_added": ("graft_evidence_id",),
        "hypothesis_updated": ("graft_ref",),
        "confidence_changed": ("graft_confidence",),
        "action_proposed": ("graft_ref",),
        "action_confirmed": ("graft_ref",),
        "action_executed": ("graft_ref",),
        "sub_agent_spawned": ("graft_child_run_id",),
        "hitl_required": ("graft_ref",),
        "budget_consumed": ("graft_budget_kind", "graft_consumed", "graft_limit"),
        "budget_warning": ("graft_budget_kind", "graft_consumed", "graft_limit"),
        "error": ("graft_code", "graft_message"),
        "done": ("graft_outcome",),
    }
    fields = required.get(event_type)
    if fields is None:
        return
    missing = [field_name for field_name in fields if field_name not in payload]
    # The retained synchronous provider predates the canonical wire aliases.
    # Accepting these values here preserves its reference semantics; contract
    # serialisation remains available through to_contract_dict().
    aliases = {
        "graft_status": "status",
        "graft_text": "text",
        "graft_confidence": "confidence",
        "graft_consumed": "consumed",
        "graft_limit": "limit",
        "graft_code": "code",
        "graft_message": "message",
        "graft_outcome": "outcome",
    }
    missing = [field_name for field_name in missing if aliases.get(field_name) not in payload]
    if missing:
        raise ContractValidationError(f"{event_type} payload is missing: {', '.join(missing)}")
    if event_type == "tool_call_result" and "graft_artifact_ref" not in payload:
        raise ContractValidationError("tool_call_result must contain an external artifact pointer")
    if event_type == "tool_call_result":
        # Tool-call results are a closed pointer-only object.  Additive fields
        # remain permitted on the event envelope and other payload variants,
        # but this boundary must not gain an inline escape hatch.
        allowed = {"graft_tool_call_id", "graft_artifact_ref", "graft_pointer_metadata"}
        unsafe = sorted(set(payload) - allowed)
        if unsafe:
            raise ContractValidationError(
                "tool_call_result must contain only pointer metadata: " + ", ".join(unsafe)
            )
        validate_reference_dict(payload["graft_artifact_ref"], "graft_artifact_ref")
        if "graft_pointer_metadata" in payload:
            validate_pointer_metadata_dict(
                payload["graft_pointer_metadata"], "graft_pointer_metadata"
            )
    pointer_events = {
        "plan_updated",
        "hypothesis_updated",
        "action_proposed",
        "action_confirmed",
        "action_executed",
        "hitl_required",
    }
    if event_type in pointer_events:
        pointer_name = "graft_ref"
        allowed = {pointer_name, "graft_pointer_metadata"}
        unsafe = sorted(set(payload) - allowed)
        if unsafe:
            raise ContractValidationError(
                f"{event_type} must contain only pointer metadata: " + ", ".join(unsafe)
            )
        pointer = payload.get(pointer_name)
        if not isinstance(pointer, dict):
            raise ContractValidationError(f"{pointer_name} must be an external reference object")
        validate_reference_dict(pointer, pointer_name)
        if "graft_pointer_metadata" in payload:
            validate_pointer_metadata_dict(
                payload["graft_pointer_metadata"], "graft_pointer_metadata"
            )
    if event_type == "evidence_added":
        allowed = {"graft_evidence_id", "graft_external_ref", "graft_pointer_metadata"}
        unsafe = sorted(set(payload) - allowed)
        if unsafe:
            raise ContractValidationError(
                "evidence_added must contain only pointer metadata: " + ", ".join(unsafe)
            )
        if "graft_external_ref" in payload:
            validate_reference_dict(payload["graft_external_ref"], "graft_external_ref")
        if "graft_pointer_metadata" in payload:
            validate_pointer_metadata_dict(
                payload["graft_pointer_metadata"], "graft_pointer_metadata"
            )
    if event_type == "status":
        status = payload.get("graft_status", payload.get("status"))
        if not isinstance(status, str) or status not in RUN_STATUSES:
            raise ContractValidationError(f"unsupported event Run status: {status}")
    if event_type == "done":
        outcome = payload.get("graft_outcome", payload.get("outcome"))
        if not isinstance(outcome, str) or outcome not in TERMINAL_OUTCOMES:
            raise ContractValidationError(f"unsupported event terminal outcome: {outcome}")
    if event_type == "error":
        error_code = payload.get("graft_code", payload.get("code"))
        if not isinstance(error_code, str) or error_code not in ERROR_CODES:
            raise ContractValidationError(f"unsupported event error code: {error_code}")
