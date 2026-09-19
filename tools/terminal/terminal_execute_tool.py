"""``terminal.execute`` — runs a command through a `Sandbox`
(`sandbox/factory.py` picks Docker if a daemon is available, otherwise the
weaker `LocalProcessSandbox`; see `sandbox/README.md` for exactly what
that fallback does and doesn't guarantee).

On top of whatever the underlying sandbox provides, this tool adds two of
its own mitigations regardless of which sandbox is active:

1. The command's working directory is always the workspace root — never
   an arbitrary host path — enforced by constructing a `Workspace` first
   (which validates the root actually exists) before running anything.
2. Only an explicit allowlist of binaries may be invoked (see
   `ALLOWED_BINARIES`), matching the project's own example command list
   (pytest, npm, ruff, mypy, eslint, tsc, go test, ...). Anything else is
   refused before the sandbox ever sees it.
"""
from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

from core.policies.permissions import PermissionLevel
from sandbox.base import Sandbox
from sandbox.factory import get_default_sandbox
from tools.base import Tool
from tools.filesystem.workspace import Workspace

ALLOWED_BINARIES = {
    "python", "python3", "pip", "pytest",
    "npm", "npx", "node",
    "ruff", "mypy", "eslint", "tsc",
    "go", "mvn", "git",
}

_EXECUTABLE_EXTENSIONS = (".exe", ".cmd", ".bat")


def _normalize_binary_name(raw: str) -> str:
    name = os.path.basename(raw).lower()
    for ext in _EXECUTABLE_EXTENSIONS:
        if name.endswith(ext):
            name = name[: -len(ext)]
    return name


class CommandNotAllowedError(ValueError):
    pass


class TerminalExecuteParams(BaseModel):
    workspace_root: str
    command: list[str] = Field(min_length=1)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)

    @field_validator("command")
    @classmethod
    def _validate_allowed_binary(cls, command: list[str]) -> list[str]:
        binary = _normalize_binary_name(command[0])
        if binary not in ALLOWED_BINARIES:
            raise CommandNotAllowedError(
                f"'{command[0]}' is not in the allowed command list ({sorted(ALLOWED_BINARIES)})"
            )
        return command


class TerminalExecuteTool(Tool):
    name = "terminal.execute"
    description = "Run an allowlisted command (pytest, npm, ruff, etc.) inside a sandbox, confined to a workspace."
    permission = PermissionLevel.EXECUTION
    timeout_seconds = 300.0
    input_schema = TerminalExecuteParams

    def __init__(self, sandbox: Sandbox | None = None):
        self.sandbox = sandbox or get_default_sandbox()

    def _execute(self, params: TerminalExecuteParams) -> dict:
        workspace = Workspace(params.workspace_root)  # validates the root exists
        result = self.sandbox.run_command(params.command, cwd=workspace.root, timeout_seconds=params.timeout_seconds)
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
            "success": result.success,
            "sandbox_provided_isolation": self.sandbox.provides_isolation,
        }
