from __future__ import annotations

from pydantic import BaseModel

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.filesystem.workspace import Workspace


class FilesystemWriteParams(BaseModel):
    workspace_root: str
    path: str
    content: str


class FilesystemWriteTool(Tool):
    name = "filesystem.write"
    description = "Create or overwrite a text file within a workspace."
    permission = PermissionLevel.SAFE_WRITE
    input_schema = FilesystemWriteParams

    def _execute(self, params: FilesystemWriteParams) -> dict:
        workspace = Workspace(params.workspace_root)
        bytes_written = workspace.write_text(params.path, params.content)
        return {"bytes_written": bytes_written}


class FilesystemDeleteParams(BaseModel):
    workspace_root: str
    path: str


class FilesystemDeleteTool(Tool):
    name = "filesystem.delete"
    description = "Delete a single file within a workspace. Refuses directories."
    permission = PermissionLevel.SAFE_WRITE
    input_schema = FilesystemDeleteParams

    def _execute(self, params: FilesystemDeleteParams) -> dict:
        workspace = Workspace(params.workspace_root)
        workspace.delete_file(params.path)
        return {"deleted": params.path}
