"""Structured patch application (spec section 19): validate, verify syntax,
THEN write — never a blind full-file rewrite from an LLM's raw output.

The new file content is always computed and syntax-checked in memory
before anything touches disk, so there is never a state to roll back from
on verification failure — the write simply never happens. This is
stronger than the spec's literal "backup then roll back" phrasing, not a
shortcut around it: no file on disk is ever observably broken, even
transiently.
"""
from __future__ import annotations

import ast

from pydantic import BaseModel, model_validator

from core.policies.permissions import PermissionLevel
from core.state.schemas import PatchOperation
from tools.base import Tool
from tools.filesystem.workspace import Workspace


class FilesystemPatchParams(BaseModel):
    workspace_root: str
    path: str
    operation: PatchOperation
    content: str | None = None
    start_line: int | None = None  # 1-indexed, inclusive
    end_line: int | None = None  # 1-indexed, inclusive

    @model_validator(mode="after")
    def _validate_combination(self) -> "FilesystemPatchParams":
        if self.operation in (PatchOperation.CREATE_FILE, PatchOperation.INSERT) and self.content is None:
            raise ValueError(f"operation {self.operation} requires 'content'")
        if self.operation == PatchOperation.REPLACE and self.content is None:
            raise ValueError("operation replace requires 'content'")
        if self.operation in (PatchOperation.REPLACE, PatchOperation.DELETE):
            if (self.start_line is None) != (self.end_line is None):
                raise ValueError("start_line and end_line must both be set or both be omitted")
            if self.start_line is not None and self.start_line > self.end_line:
                raise ValueError("start_line must be <= end_line")
        return self


class PatchVerificationError(ValueError):
    pass


def _verify_syntax_if_python(path: str, source: str) -> None:
    if path.endswith(".py"):
        try:
            ast.parse(source, filename=path)
        except SyntaxError as exc:
            raise PatchVerificationError(f"patch produces invalid Python syntax in {path}: {exc}") from exc


class FilesystemPatchTool(Tool):
    name = "filesystem.patch"
    description = "Apply a structured patch (create/replace/insert/delete) to a file, verifying syntax before committing."
    permission = PermissionLevel.SAFE_WRITE
    input_schema = FilesystemPatchParams

    def _execute(self, params: FilesystemPatchParams) -> dict:
        workspace = Workspace(params.workspace_root)

        if params.operation == PatchOperation.CREATE_FILE:
            if workspace.exists(params.path):
                raise FileExistsError(f"{params.path} already exists; use replace to modify it")
            _verify_syntax_if_python(params.path, params.content)
            workspace.write_text(params.path, params.content)
            return {"applied": True, "operation": "create_file"}

        original = workspace.read_text(params.path)
        lines = original.splitlines(keepends=True)

        if params.operation == PatchOperation.REPLACE:
            if params.start_line is None:
                new_source = params.content
            else:
                new_source = "".join(lines[: params.start_line - 1] + [params.content] + lines[params.end_line:])
        elif params.operation == PatchOperation.DELETE:
            new_source = "".join(lines[: params.start_line - 1] + lines[params.end_line:])
        elif params.operation == PatchOperation.INSERT:
            insert_at = (params.start_line - 1) if params.start_line else len(lines)
            new_source = "".join(lines[:insert_at] + [params.content] + lines[insert_at:])
        else:
            raise ValueError(f"Unsupported operation: {params.operation}")

        _verify_syntax_if_python(params.path, new_source)
        workspace.write_text(params.path, new_source)
        return {"applied": True, "operation": params.operation.value}
