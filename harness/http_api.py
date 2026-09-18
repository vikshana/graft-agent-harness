"""Dependency-free HTTP adapter for the transport-independent harness contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol, runtime_checkable
from urllib.parse import parse_qs, urlsplit

from .contracts import AlertTrigger, ErrorEnvelope, RunCreateRequest
from .service import HarnessService
from .store import IdempotencyConflict, TenantBoundaryError


@runtime_checkable
class ReadableInput(Protocol):
    def read(self, length: int) -> object:
        """Read request bytes from the WSGI input stream."""


class HarnessHttpApplication:
    """WSGI application; surface adapters may wrap the same service contract."""

    def __init__(self, service: HarnessService | None = None):
        self.service = service or HarnessService()

    def __call__(
        self, environ: dict[str, object], start_response: Callable[..., object]
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        graft_principal_id = str(environ.get("HTTP_X_GRAFT_PRINCIPAL", ""))
        request_id = str(environ.get("HTTP_X_GRAFT_REQUEST_ID", "request-local"))
        try:
            if not graft_principal_id:
                return self._error(
                    start_response,
                    401,
                    ErrorEnvelope("unauthenticated", "verified Principal is required", request_id),
                )
            if method == "POST" and path == "/v1/runs":
                body = self._body(environ)
                body_principal_id = self._string_field(
                    body.get("graft_principal_id"), "graft_principal_id"
                )
                if body_principal_id != graft_principal_id:
                    return self._error(
                        start_response,
                        403,
                        ErrorEnvelope(
                            "authorisation_denied", "Principal binding mismatch", request_id
                        ),
                    )
                trigger = self._object_field(body.get("trigger"), "trigger")
                idempotency_value = environ.get(
                    "HTTP_X_GRAFT_IDEMPOTENCY_KEY", body.get("idempotency_key", "")
                )
                request = RunCreateRequest(
                    graft_tenant_id=self._string_field(
                        body.get("graft_tenant_id"), "graft_tenant_id"
                    ),
                    graft_principal_id=graft_principal_id,
                    idempotency_key=self._string_field(idempotency_value, "idempotency_key"),
                    trigger=AlertTrigger(
                        self._string_field(trigger.get("source"), "trigger.source"),
                        self._string_field(trigger.get("alert_id"), "trigger.alert_id"),
                        self._string_field(trigger.get("summary"), "trigger.summary"),
                        self._string_field(trigger.get("fingerprint"), "trigger.fingerprint"),
                        self._labels_field(trigger.get("labels", {})),
                    ),
                )
                return self._json(start_response, 201, self.service.create_run(request).to_dict())
            parts = path.split("/")
            if len(parts) == 4 and parts[:3] == ["", "v1", "runs"]:
                graft_run_id = parts[3]
                graft_tenant_id = str(
                    environ.get("HTTP_X_GRAFT-TENANT", environ.get("HTTP_X_GRAFT_TENANT", ""))
                )
                if method == "GET":
                    return self._json(
                        start_response,
                        200,
                        self.service.get_run(graft_tenant_id, graft_run_id).to_dict(),
                    )
            if len(parts) == 5 and parts[:3] == ["", "v1", "runs"]:
                graft_run_id = parts[3]
                graft_tenant_id = str(
                    environ.get("HTTP_X_GRAFT_TENANT", environ.get("HTTP_X_GRAFT_TENANT", ""))
                )
                if parts[4] == "events" and method == "GET":
                    query = parse_qs(urlsplit(str(environ.get("RAW_URI", ""))).query)
                    after = int(query.get("after_graft_event_id", ["0"])[0])
                    events = self.service.replay_events(graft_tenant_id, graft_run_id, after)
                    return self._json(start_response, 200, [event.to_dict() for event in events])
                if parts[4] == "cancel" and method == "POST":
                    return self._json(
                        start_response,
                        202,
                        self.service.cancel_run(graft_tenant_id, graft_run_id).to_dict(),
                    )
            return self._error(
                start_response, 404, ErrorEnvelope("not_found", "route not found", request_id)
            )
        except IdempotencyConflict as exc:
            return self._error(
                start_response, 409, ErrorEnvelope("idempotency_conflict", str(exc), request_id)
            )
        except (KeyError, TypeError, ValueError) as exc:
            return self._error(
                start_response, 400, ErrorEnvelope("invalid_request", str(exc), request_id)
            )
        except TenantBoundaryError as exc:
            return self._error(
                start_response, 404, ErrorEnvelope("not_found", str(exc), request_id)
            )

    @staticmethod
    def _body(environ: dict[str, object]) -> dict[str, object]:
        stream = environ.get("wsgi.input")
        length = int(str(environ.get("CONTENT_LENGTH", "0") or "0"))
        if stream is None:
            raw = b""
        elif isinstance(stream, ReadableInput):
            raw_value = stream.read(length)
            if not isinstance(raw_value, bytes):
                raise ValueError("wsgi.input.read must return bytes")
            raw = raw_value
        else:
            raise ValueError("wsgi.input must provide a read method")
        value: object = json.loads(raw or b"{}")
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ValueError("request body must be an object")
        return {key: item for key, item in value.items()}

    @staticmethod
    def _string_field(value: object, field: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        return value

    @staticmethod
    def _object_field(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ValueError(f"{field} must be an object")
        return {key: item for key, item in value.items()}

    @classmethod
    def _labels_field(cls, value: object) -> dict[str, str]:
        labels = cls._object_field(value, "trigger.labels")
        result: dict[str, str] = {}
        for key, label in labels.items():
            result[key] = cls._string_field(label, f"trigger.labels[{key!r}]")
        return result

    @staticmethod
    def _json(start_response: Callable[..., object], status: int, value: object) -> list[bytes]:
        raw = json.dumps(value, separators=(",", ":")).encode()
        start_response(
            f"{status} {'OK' if status < 300 else 'Accepted'}",
            [("Content-Type", "application/json"), ("Content-Length", str(len(raw)))],
        )
        return [raw]

    @staticmethod
    def _error(
        start_response: Callable[..., object], status: int, error: ErrorEnvelope
    ) -> list[bytes]:
        return HarnessHttpApplication._json(start_response, status, error.to_dict())
