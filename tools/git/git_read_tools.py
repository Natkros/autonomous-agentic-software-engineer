"""READ_ONLY git tools: status, diff, log."""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.git.git_repo import GitRepo


class GitPathParams(BaseModel):
    repository_path: str


class GitStatusTool(Tool):
    name = "git.status"
    description = "List changed/untracked files in a git working tree."
    permission = PermissionLevel.READ_ONLY
    input_schema = GitPathParams

    def _execute(self, params: GitPathParams) -> dict:
        entries = GitRepo(params.repository_path).status()
        return {"entries": [e.model_dump() for e in entries], "clean": len(entries) == 0}


class GitDiffParams(BaseModel):
    repository_path: str
    staged: bool = False


class GitDiffTool(Tool):
    name = "git.diff"
    description = "Show the unified diff of unstaged (or staged) changes."
    permission = PermissionLevel.READ_ONLY
    input_schema = GitDiffParams

    def _execute(self, params: GitDiffParams) -> dict:
        return {"diff": GitRepo(params.repository_path).diff(staged=params.staged)}


class GitLogParams(BaseModel):
    repository_path: str
    max_count: int = Field(default=10, ge=1, le=200)


class GitLogTool(Tool):
    name = "git.log"
    description = "List the most recent commits (sha + message)."
    permission = PermissionLevel.READ_ONLY
    input_schema = GitLogParams

    def _execute(self, params: GitLogParams) -> dict:
        commits = GitRepo(params.repository_path).log(max_count=params.max_count)
        return {"commits": [c.model_dump() for c in commits]}
