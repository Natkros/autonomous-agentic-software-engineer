from __future__ import annotations

from pydantic import BaseModel

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.filesystem.workspace import Workspace


class FilesystemReadParams(BaseModel):
    workspace_root: str
    path: str


class FilesystemReadTool(Tool):
    name = "filesystem.read"
    description = "Read a text file's contents from within a workspace."
    permission = PermissionLevel.READ_ONLY
    input_schema = FilesystemReadParams

    def _execute(self, params: FilesystemReadParams) -> dict:
        workspace = Workspace(params.workspace_root)
        return {"content": workspace.read_text(params.path)}
