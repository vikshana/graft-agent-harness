"""Dependency-free HTTP adapter for the transport-independent harness contract.

This WSGI adapter is a reference provider, not an identity authority.  The
``test_verified_identity`` argument is an explicit, test-only composition
seam: it represents the already verified Authority Service result and is never
read from a request body or HTTP header.  Production composition remains
pending the Gate 1 Task 2 Authority Service implementation.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import parse_qs, urlsplit

from .contracts import (
    AlertTrigger,
    ContractValidationError,
    ErrorEnvelope,
    EventReplayPage,
    RunCreateRequest,
    UnsupportedContractVersion,
    validate_run_id,
)
from .service import HarnessService
from .store import IdempotencyConflict, TenantBoundaryError


@runtime_checkable
class ReadableInput(Protocol):
    def read(self, length: int) -> object:
        """Read request bytes from the WSGI input stream."""


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    """The non-wire identity context injected by the reference test seam."""

    graft_tenant_id: str
    graft_principal_id: str

    def validate(self) -> None:
        if not self.graft_tenant_id or not self.graft_principal_id:
            raise ValueError("test verified identity requires Tenant and Principal")


class CursorInvalid(ValueError):
    """Raised when a replay cursor is outside the canonical request shape."""


class HarnessHttpApplication:
    """WSGI reference adapter over the canonical Run contract.

    ``test_verified_identity`` is deliberately named and typed as a test
    seam.  It is the only identity source in this provider; ``X-Graft-*``
    request headers and request-body identity fields are not trusted.
    """

    def __init__(
        self,
        service: HarnessService | None = None,
        *,
        test_verified_identity: VerifiedIdentity | None = None,
    ) -> None:
        self.service = service or HarnessService()
        self.test_verified_identity = test_verified_identity or VerifiedIdentity(
            "tenant-test", "principal-test"
        )
        self.test_verified_identity.validate()

    def __call__(
        self, environ: dict[str, object], start_response: Callable[..., object]
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        request_id = str(environ.get("HTTP_X_GRAFT_REQUEST_ID", "request-local"))
        identity = self.test_verified_identity
        legacy_wire = False
        try:
            if method == "POST" and path == "/v1/runs":
                body = self._body(environ)
                legacy_wire = "trigger" in body and "graft_trigger" not in body
                request = self._create_request(body, environ, identity)
                run, created = self.service.create_run_result(request)
                response = run.to_dict() if legacy_wire else run.to_contract_dict()
                return self._json(
                    start_response,
                    201 if created else 200,
                    response,
                    request_id=request_id,
                )

            parts = path.split("/")
            if len(parts) == 4 and parts[:3] == ["", "v1", "runs"]:
                graft_run_id = parts[3]
                validate_run_id(graft_run_id)
                if method == "GET":
                    return self._json(
                        start_response,
                        200,
                        self.service.get_run(
                            identity.graft_tenant_id, graft_run_id
                        ).to_contract_dict(),
                        request_id=request_id,
                    )
            if len(parts) == 5 and parts[:3] == ["", "v1", "runs"]:
                graft_run_id = parts[3]
                validate_run_id(graft_run_id)
                if parts[4] == "events" and method == "GET":
                    query = parse_qs(
                        urlsplit(self._request_uri(environ)).query,
                        keep_blank_values=True,
                    )
                    replay_mode = query.get("graft_replay_mode", ["replay"])[0]
                    if replay_mode not in {"replay", "follow"}:
                        raise ValueError("graft_replay_mode must be 'replay' or 'follow'")
                    if replay_mode == "follow":
                        raise ValueError("follow mode is not supported by the reference provider")
                    after = self._query_int(query, "after_graft_event_id", 0, minimum=0)
                    limit = self._query_int(
                        query, "graft_event_limit", 100, minimum=1, maximum=1000
                    )
                    all_events = self.service.replay_events(
                        identity.graft_tenant_id, graft_run_id, after
                    )
                    page_events = tuple(all_events[:limit])
                    page = EventReplayPage(
                        graft_run_id,
                        page_events,
                        page_events[-1].graft_event_id if page_events else after,
                        len(all_events) > limit,
                    )
                    return self._json(
                        start_response, 200, page.to_contract_dict(), request_id=request_id
                    )
                if parts[4] == "cancel" and method == "POST":
                    body = self._body(environ)
                    self._validate_cancel_request(body)
                    return self._json(
                        start_response,
                        202,
                        self.service.cancel_run(
                            identity.graft_tenant_id, graft_run_id
                        ).to_contract_dict(),
                        request_id=request_id,
                    )
            return self._error(
                start_response,
                404,
                ErrorEnvelope("not_found", "route not found", request_id),
                legacy=legacy_wire,
            )
        except IdempotencyConflict as exc:
            return self._error(
                start_response,
                409,
                ErrorEnvelope("idempotency_conflict", str(exc), request_id),
                legacy=legacy_wire,
            )
        except TenantBoundaryError as exc:
            return self._error(
                start_response,
                404,
                ErrorEnvelope("not_found", str(exc), request_id),
                legacy=legacy_wire,
            )
        except UnsupportedContractVersion as exc:
            return self._error(
                start_response,
                400,
                ErrorEnvelope("unsupported_contract_version", str(exc), request_id),
                legacy=legacy_wire,
            )
        except CursorInvalid as exc:
            return self._error(
                start_response,
                400,
                ErrorEnvelope("cursor_invalid", str(exc), request_id),
                legacy=legacy_wire,
            )
        except (ContractValidationError, KeyError, TypeError, ValueError) as exc:
            return self._error(
                start_response,
                400,
                ErrorEnvelope("invalid_request", str(exc), request_id),
                legacy=legacy_wire,
            )

    def _create_request(
        self,
        body: dict[str, object],
        environ: dict[str, object],
        identity: VerifiedIdentity,
    ) -> RunCreateRequest:
        # Canonical REST inputs never carry identity.  Rejecting these fields
        # here prevents a caller from confusing an unverified value with the
        # out-of-band identity context.
        if "graft_trigger" in body:
            forbidden = {"graft_tenant_id", "graft_principal_id", "graft_identity"} & body.keys()
            if forbidden:
                raise ValueError("caller-supplied identity fields are not accepted")
            trigger = self._object_field(body["graft_trigger"], "graft_trigger")
            source = self._string_field(trigger.get("graft_source"), "graft_trigger.graft_source")
            alert_id = self._string_field(
                trigger.get("graft_alert_id"), "graft_trigger.graft_alert_id"
            )
            summary = self._string_field(
                trigger.get("graft_summary"), "graft_trigger.graft_summary"
            )
            fingerprint = self._string_field(
                trigger.get("graft_fingerprint"), "graft_trigger.graft_fingerprint"
            )
            labels = self._labels_field(
                trigger.get("graft_labels", {}), "graft_trigger.graft_labels"
            )
            trigger_kind = self._optional_const(body, "graft_trigger_kind", "system_initiated")
            visibility = self._optional_const(body, "graft_visibility", "private")
            tool_classes = self._optional_tool_classes(body.get("graft_tool_classes", ["read"]))
            contract_version = self._optional_const(body, "graft_contract_version", "v1")
        else:
            # Retain the old field spelling solely for the existing synchronous
            # unit adapter.  It is still composed with the verified test seam;
            # body/header identity values are ignored rather than trusted.
            trigger = self._object_field(body.get("trigger"), "trigger")
            source = self._string_field(trigger.get("source"), "trigger.source")
            alert_id = self._string_field(trigger.get("alert_id"), "trigger.alert_id")
            summary = self._string_field(trigger.get("summary"), "trigger.summary")
            fingerprint = self._string_field(trigger.get("fingerprint"), "trigger.fingerprint")
            labels = self._labels_field(trigger.get("labels", {}), "trigger.labels")
            trigger_kind = "system_initiated"
            visibility = "private"
            tool_classes = ("read",)
            contract_version = "v1"

        # The canonical REST idempotency location is the header.  The body
        # spelling is accepted only by the explicitly legacy prototype shape;
        # it must never silently weaken the canonical REST contract.
        if "graft_trigger" in body:
            idempotency_value = environ.get("HTTP_X_GRAFT_IDEMPOTENCY_KEY", "")
        else:
            idempotency_value = environ.get(
                "HTTP_X_GRAFT_IDEMPOTENCY_KEY", body.get("idempotency_key", "")
            )
        idempotency_key = self._string_field(idempotency_value, "X-Graft-Idempotency-Key")
        if not idempotency_key:
            raise ValueError("X-Graft-Idempotency-Key is required")
        if len(idempotency_key) > 256:
            raise ValueError("X-Graft-Idempotency-Key exceeds the contract limit")
        return RunCreateRequest(
            graft_tenant_id=identity.graft_tenant_id,
            graft_principal_id=identity.graft_principal_id,
            idempotency_key=idempotency_key,
            trigger=AlertTrigger(source, alert_id, summary, fingerprint, labels),
            trigger_kind=trigger_kind,
            visibility=visibility,
            tool_classes=tool_classes,
            contract_version=contract_version,
        )

    @classmethod
    def _validate_cancel_request(cls, body: dict[str, object]) -> None:
        """Validate the optional canonical cancellation body before the use case."""

        forbidden = {"graft_tenant_id", "graft_principal_id", "graft_identity"} & body.keys()
        if forbidden:
            raise ValueError("caller-supplied identity fields are not accepted")
        if "graft_reason" in body:
            reason = cls._string_field(body["graft_reason"], "graft_reason")
            if len(reason) > 1024:
                raise ValueError("graft_reason exceeds the contract limit")
        if "graft_contract_version" in body and body["graft_contract_version"] != "v1":
            raise UnsupportedContractVersion("unsupported contract version")

    @staticmethod
    def _request_uri(environ: dict[str, object]) -> str:
        return str(environ.get("RAW_URI", environ.get("PATH_INFO", "/")))

    @staticmethod
    def _query_int(
        query: dict[str, list[str]],
        name: str,
        default: int,
        *,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        try:
            value = int(query.get(name, [str(default)])[0])
        except (TypeError, ValueError) as exc:
            raise CursorInvalid(f"{name} must be an integer") from exc
        if value < minimum or (maximum is not None and value > maximum):
            raise CursorInvalid(f"{name} is outside the contract range")
        return value

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
    def _labels_field(cls, value: object, field: str) -> dict[str, str]:
        labels = cls._object_field(value, field)
        result: dict[str, str] = {}
        for key, label in labels.items():
            result[key] = cls._string_field(label, f"{field}[{key!r}]")
        return result

    @classmethod
    def _optional_const(cls, body: dict[str, object], field: str, expected: str) -> str:
        value = body.get(field, expected)
        if value != expected:
            if field == "graft_contract_version":
                raise UnsupportedContractVersion("unsupported contract version")
            raise ValueError(f"{field} must be {expected!r}")
        return expected

    @classmethod
    def _optional_tool_classes(cls, value: object) -> tuple[str, ...]:
        if value != ["read"] and value != ("read",):
            raise ValueError("graft_tool_classes must be ['read']")
        return ("read",)

    @staticmethod
    def _json(
        start_response: Callable[..., object],
        status: int,
        value: object,
        *,
        request_id: str | None = None,
    ) -> list[bytes]:
        raw = json.dumps(value, separators=(",", ":")).encode()
        reason = {200: "OK", 201: "Created", 202: "Accepted"}.get(status, "Error")
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(raw)))]
        if request_id:
            headers.append(("X-Graft-Request-Id", request_id))
        start_response(
            f"{status} {reason}",
            headers,
        )
        return [raw]

    @staticmethod
    def _error(
        start_response: Callable[..., object],
        status: int,
        error: ErrorEnvelope,
        *,
        legacy: bool = False,
    ) -> list[bytes]:
        return HarnessHttpApplication._json(
            start_response,
            status,
            error.to_dict() if legacy else error.to_contract_dict(),
            request_id=error.graft_request_id,
        )
