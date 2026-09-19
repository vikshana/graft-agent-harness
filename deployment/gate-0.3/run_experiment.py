#!/usr/bin/env python3
"""Run the bounded, local-only Gate 0.3 DBOS experiment matrix."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import inspect
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import psycopg
from dbos import DBOS, DBOSConfig, SetWorkflowID
from langgraph.graph import END, START, StateGraph

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "specs/phase-1-walking-skeleton/evidence/gate-0.3"
RUNTIME_ENV = ROOT / "deployment/gate-0.3/.env"
APP_DATABASE_URL = "postgresql://gate03@localhost:55432/gate03_app"
SYSTEM_DATABASE_URL = "postgresql://gate03@localhost:55433/gate03_system"
POOLER_DATABASE_URL = "postgresql://gate03@localhost:56432/gate03_app"
REDACTION = "[REDACTED]"
MCP_URL = "http://127.0.0.1:59999/mcp"


def _mcp_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "gate-0-3-synthetic",
        host="127.0.0.1",
        port=59999,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )

    @server.tool()
    def synthetic_tool(value: str, fail: bool = False) -> str:
        if fail:
            raise RuntimeError("synthetic MCP failure injection")
        return f"mcp:{value}"

    return server


def _start_mcp_server() -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "mcp-server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output, _ = process.communicate()
            raise RuntimeError(f"synthetic MCP server exited early: {output}")
        try:
            connection = http.client.HTTPConnection("127.0.0.1", 59999, timeout=0.5)
            try:
                connection.request(
                    "GET",
                    "/mcp",
                    headers={
                        "Accept": "application/json, text/event-stream",
                        "Host": "127.0.0.1:59999",
                    },
                )
                connection.getresponse()
                return process
            finally:
                connection.close()
        except OSError:
            time.sleep(0.1)
    process.terminate()
    output, _ = process.communicate(timeout=5)
    raise TimeoutError(f"synthetic MCP server did not start: {output}")


def _stop_mcp_server(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
    redacted = _redact(output)
    return redacted if isinstance(redacted, str) else str(redacted)


class GraphState(TypedDict):
    value: str


def _no_checkpointer_graph() -> Any:
    graph: StateGraph[GraphState] = StateGraph(GraphState)

    def describe(state: GraphState) -> GraphState:
        return {"value": f"graph:{state['value']}"}

    graph.add_node("describe", describe)
    graph.add_edge(START, "describe")
    graph.add_edge("describe", END)
    return graph.compile()


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return REDACTION if "gate03_local_only" in value else value
    return value


def _write(name: str, value: object) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(_redact(value), indent=2, sort_keys=True) + "\n")


def _write_text(name: str, value: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(value)


def _command(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": _redact(completed.stdout),
        "stderr": _redact(completed.stderr),
    }


def _ensure_runtime_env() -> None:
    RUNTIME_ENV.write_text(
        "# Generated for the local Gate 0.3 throwaway experiment; ignored by git.\n"
        "G03_DB_USER=gate03\n"
        "G03_DB_PASSWORD=gate03_local_only\n"
        "G03_APP_DB=gate03_app\n"
        "G03_SYSTEM_DB=gate03_system\n"
    )


def _versions() -> dict[str, object]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "dbos": _dbos_version(),
        "dbos_config_annotations": sorted(DBOSConfig.__annotations__),
        "dbos_api_signatures": {
            name: str(inspect.signature(getattr(DBOS, name)))
            for name in (
                "launch",
                "destroy",
                "workflow",
                "step",
                "start_workflow_async",
                "list_workflows",
                "get_latest_application_version",
            )
        },
        "docker": _command(["docker", "version", "--format", "{{.Server.Version}}"]),
        "compose": _command(["docker", "compose", "version"]),
        "images": {
            "postgres": _command(
                [
                    "docker",
                    "image",
                    "inspect",
                    "postgres:16",
                    "--format",
                    "{{index .RepoDigests 0}}",
                ]
            ),
            "pgbouncer": _command(
                [
                    "docker",
                    "image",
                    "inspect",
                    "edoburu/pgbouncer:latest",
                    "--format",
                    "{{index .RepoDigests 0}}",
                ]
            ),
        },
    }


def _database_probe() -> dict[str, object]:
    result: dict[str, object] = {}
    for label, url in (
        ("application", os.environ["G03_APP_DATABASE_URL"]),
        ("transaction_mode_pooler", os.environ["G03_POOLER_DATABASE_URL"]),
    ):
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute("select current_database(), current_user")
            database, user = cursor.fetchone()
        result[label] = {"database": database, "user": user, "connected": True}
    return result


def _dbos_version() -> str:
    try:
        from importlib.metadata import version

        return version("dbos")
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        return f"unknown: {exc}"


@DBOS.step()
async def async_step(value: str) -> str:
    await asyncio.sleep(0)
    return f"step:{value}"


@DBOS.step()
async def idempotent_step(key: str, state: dict[str, int]) -> str:
    state[key] = state.get(key, 0) + 1
    return f"idempotent:{key}"


@DBOS.step()
async def graph_step(value: str) -> str:
    result = _no_checkpointer_graph().invoke({"value": value})
    return str(result["value"])


def _mcp_client() -> Any:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    return MultiServerMCPClient(
        {"synthetic": {"transport": "streamable_http", "url": MCP_URL}},
        handle_tool_errors=False,
    )


@DBOS.step()
async def mcp_step(value: str) -> str:
    client = _mcp_client()
    tools = await client.get_tools(server_name="synthetic")
    return str(await tools[0].ainvoke({"value": value, "fail": False}))


@DBOS.step()
async def mcp_failure_step(value: str) -> str:
    try:
        client = _mcp_client()
        tools = await client.get_tools(server_name="synthetic")
        await tools[0].ainvoke({"value": value, "fail": True})
    except Exception as exc:
        return f"injected_failure:{type(exc).__name__}"
    return "injected_failure:not_observed"


@DBOS.workflow()
async def async_workflow(value: str) -> str:
    return await async_step(value)


@DBOS.workflow()
async def graph_mcp_workflow(value: str) -> dict[str, str]:
    return {
        "graph": await graph_step(value),
        "mcp": await mcp_step(value),
        "mcp_failure": await mcp_failure_step(value),
    }


@DBOS.workflow()
async def idempotent_workflow(key: str, state: dict[str, int]) -> str:
    return await idempotent_step(key, state)


async def _run_dbos_experiments() -> dict[str, object]:
    DBOS.destroy()
    config: DBOSConfig = {
        "name": "gate-0-3",
        "system_database_url": os.environ["G03_SYSTEM_DATABASE_URL"],
        "executor_id": "gate03-executor-a",
        "run_migrations": True,
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
    }
    dbos_instance = DBOS(config=config)
    DBOS.launch()
    try:
        async_handle = await DBOS.start_workflow_async(async_workflow, "synthetic")
        async_result = await async_handle.get_result(polling_interval_sec=0.05)
        status = await async_handle.get_status()
        graph_mcp_handle = await DBOS.start_workflow_async(graph_mcp_workflow, "synthetic")
        graph_mcp_result = await graph_mcp_handle.get_result(polling_interval_sec=0.05)
        executor_rows = await DBOS.list_workflows_async(executor_id="gate03-executor-a")
        no_rows = await DBOS.list_workflows_async(executor_id="does-not-exist")
        version_one = await DBOS.get_latest_application_version_async()
        same_source_version = dbos_instance._registry.compute_app_version("gate-0-3")
        same_source_stable = _version_field(version_one, "version_name") == same_source_version

        @DBOS.workflow(name="synthetic_source_change")
        async def changed_workflow(value: str) -> str:
            return f"changed:{value}"

        changed_source_version = dbos_instance._registry.compute_app_version("gate-0-3")
        state: dict[str, int] = {}
        with SetWorkflowID("gate03-idempotent-workflow"):
            first_handle = await DBOS.start_workflow_async(idempotent_workflow, "once", state)
        first_idempotent = await first_handle.get_result(polling_interval_sec=0.05)
        with SetWorkflowID("gate03-idempotent-workflow"):
            second_handle = await DBOS.start_workflow_async(idempotent_workflow, "once", state)
        second_idempotent = await second_handle.get_result(polling_interval_sec=0.05)
        return {
            "async_step": {
                "result": async_result,
                "status": _status_dict(status),
            },
            "langgraph_mcp_dbos": {
                "result": graph_mcp_result,
                "checkpointer_configured": False,
                "decorated_step_boundaries": ["graph_step", "mcp_step", "mcp_failure_step"],
            },
            "conductor_free_executor_filter": {
                "matching_count": len(executor_rows),
                "nonmatching_count": len(no_rows),
                "matching_executor_ids": sorted({row.executor_id for row in executor_rows}),
            },
            "application_version": {
                "registered": _version_dict(version_one),
                "same_source_recomputed": same_source_version,
                "same_source_stable": same_source_stable,
                "changed_source_recomputed": changed_source_version,
                "changed_source_differs": changed_source_version != same_source_version,
            },
            "isolated_idempotent_synthetic": {
                "first_result": first_idempotent,
                "second_result": second_idempotent,
                "attempt_count": state.get("once"),
                "note": (
                    "Repeated identical workflow ID/input was used; this is not "
                    "alive-but-silent recovery proof."
                ),
            },
        }
    finally:
        DBOS.destroy()


def _status_dict(status: object) -> dict[str, object]:
    fields = (
        "workflow_id",
        "status",
        "name",
        "executor_id",
        "app_version",
        "application_version",
    )
    return {field: getattr(status, field, None) for field in fields}


def _version_dict(version: object) -> dict[str, object]:
    if isinstance(version, dict):
        return dict(version)
    return {
        name: getattr(version, name, None)
        for name in ("version_name", "application_name", "created_at")
    }


def _version_field(version: object, field: str) -> object:
    if isinstance(version, dict):
        return version.get(field)
    return getattr(version, field, None)


def _write_mcp_probe() -> dict[str, object]:
    try:
        client = _mcp_client()
        return {
            "capability": "streamable_http_client_constructed",
            "client_type": type(client).__name__,
            "endpoint": MCP_URL,
        }
    except Exception as exc:
        return {"result": "blocked", "error_type": type(exc).__name__, "error": str(exc)}


def _source_change_version() -> dict[str, object]:
    source = inspect.getsource(async_workflow)
    changed_source = source + "\n# synthetic source change\n"
    return {
        "identical_source_hash": hashlib.sha256(source.encode()).hexdigest(),
        "changed_source_hash": hashlib.sha256(changed_source.encode()).hexdigest(),
        "source_change_differs": source != changed_source,
        "result": "requires_second_process/reloaded_workflow_to_measure_DBOS_version_change",
    }


def run() -> int:
    _ensure_runtime_env()
    os.environ.update(
        {
            "G03_APP_DATABASE_URL": f"{APP_DATABASE_URL}?password=gate03_local_only",
            "G03_SYSTEM_DATABASE_URL": f"{SYSTEM_DATABASE_URL}?password=gate03_local_only",
            "G03_POOLER_DATABASE_URL": f"{POOLER_DATABASE_URL}?password=gate03_local_only",
        }
    )
    started = datetime.now(UTC).isoformat()
    mcp_process = _start_mcp_server()
    mcp_probe = _write_mcp_probe()
    result: dict[str, object] = {
        "experiment": "gate-0.3",
        "started_at": started,
        "versions": _versions(),
        "environment": {
            "application_database": "synthetic_local_postgresql_16",
            "system_database": "synthetic_local_postgresql_16",
            "pooler": "transaction_mode_pgbouncer",
            "customer_system_access": False,
            "embedded_real_secrets": False,
            "database_probes": _database_probe(),
        },
        "G03-A": {
            "async_dbos_steps": "pending",
            "langgraph_no_checkpointer": "not_run_in_dbos_matrix",
            "streamable_http_mcp": mcp_probe,
        },
        "G03-B": {
            "alive_but_silent_recovery": "unresolved_public_api_not_safe_to_prove",
            "timeout_is_not_recovery_proof": True,
        },
        "G03-C": "pending",
        "G03-D": "pending",
    }
    try:
        dbos_result = asyncio.run(_run_dbos_experiments())
        result["G03-A"] = {
            "async_dbos_steps": dbos_result.pop("async_step"),
            "langgraph_no_checkpointer": dbos_result.pop("langgraph_mcp_dbos"),
            "streamable_http_mcp": mcp_probe,
        }
        result["G03-B"] = {
            "alive_but_silent_recovery": "unresolved_public_api_not_safe_to_prove",
            "timeout_is_not_recovery_proof": True,
            "isolated_idempotent_synthetic": dbos_result.pop("isolated_idempotent_synthetic"),
        }
        result["G03-C"] = dbos_result.pop("conductor_free_executor_filter")
        application_version = dbos_result.pop("application_version")
        if not isinstance(application_version, dict):
            raise TypeError("DBOS application-version result must be an object")
        result["G03-D"] = {**application_version, "source_change": _source_change_version()}
        result["result"] = "partial_evidence_with_explicit_unresolved_questions"
    except Exception as exc:
        result["result"] = "blocked"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        _write_text("mcp-server.log", _stop_mcp_server(mcp_process))
        result["finished_at"] = datetime.now(UTC).isoformat()
        _write("result.json", result)
        _write(
            "commands.json",
            {
                "compose_config": [
                    "docker",
                    "compose",
                    "-f",
                    "deployment/gate-0.3/docker-compose.yml",
                    "config",
                ],
                "runner": ["uv", "run", "python", "deployment/gate-0.3/run_experiment.py", "run"],
                "cleanup": [
                    "docker",
                    "compose",
                    "-f",
                    "deployment/gate-0.3/docker-compose.yml",
                    "down",
                    "-v",
                ],
            },
        )
    return 0 if result.get("result") != "blocked" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["mcp-server", "prepare", "run", "async-mcp", "listing", "versions"]
    )
    args = parser.parse_args()
    if args.command == "mcp-server":
        import uvicorn

        uvicorn.run(_mcp_server().streamable_http_app(), host="127.0.0.1", port=59999)
        return 0
    if args.command == "prepare":
        _ensure_runtime_env()
        print(f"wrote ignored runtime environment: {RUNTIME_ENV}")
        return 0
    if args.command == "versions":
        print(json.dumps(_redact(_versions()), indent=2, sort_keys=True))
        return 0
    if args.command == "async-mcp":
        return run()
    if args.command == "listing":
        return run()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
