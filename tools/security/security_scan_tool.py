"""``security.scan`` — READ_ONLY tool combining static analysis (Python
files) and secret scanning (every file) over a whole workspace directory.
"""
from __future__ import annotations

import os

from pydantic import BaseModel

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.filesystem.workspace import Workspace
from tools.security.secret_scanner import scan_text_for_secrets
from tools.security.static_analysis import analyze_python_source

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache"}
_MAX_FILE_SIZE_BYTES = 1_000_000


class SecurityScanParams(BaseModel):
    workspace_root: str


class SecurityScanTool(Tool):
    name = "security.scan"
    description = "Run static analysis and secret scanning across every file in a workspace."
    permission = PermissionLevel.READ_ONLY
    input_schema = SecurityScanParams

    def _execute(self, params: SecurityScanParams) -> dict:
        workspace = Workspace(params.workspace_root)
        findings = []

        for dirpath, dirnames, filenames in os.walk(workspace.root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, workspace.root).replace(os.sep, "/")

                try:
                    if os.path.getsize(full_path) > _MAX_FILE_SIZE_BYTES:
                        continue
                    with open(full_path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue

                findings.extend(scan_text_for_secrets(content, rel_path))
                if filename.endswith(".py"):
                    findings.extend(analyze_python_source(content, rel_path))

        return {
            "findings": [f.model_dump() for f in findings],
            "blocks_finalization": any(f.severity.value in ("blocker", "high") for f in findings),
        }
