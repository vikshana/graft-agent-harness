"""Explicit-Tenant event and Run repository used by the local provider."""

from __future__ import annotations

from dataclasses import replace
from threading import RLock

from .contracts import Run, RunEvent, utc_now


class TenantBoundaryError(PermissionError):
    """Raised when a caller tries to access another Tenant's data."""


class IdempotencyConflict(ValueError):
    """Raised when a key is reused with a different request fingerprint."""


class InMemoryStore:
    """Reference repository; production replacement must preserve these semantics."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._events: dict[str, list[RunEvent]] = {}
        self._dedupe: dict[tuple[str, str], tuple[str, str]] = {}
        self._next_event_id = 1
        self._lock = RLock()

    def create_run(
        self, run: Run, graft_idempotency_key: str, request_fingerprint: str
    ) -> tuple[Run, bool]:
        with self._lock:
            dedupe_key = (run.graft_tenant_id, graft_idempotency_key)
            previous = self._dedupe.get(dedupe_key)
            if previous:
                previous_run_id, previous_fingerprint = previous
                if previous_fingerprint != request_fingerprint:
                    raise IdempotencyConflict("idempotency key is bound to another request")
                return self._runs[previous_run_id], False
            self._runs[run.graft_run_id] = run
            self._events[run.graft_run_id] = []
            self._dedupe[dedupe_key] = (run.graft_run_id, request_fingerprint)
            return run, True

    def get_run(self, graft_tenant_id: str, graft_run_id: str) -> Run:
        with self._lock:
            run = self._runs.get(graft_run_id)
            return self._assert_scope(run, graft_tenant_id)

    def update_run(self, graft_tenant_id: str, graft_run_id: str, **changes: object) -> Run:
        with self._lock:
            run = self.get_run(graft_tenant_id, graft_run_id)
            allowed_fields = {"status", "terminal_outcome", "finding"}
            unexpected_fields = set(changes) - allowed_fields
            if unexpected_fields:
                raise ValueError(
                    "unsupported Run update fields: " + ", ".join(sorted(unexpected_fields))
                )

            status = run.status
            if "status" in changes:
                status_value = changes["status"]
                if not isinstance(status_value, str):
                    raise ValueError("status must be a string")
                if status_value not in {
                    "queued",
                    "running",
                    "completed",
                    "cancelled",
                    "failed",
                    "cancellation_requested",
                }:
                    raise ValueError(f"unsupported Run status: {status_value}")
                status = status_value

            terminal_outcome = run.terminal_outcome
            if "terminal_outcome" in changes:
                terminal_outcome_value = changes["terminal_outcome"]
                if terminal_outcome_value is not None and not isinstance(
                    terminal_outcome_value, str
                ):
                    raise ValueError("terminal_outcome must be a string or null")
                terminal_outcome = terminal_outcome_value

            finding = run.finding
            if "finding" in changes:
                finding_value = changes["finding"]
                if finding_value is not None and not isinstance(finding_value, str):
                    raise ValueError("finding must be a string or null")
                finding = finding_value

            updated = replace(
                run,
                status=status,
                terminal_outcome=terminal_outcome,
                finding=finding,
                updated_at=utc_now(),
            )
            self._runs[graft_run_id] = updated
            return updated

    def append_event(
        self, graft_tenant_id: str, graft_run_id: str, event_type: str, payload: dict[str, object]
    ) -> RunEvent:
        with self._lock:
            run = self.get_run(graft_tenant_id, graft_run_id)
            event = RunEvent(
                self._next_event_id,
                graft_run_id,
                run.graft_tenant_id,
                event_type,
                dict(payload),
                utc_now(),
            )
            self._next_event_id += 1
            self._events[graft_run_id].append(event)
            return event

    def replay(
        self, graft_tenant_id: str, graft_run_id: str, after_graft_event_id: int = 0
    ) -> list[RunEvent]:
        with self._lock:
            self.get_run(graft_tenant_id, graft_run_id)
            return [
                event
                for event in self._events[graft_run_id]
                if event.graft_event_id > after_graft_event_id
            ]

    @staticmethod
    def _assert_scope(run: Run | None, graft_tenant_id: str) -> Run:
        if run is None or run.graft_tenant_id != graft_tenant_id:
            raise TenantBoundaryError("Run is not visible in this Tenant scope")
        return run
