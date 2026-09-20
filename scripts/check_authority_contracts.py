#!/usr/bin/env python3
"""Check the closed Gate 1 Task 2 internal authority contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/authority-internal-v1.openapi.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    try:
        document = json.loads(CONTRACT.read_text(encoding="utf-8"))
        require(document.get("openapi") == "3.1.0", "OpenAPI 3.1 required")
        require(document.get("x-graft-test-only-boundary"), "test-only boundary must be explicit")
        paths = document.get("paths", {})
        require(
            set(paths)
            == {
                "/internal/authority/v1/surface-resolution",
                "/internal/authority/v1/run-capability-mint",
            },
            "exactly two internal routes required",
        )
        security = document.get("components", {}).get("securitySchemes", {})
        require(set(security) == {"mutualTLS"}, "only mutual TLS security scheme is allowed")
        require(security["mutualTLS"].get("type") == "mutualTLS", "mutualTLS scheme type")
        for path, item in paths.items():
            operation = item.get("post", {})
            require(operation.get("security") == [{"mutualTLS": []}], f"{path} is not mTLS-only")
            request = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            require(bool(isinstance(request, dict) and request), f"{path} request schema missing")
            require(
                "Authorization" not in json.dumps(operation), f"{path} mentions bearer fallback"
            )
        schemas = document.get("components", {}).get("schemas", {})
        required = {
            "SurfaceResolutionRequest",
            "RunCapabilityMintRequest",
            "SurfaceResolutionResponse",
            "RunCapabilityMintResponse",
            "VerifiedIdentity",
            "WebhookEnvelope",
        }
        require(required <= set(schemas), "authority schemas incomplete")
        for name in (
            "WebhookEnvelope",
            "Source",
            "Event",
            "Delivery",
            "Alert",
            "VerifiedIdentity",
            "AuditActor",
            "FirstResolution",
            "ResolutionAllow",
            "ResolutionDeny",
            "MintAllow",
            "MintDeny",
            "ProtocolError",
        ):
            schema = schemas[name]
            require(schema.get("additionalProperties") is False, f"{name} must be closed")
        text = json.dumps(document).lower()
        require("duplicate" not in text, "Token Service duplicate result is forbidden")
        require("test-only" in text, "the contract must be labelled test-only")
        require(
            "graft_capability_token" not in json.dumps(schemas["ResolutionAllow"]),
            "resolution must not contain a token",
        )
        require(
            "graft_run_id" not in json.dumps(schemas["ResolutionAllow"]),
            "resolution must not contain a Run",
        )
    except (AssertionError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"authority contract check failed: {exc}", file=sys.stderr)
        return 1
    print("authority contract check passed: closed v1 two-call mTLS schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
