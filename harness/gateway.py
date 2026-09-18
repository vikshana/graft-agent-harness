"""Read-only Tool Gateway boundary with curated descriptions and pointers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .security import CapabilityAuthority


@dataclass(frozen=True, slots=True)
class ArtifactPointer:
    graft_artifact_id: str
    content_type: str
    byte_length: int


@dataclass(frozen=True, slots=True)
class CuratedTool:
    graft_tool_name: str
    tool_class: str
    input_schema: dict[str, Any]
    invoke: Callable[[dict[str, Any]], tuple[str, int]]


class ToolGateway:
    def __init__(self, authority: CapabilityAuthority, tools: dict[str, CuratedTool]) -> None:
        self._authority = authority
        self._tools = dict(tools)

    def call(
        self,
        *,
        token: str,
        graft_run_id: str,
        graft_tenant_id: str,
        graft_tool_name: str,
        arguments: dict[str, Any],
    ) -> ArtifactPointer:
        tool = self._tools.get(graft_tool_name)
        if tool is None:
            raise LookupError("unknown curated Tool")
        self._authority.validate(
            token,
            graft_run_id=graft_run_id,
            graft_tenant_id=graft_tenant_id,
            required_tool_class=tool.tool_class,
        )
        self._validate_arguments(tool.input_schema, arguments)
        graft_artifact_id, byte_length = tool.invoke(dict(arguments))
        return ArtifactPointer(graft_artifact_id, "application/json", byte_length)

    @staticmethod
    def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
        required = set(schema.get("required", []))
        if not required <= arguments.keys():
            raise ValueError("Tool arguments are missing required fields")
        properties = schema.get("properties", {})
        for key, value in arguments.items():
            expected = properties.get(key, {}).get("type")
            if expected == "string" and not isinstance(value, str):
                raise ValueError(f"Tool argument {key!r} must be a string")
            if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"Tool argument {key!r} must be an integer")
