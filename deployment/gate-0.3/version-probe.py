#!/usr/bin/env python3
"""Compute one DBOS application version from a physical source file."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import platform
import sys
from importlib.metadata import version as package_version
from pathlib import Path
from types import ModuleType

import dbos
from dbos import DBOS
from dbos._dbos import DBOSRegistry


def _load_source(path: Path) -> ModuleType:
    module_name = "gate_0_3_matrix_source"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load source file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--app-name", required=True)
    args = parser.parse_args()

    source_file = args.source_file.resolve()
    _load_source(source_file)
    instance = DBOS(
        config={
            "name": args.app_name,
            "system_database_url": "sqlite:////tmp/gate-0-3-version-probe.sqlite",
            "executor_id": "gate03-version-probe",
            "run_migrations": False,
        }
    )
    try:
        version_name = instance._registry.compute_app_version(args.app_name)
        workflow_sources = {
            name: inspect.getsource(workflow)
            for name, workflow in sorted(instance._registry.workflow_info_map.items())
        }
        source_path = inspect.getsourcefile(DBOSRegistry.compute_app_version)
        if source_path is None:
            raise RuntimeError("DBOS hash function source path was unavailable")
        hash_source = Path(source_path)
        package_file = dbos.__file__
        if package_file is None:
            raise RuntimeError("DBOS package path was unavailable")
        package_root = Path(package_file).resolve().parent
        source_lines, source_line = inspect.getsourcelines(DBOSRegistry.compute_app_version)
        print(
            json.dumps(
                {
                    "application_name": args.app_name,
                    "application_version": version_name,
                    "dbos_version": package_version("dbos"),
                    "python": platform.python_version(),
                    "source_file_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
                    "workflow_names": sorted(workflow_sources),
                    "workflow_source_sha256": {
                        name: hashlib.sha256(source.encode()).hexdigest()
                        for name, source in workflow_sources.items()
                    },
                    "dbos_hash_provenance": {
                        "module_file": str(hash_source.resolve().relative_to(package_root.parent)),
                        "module_file_sha256": hashlib.sha256(hash_source.read_bytes()).hexdigest(),
                        "function": "DBOSRegistry.compute_app_version",
                        "first_line": source_line,
                        "source_line_count": len(source_lines),
                    },
                },
                sort_keys=True,
            )
        )
    finally:
        DBOS.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
