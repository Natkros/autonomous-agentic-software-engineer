"""GIT_WRITE tools: branch, commit, push. Per the project's design, these
require a higher autonomy level than any tool built in earlier phases
(AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR or above) — see
`core/policies/permissions.py`.
"""
from __future__ import annotations

from pydantic import BaseModel

from core.policies.permissions import PermissionLevel
from tools.base import Tool
from tools.git.git_repo import GitRepo


class GitBranchParams(BaseModel):
    repository_path: str
    branch_name: str


class GitBranchTool(Tool):
    name = "git.branch"
    description = "Create and check out a new branch."
    permission = PermissionLevel.GIT_WRITE
    input_schema = GitBranchParams

    def _execute(self, params: GitBranchParams) -> dict:
        GitRepo(params.repository_path).create_branch(params.branch_name)
        return {"branch": params.branch_name}


class GitCommitParams(BaseModel):
    repository_path: str
    message: str


class GitCommitTool(Tool):
    name = "git.commit"
    description = "Stage all changes and create a commit."
    permission = PermissionLevel.GIT_WRITE
    input_schema = GitCommitParams

    def _execute(self, params: GitCommitParams) -> dict:
        record = GitRepo(params.repository_path).commit_all(params.message)
        return record.model_dump()


class GitPushParams(BaseModel):
    repository_path: str
    remote: str = "origin"
    branch: str | None = None


class GitPushTool(Tool):
    name = "git.push"
    description = "Push the current (or specified) branch to a remote."
    permission = PermissionLevel.GIT_WRITE
    input_schema = GitPushParams

    def _execute(self, params: GitPushParams) -> dict:
        pushed_branch = GitRepo(params.repository_path).push(remote=params.remote, branch=params.branch)
        return {"pushed": True, "remote": params.remote, "branch": pushed_branch}
