#!/usr/bin/env python3
"""Launch one DBOS version in one disposable, version-specific system schema."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import platform
import sys
from pathlib import Path
from types import ModuleType

import psycopg
from dbos import DBOS, DBOSConfig

APP_NAME = "gate-0-3-db-version-compare"
WORKFLOW_INPUT = "gate-0-3-version-fingerprint"
VERSION_FIELDS = (
    "version_name",
    "version_id",
    "application_name",
    "created_at",
    "version_timestamp",
)
STATUS_FIELDS = (
    "workflow_id",
    "status",
    "name",
    "executor_id",
    "app_version",
    "application_version",
    "application_name",
)


def _load_helper_source(path: Path) -> ModuleType:
    module_name = "gate_0_3_runtime_helper_source"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load helper source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _value_fields(value: object, fields: tuple[str, ...]) -> dict[str, object]:
    if isinstance(value, dict):
        return {field: value.get(field) for field in fields}
    return {field: getattr(value, field, None) for field in fields}


def _all_distributions() -> list[dict[str, str]]:
    distributions = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if name is not None:
            distributions.append({"name": name, "version": distribution.version})
    return sorted(distributions, key=lambda item: (item["name"].lower(), item["version"]))


def _system_database_probe(url: str, schema: str) -> dict[str, object]:
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select current_database(), current_user, current_schema(),
                   current_setting('search_path'), version()
            """
        )
        database, user, current_schema, search_path, server_version = cursor.fetchone()
        cursor.execute(
            """
            select nspname
            from pg_namespace
            where nspname = %s
            """,
            (schema,),
        )
        schema_exists = cursor.fetchone() is not None
        cursor.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = %s
            order by table_name
            """,
            (schema,),
        )
        tables = [str(row[0]) for row in cursor.fetchall()]
        cursor.execute(
            """
            select table_name, column_name
            from information_schema.columns
            where table_schema = %s
              and (lower(table_name) like '%%migration%%'
                   or lower(table_name) like '%%schema%%'
                   or lower(column_name) like '%%migration%%'
                   or lower(column_name) like '%%schema%%')
            order by table_name, ordinal_position
            """,
            (schema,),
        )
        migration_columns = [
            {"table": str(table), "column": str(column)} for table, column in cursor.fetchall()
        ]
        migration_records: list[dict[str, object]] = []
        if "dbos_migrations" in tables:
            cursor.execute(f'SELECT * FROM "{schema}"."dbos_migrations" ORDER BY 1')
            columns = [str(description[0]) for description in cursor.description or ()]
            migration_records = [
                {column: str(value) for column, value in zip(columns, row, strict=True)}
                for row in cursor.fetchall()
            ]
    return {
        "database": database,
        "user": user,
        "requested_schema": schema,
        "current_schema_before_dbos": current_schema,
        "search_path_before_dbos": search_path,
        "schema_exists": schema_exists,
        "server_version": server_version,
        "tables_after_launch": tables,
        "migration_and_schema_columns": migration_columns,
        "migration_records": migration_records,
    }


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


async def _run(args: argparse.Namespace) -> dict[str, object]:
    # A helper source imports and registers its workflow at module load time, so
    # clear the process-global registry before loading it.  Each worker is a new
    # process, but this also makes the launch boundary explicit for the probe.
    DBOS.destroy(destroy_registry=True)
    helper_module: ModuleType | None = None
    if args.helper_source:
        helper_module = _load_helper_source(Path(args.helper_source).resolve())
        workflow = helper_module.matrix_workflow
        workflow_source = inspect.getsource(workflow)
    else:

        @DBOS.workflow()
        async def matrix_workflow(value: str) -> str:
            return f"minimal:{value}"

        workflow = matrix_workflow
        workflow_source = inspect.getsource(workflow)

    source_file = (
        Path(args.helper_source).resolve() if args.helper_source else Path(__file__).resolve()
    )
    config: DBOSConfig = {
        "name": args.application_name,
        "system_database_url": args.system_database_url,
        "executor_id": args.executor_id,
        "dbos_system_schema": args.schema,
        "run_migrations": True,
        "use_listen_notify": True,
        "notification_listener_polling_interval_sec": 0.05,
        "notification_coalesce_sec": 0.01,
    }
    DBOS(config=config)
    launched = False
    try:
        DBOS.launch()
        launched = True
        latest = await DBOS.get_latest_application_version_async()
        handle = await DBOS.start_workflow_async(workflow, WORKFLOW_INPUT)
        workflow_id = handle.get_workflow_id()
        workflow_result = await handle.get_result(polling_interval_sec=0.05)
        status = await DBOS.get_workflow_status_async(workflow_id)
        try:
            from dbos._utils import GlobalParams

            global_params = {
                "app_name": GlobalParams.app_name,
                "app_version": GlobalParams.app_version,
                "dbos_version": GlobalParams.dbos_version,
                "executor_id": GlobalParams.executor_id,
            }
        except Exception as exc:  # pragma: no cover - diagnostics for SDK drift
            global_params = {"error": f"{type(exc).__name__}: {exc}"}

        launch_fields = {
            "config_name": config["name"],
            "config_application_version": config.get("application_version"),
            "DBOS_application_version": DBOS.application_version,
            "DBOS_application_name": getattr(DBOS, "application_name", None),
            "GlobalParams": global_params,
            "latest_application_version": _value_fields(latest, VERSION_FIELDS),
            "workflow_status": _value_fields(status, STATUS_FIELDS),
        }
        database = _system_database_probe(args.system_database_url, args.schema)
        source_fingerprint = {
            "workflow_source_sha256": hashlib.sha256(workflow_source.encode()).hexdigest(),
            "source_file_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
            "application_name": args.application_name,
        }
        result: dict[str, object] = {
            "status": "passed",
            "dbos_version": importlib.metadata.version("dbos"),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "resolved_distributions": _all_distributions(),
            "application_name": args.application_name,
            "executor_id": args.executor_id,
            "system_database_endpoint": args.system_database_url.split("?")[0],
            "system_schema": args.schema,
            "source_fingerprint": source_fingerprint,
            "launch_runtime_application_version_fields": launch_fields,
            "workflow": {
                "workflow_id": workflow_id,
                "input": WORKFLOW_INPUT,
                "result": workflow_result,
            },
            "system_database_schema_and_migrations": database,
            "helper_runtime": {
                "source_variant": args.helper_source,
                "helper_result_is_runtime_observation": bool(args.helper_source),
                "note": (
                    "The helper variant was imported, launched, and executed by DBOS; "
                    "this is separate from the source-only hash probe."
                    if args.helper_source
                    else "No helper variant was requested."
                ),
            },
        }
        result["result_fingerprint"] = _fingerprint(
            {
                "dbos_version": result["dbos_version"],
                "python": result["python"],
                "application_name": result["application_name"],
                "source_fingerprint": source_fingerprint,
                "launch_runtime_application_version_fields": launch_fields,
                "workflow_result": workflow_result,
                "system_schema": args.schema,
                "system_tables": database["tables_after_launch"],
            }
        )
        return result
    finally:
        if launched:
            DBOS.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-database-url", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--application-name", default=APP_NAME)
    parser.add_argument("--helper-source")
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(_run(args)), sort_keys=True), flush=True)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "dbos_version": importlib.metadata.version("dbos"),
                    "python": platform.python_version(),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
