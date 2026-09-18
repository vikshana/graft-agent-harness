from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

import pytest

from harness.contracts import AlertTrigger, RunCreateRequest
from harness.gateway import CuratedTool, ToolGateway
from harness.http_api import HarnessHttpApplication
from harness.security import CapabilityAuthority, CapabilityClaims, CapabilityDenied
from harness.service import HarnessService
from harness.store import IdempotencyConflict, TenantBoundaryError


@pytest.mark.unit
class ContractAndProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HarnessService()
        self.request = RunCreateRequest(
            graft_tenant_id="tenant-a",
            graft_principal_id="principal-webhook",
            idempotency_key="hook-1",
            trigger=AlertTrigger(
                "alertmanager", "alert-1", "CPU is high", "fingerprint-1", {"severity": "warning"}
            ),
        )

    def test_alert_creates_private_read_only_run_and_ordered_events(self) -> None:
        run = self.service.create_run(self.request)
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.terminal_outcome, "finding")
        self.assertEqual(run.tool_classes, ("read",))
        events = self.service.replay_events("tenant-a", run.graft_run_id)
        self.assertEqual(
            [event.graft_event_id for event in events],
            sorted(event.graft_event_id for event in events),
        )
        self.assertEqual(events[0].event_type, "status")
        self.assertEqual(events[-1].event_type, "done")
        self.assertTrue(any(event.event_type == "token" for event in events))
        self.assertTrue(
            all(
                event.graft_tenant_id == "tenant-a" and event.contract_version == "v1"
                for event in events
            )
        )

    def test_idempotency_returns_original_run_without_duplicate_events(self) -> None:
        first = self.service.create_run(self.request)
        first_count = len(self.service.replay_events("tenant-a", first.graft_run_id))
        second = self.service.create_run(self.request)
        self.assertEqual(first.graft_run_id, second.graft_run_id)
        self.assertEqual(
            first_count, len(self.service.replay_events("tenant-a", first.graft_run_id))
        )

    def test_replay_cursor_is_exclusive(self) -> None:
        run = self.service.create_run(self.request)
        events = self.service.replay_events("tenant-a", run.graft_run_id)
        self.assertEqual(
            [
                event.graft_event_id
                for event in self.service.replay_events(
                    "tenant-a", run.graft_run_id, events[1].graft_event_id
                )
            ],
            [event.graft_event_id for event in events[2:]],
        )

    def test_idempotency_key_conflict_is_rejected(self) -> None:
        self.service.create_run(self.request)
        conflicting = RunCreateRequest(
            graft_tenant_id="tenant-a",
            graft_principal_id="principal-webhook",
            idempotency_key="hook-1",
            trigger=AlertTrigger("alertmanager", "alert-2", "A different alert", "fingerprint-2"),
        )
        with self.assertRaises(IdempotencyConflict):
            self.service.create_run(conflicting)

    def test_tenant_scope_is_enforced(self) -> None:
        run = self.service.create_run(self.request)
        with self.assertRaises(TenantBoundaryError):
            self.service.get_run("tenant-b", run.graft_run_id)
        with self.assertRaises(TenantBoundaryError):
            self.service.replay_events("tenant-b", run.graft_run_id)

    def test_cancel_terminal_run_is_idempotent(self) -> None:
        run = self.service.create_run(self.request)
        outcome = self.service.cancel_run("tenant-a", run.graft_run_id)
        self.assertEqual(outcome.outcome, "already_terminal")
        self.assertEqual(outcome.status, "completed")

    def test_store_rejects_unknown_update_fields_and_invalid_values(self) -> None:
        run = self.service.create_run(self.request)
        with self.assertRaises(ValueError):
            self.service.store.update_run("tenant-a", run.graft_run_id, created_at="forged")
        with self.assertRaises(ValueError):
            self.service.store.update_run("tenant-a", run.graft_run_id, status=object())
        with self.assertRaises(ValueError):
            self.service.store.update_run("tenant-a", run.graft_run_id, status="unknown")


@pytest.mark.unit
class CapabilityAndGatewayTests(unittest.TestCase):
    def test_capability_rejects_wrong_binding_and_write_class(self) -> None:
        authority = CapabilityAuthority(b"test", clock=lambda: 100)
        token = authority.mint(CapabilityClaims("run-a", "tenant-a", frozenset({"read"}), 200))
        with self.assertRaises(CapabilityDenied):
            authority.validate(
                token, graft_run_id="run-b", graft_tenant_id="tenant-a", required_tool_class="read"
            )
        with self.assertRaises(CapabilityDenied):
            authority.validate(
                token, graft_run_id="run-a", graft_tenant_id="tenant-a", required_tool_class="write"
            )
        expired = authority.mint(CapabilityClaims("run-a", "tenant-a", frozenset({"read"}), 100))
        with self.assertRaises(CapabilityDenied):
            authority.validate(
                expired,
                graft_run_id="run-a",
                graft_tenant_id="tenant-a",
                required_tool_class="read",
            )

    def test_gateway_validates_curated_arguments_and_returns_pointer(self) -> None:
        authority = CapabilityAuthority(b"test", clock=lambda: 100)
        gateway = ToolGateway(
            authority,
            {
                "get_alert": CuratedTool(
                    "get_alert",
                    "read",
                    {"required": ["alert_id"], "properties": {"alert_id": {"type": "string"}}},
                    lambda _: ("artifact-1", 42),
                )
            },
        )
        token = authority.mint(CapabilityClaims("run-a", "tenant-a", frozenset({"read"}), 200))
        pointer = gateway.call(
            token=token,
            graft_run_id="run-a",
            graft_tenant_id="tenant-a",
            graft_tool_name="get_alert",
            arguments={"alert_id": "alert-1"},
        )
        self.assertEqual(pointer.graft_artifact_id, "artifact-1")
        with self.assertRaises(ValueError):
            gateway.call(
                token=token,
                graft_run_id="run-a",
                graft_tenant_id="tenant-a",
                graft_tool_name="get_alert",
                arguments={},
            )


@pytest.mark.contract
class ContractArtifactTests(unittest.TestCase):
    def test_machine_readable_contract_artifacts(self) -> None:
        root = Path(__file__).parents[1]
        openapi = json.loads((root / "contracts/harness-v1.openapi.json").read_text())
        events = json.loads((root / "contracts/run-events-v1.schema.json").read_text())
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertIn("/v1/runs/{graft_run_id}/events", openapi["paths"])
        self.assertEqual(events["properties"]["event_version"]["const"], 1)

    def test_http_provider_contract(self) -> None:
        application = HarnessHttpApplication()
        request_body = json.dumps(
            {
                "graft_tenant_id": "tenant-http",
                "graft_principal_id": "principal-http",
                "idempotency_key": "http-1",
                "trigger": {
                    "source": "alertmanager",
                    "alert_id": "alert-http",
                    "summary": "Disk full",
                    "fingerprint": "fp-http",
                },
            }
        ).encode()
        captured: list[str] = []
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(request_body)),
            "HTTP_X_GRAFT_PRINCIPAL": "principal-http",
            "HTTP_X_GRAFT_IDEMPOTENCY_KEY": "http-1",
            "wsgi.input": io.BytesIO(request_body),
        }
        response = application(environ, lambda status, _: captured.append(status))
        self.assertTrue(captured[0].startswith("201"))
        run = json.loads(response[0])
        self.assertEqual(run["status"], "completed")

    def test_http_rejects_non_string_trigger_fields(self) -> None:
        application = HarnessHttpApplication()
        request_body = json.dumps(
            {
                "graft_tenant_id": "tenant-http",
                "graft_principal_id": "principal-http",
                "idempotency_key": "http-invalid-trigger",
                "trigger": {
                    "source": "alertmanager",
                    "alert_id": "alert-http",
                    "summary": 42,
                    "fingerprint": "fp-http",
                },
            }
        ).encode()
        captured: list[str] = []
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(request_body)),
            "HTTP_X_GRAFT_PRINCIPAL": "principal-http",
            "wsgi.input": io.BytesIO(request_body),
        }
        response = application(environ, lambda status, _: captured.append(status))
        self.assertTrue(captured[0].startswith("400"))
        self.assertEqual(json.loads(response[0])["code"], "invalid_request")

    def test_http_rejects_non_string_label_values(self) -> None:
        application = HarnessHttpApplication()
        request_body = json.dumps(
            {
                "graft_tenant_id": "tenant-http",
                "graft_principal_id": "principal-http",
                "idempotency_key": "http-invalid-label",
                "trigger": {
                    "source": "alertmanager",
                    "alert_id": "alert-http",
                    "summary": "Disk full",
                    "fingerprint": "fp-http",
                    "labels": {"severity": 5},
                },
            }
        ).encode()
        captured: list[str] = []
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/v1/runs",
            "CONTENT_LENGTH": str(len(request_body)),
            "HTTP_X_GRAFT_PRINCIPAL": "principal-http",
            "wsgi.input": io.BytesIO(request_body),
        }
        response = application(environ, lambda status, _: captured.append(status))
        self.assertTrue(captured[0].startswith("400"))
        self.assertEqual(json.loads(response[0])["code"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
