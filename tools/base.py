"""The controlled tool interface every agent tool implements.

Per the project's design (section 15): every tool declares a schema, a
description, a minimum permission level, and a timeout, and every
invocation is audit-logged — regardless of whether it succeeds. Agents
never call arbitrary code directly; they only ever go through
``Tool.run()``, which enforces the permission check before the tool's own
logic runs at all.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel

from core.policies.permissions import AutonomyLevel, PermissionDeniedError, PermissionLevel, enforce_permission
from core.state.schemas import ToolCallRecord


@dataclass
class ToolResult:
    success: bool
    output: dict | None = None
    error: str | None = None
    duration_ms: float = 0.0


class AuditLog:
    """An in-memory, ordered record of every tool call made during a run.
    Real and inspectable — not a placeholder — but not yet persisted to the
    database (that lands with the `audit_logs` table in a later phase).
    """

    def __init__(self) -> None:
        self._records: list[ToolCallRecord] = []

    def record(self, tool_name: str, input_summary: str, success: bool, duration_ms: float, error: str | None = None) -> None:
        self._records.append(ToolCallRecord(
            tool_name=tool_name, input_summary=input_summary, success=success,
            duration_ms=duration_ms, error=error,
        ))

    def to_list(self) -> list[dict]:
        return [r.model_dump() for r in self._records]

    def __len__(self) -> int:
        return len(self._records)


class Tool(ABC):
    name: str
    description: str
    permission: PermissionLevel
    timeout_seconds: float = 30.0
    input_schema: type[BaseModel]

    @abstractmethod
    def _execute(self, params: BaseModel) -> dict:
        """Do the actual work. Raise on failure; `run()` handles catching,
        timing, and audit logging uniformly so individual tools don't have
        to reimplement that plumbing.
        """

    def run(self, audit_log: AuditLog, autonomy_level: AutonomyLevel, **kwargs) -> ToolResult:
        input_summary = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())[:500]
        start = time.monotonic()

        try:
            enforce_permission(self.name, self.permission, autonomy_level)
            params = self.input_schema.model_validate(kwargs)
            output = self._execute(params)
            duration_ms = (time.monotonic() - start) * 1000
            audit_log.record(self.name, input_summary, success=True, duration_ms=duration_ms)
            return ToolResult(success=True, output=output, duration_ms=duration_ms)
        except PermissionDeniedError as exc:
            duration_ms = (time.monotonic() - start) * 1000
            audit_log.record(self.name, input_summary, success=False, duration_ms=duration_ms, error=str(exc))
            return ToolResult(success=False, error=str(exc), duration_ms=duration_ms)
        except Exception as exc:  # tool-specific failures are still audited
            duration_ms = (time.monotonic() - start) * 1000
            audit_log.record(self.name, input_summary, success=False, duration_ms=duration_ms, error=str(exc))
            return ToolResult(success=False, error=str(exc), duration_ms=duration_ms)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"A tool named '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"No tool registered with name '{name}'") from exc

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())
