"""``test.run`` — runs pytest against a workspace through a `Sandbox` and
parses the real pass/fail/error/skip counts out of pytest's own summary
line, rather than just returning a raw exit code.

Uses `sys.executable -m pytest` (this interpreter's own pytest) rather
than a bare `pytest` on PATH, so it works regardless of which environment
invoked the tool.
"""
from __future__ import annotations

import re
import sys

from pydantic import BaseModel, Field

from core.policies.permissions import PermissionLevel
from sandbox.base import Sandbox
from sandbox.factory import get_default_sandbox
from tools.base import Tool
from tools.filesystem.workspace import Workspace

_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error(?:s)?|skipped)")


def parse_pytest_summary(output: str) -> dict:
    """Extract counts from pytest's final summary line, e.g.
    ``2 failed, 3 passed, 1 skipped in 0.42s``. Any category not present
    in the output is reported as 0 — pytest omits zero-count categories.
    """
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for match in _COUNT_RE.finditer(output):
        number, category = int(match.group(1)), match.group(2)
        key = "error" if category.startswith("error") else category
        counts[key] = number
    return counts


class RunTestsParams(BaseModel):
    workspace_root: str
    test_path: str = "."
    timeout_seconds: float = Field(default=120.0, gt=0, le=600)


class RunTestsTool(Tool):
    name = "test.run"
    description = "Run pytest against a workspace and report parsed pass/fail/error/skip counts."
    permission = PermissionLevel.EXECUTION
    timeout_seconds = 600.0
    input_schema = RunTestsParams

    def __init__(self, sandbox: Sandbox | None = None):
        self.sandbox = sandbox or get_default_sandbox()

    def _execute(self, params: RunTestsParams) -> dict:
        workspace = Workspace(params.workspace_root)
        command = [sys.executable, "-m", "pytest", params.test_path, "--tb=short", "-q"]
        result = self.sandbox.run_command(command, cwd=workspace.root, timeout_seconds=params.timeout_seconds)

        counts = parse_pytest_summary(result.stdout)
        # Exit code 5 = pytest collected zero tests; distinct from a real failure.
        no_tests_collected = result.exit_code == 5

        return {
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "counts": counts,
            "all_passed": (not result.timed_out) and result.exit_code == 0,
            "no_tests_collected": no_tests_collected,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
