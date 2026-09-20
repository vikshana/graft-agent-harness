"""Reference provider for the versioned harness contract."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass

from .contracts import CancelOutcome, EventReplayPage, Run, RunCreateRequest, RunEvent, utc_now
from .security import CapabilityAuthority, CapabilityClaims
from .store import InMemoryStore


@dataclass(frozen=True, slots=True)
class ModelResponse:
    finding: str
    evidence: tuple[str, ...] = ()


class DeterministicChatModel:
    """Small chat-model double with the same invocation shape used by graph nodes."""

    def invoke(self, messages: list[dict[str, str]]) -> ModelResponse:
        summary = messages[-1]["content"]
        return ModelResponse(f"Investigation complete: {summary}", ("alert-summary",))


class HarnessService:
    def __init__(
        self,
        store: InMemoryStore | None = None,
        authority: CapabilityAuthority | None = None,
        model: DeterministicChatModel | None = None,
    ) -> None:
        self.store = store or InMemoryStore()
        self.authority = authority or CapabilityAuthority(b"phase-1-local-secret")
        self.model = model or DeterministicChatModel()

    def create_run(self, request: RunCreateRequest) -> Run:
        run, _ = self.create_run_result(request)
        return run

    def create_run_result(self, request: RunCreateRequest) -> tuple[Run, bool]:
        request.validate()
        graft_run_id = str(uuid.uuid4())
        now = utc_now()
        run = Run(
            graft_run_id,
            request.graft_tenant_id,
            request.graft_principal_id,
            "queued",
            None,
            None,
            request.tool_classes,
            now,
            now,
        )
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "trigger": request.trigger.__dict__
                    if hasattr(request.trigger, "__dict__")
                    else {
                        "source": request.trigger.source,
                        "alert_id": request.trigger.alert_id,
                        "summary": request.trigger.summary,
                        "fingerprint": request.trigger.fingerprint,
                        "labels": request.trigger.labels,
                    },
                    "principal": request.graft_principal_id,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        run, created = self.store.create_run(run, request.idempotency_key, fingerprint)
        if not created:
            return run, False
        self.store.append_event(
            request.graft_tenant_id, run.graft_run_id, "status", {"graft_status": "queued"}
        )
        self._execute(request, run.graft_run_id)
        return self.store.get_run(request.graft_tenant_id, run.graft_run_id), True

    def get_run(self, graft_tenant_id: str, graft_run_id: str) -> Run:
        return self.store.get_run(graft_tenant_id, graft_run_id)

    def replay_events(
        self, graft_tenant_id: str, graft_run_id: str, after_graft_event_id: int = 0
    ) -> list[RunEvent]:
        return self.store.replay(graft_tenant_id, graft_run_id, after_graft_event_id)

    def replay_page(
        self,
        graft_tenant_id: str,
        graft_run_id: str,
        after_graft_event_id: int = 0,
        limit: int = 100,
    ) -> EventReplayPage:
        if limit < 1 or limit > 1000:
            raise ValueError("graft_event_limit is outside the contract range")
        events = self.replay_events(graft_tenant_id, graft_run_id, after_graft_event_id)
        page_events = tuple(events[:limit])
        return EventReplayPage(
            graft_run_id,
            page_events,
            page_events[-1].graft_event_id if page_events else after_graft_event_id,
            len(events) > limit,
        )

    def cancel_run(self, graft_tenant_id: str, graft_run_id: str) -> CancelOutcome:
        run = self.store.get_run(graft_tenant_id, graft_run_id)
        if run.status in {"completed", "cancelled", "failed"}:
            return CancelOutcome(graft_run_id, "already_terminal", run.status)
        if run.status == "cancellation_requested":
            return CancelOutcome(graft_run_id, "already_requested", run.status)
        self.store.update_run(graft_tenant_id, graft_run_id, status="cancellation_requested")
        self.store.append_event(
            graft_tenant_id,
            graft_run_id,
            "status",
            {"graft_status": "cancellation_requested", "graft_effective_at": "next_step_boundary"},
        )
        return CancelOutcome(graft_run_id, "accepted", "cancellation_requested")

    def mint_run_capability(self, graft_tenant_id: str, graft_run_id: str, expires_at: int) -> str:
        run = self.store.get_run(graft_tenant_id, graft_run_id)
        return self.authority.mint(
            CapabilityClaims(
                run.graft_run_id, run.graft_tenant_id, frozenset(run.tool_classes), expires_at
            )
        )

    def _execute(self, request: RunCreateRequest, graft_run_id: str) -> None:
        self.store.update_run(request.graft_tenant_id, graft_run_id, status="running")
        self.store.append_event(
            request.graft_tenant_id, graft_run_id, "status", {"graft_status": "running"}
        )
        response = self.model.invoke([{"role": "user", "content": request.trigger.summary}])
        for token in response.finding.split(" "):
            self.store.append_event(
                request.graft_tenant_id, graft_run_id, "token", {"graft_text": token + " "}
            )
        for evidence in response.evidence:
            self.store.append_event(
                request.graft_tenant_id,
                graft_run_id,
                "evidence_added",
                {"graft_evidence_id": evidence},
            )
        self.store.update_run(
            request.graft_tenant_id,
            graft_run_id,
            status="completed",
            terminal_outcome="finding",
            finding=response.finding,
        )
        self.store.append_event(
            request.graft_tenant_id, graft_run_id, "done", {"graft_outcome": "finding"}
        )
