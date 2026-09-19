from __future__ import annotations

from pydantic import BaseModel

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.filesystem.workspace import Workspace


class FilesystemListParams(BaseModel):
    workspace_root: str
    path: str = "."


class FilesystemListTool(Tool):
    name = "filesystem.list"
    description = "List entries in a directory within a workspace."
    permission = PermissionLevel.READ_ONLY
    input_schema = FilesystemListParams

    def _execute(self, params: FilesystemListParams) -> dict:
        workspace = Workspace(params.workspace_root)
        return {"entries": workspace.list_dir(params.path)}
