"""Transport-independent Phase 1 harness contract models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

CONTRACT_VERSION = "v1"
EVENT_VERSION = 1

EVENT_TYPES = frozenset(
    {
        "status",
        "token",
        "tool_call_start",
        "tool_call_result",
        "evidence_added",
        "budget_consumed",
        "error",
        "done",
    }
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = field(default_factory=dict)
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
            raise ValueError("unsupported contract version")
        if self.trigger_kind != "system_initiated" or self.visibility != "private":
            raise ValueError("Phase 1 webhook Runs must be private system Runs")
        if self.tool_classes != ("read",):
            raise ValueError("system-initiated Runs may only have the read ToolClass")
        if not self.graft_tenant_id or not self.graft_principal_id or not self.idempotency_key:
            raise ValueError("Tenant, Principal, and idempotency key are required")


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {self.event_type}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CancelOutcome:
    graft_run_id: str
    outcome: str
    status: str
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
