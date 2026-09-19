"""A thin, real wrapper around the system `git` binary — same approach as
`code_intelligence/indexing/git_ingest.py`'s clone helper: shell out to
git directly rather than add a GitPython dependency for a handful of
commands. Every method here actually runs `git` and parses its real
output; nothing is simulated.
"""
from __future__ import annotations

import subprocess

from core.state.schemas import GitCommitRecord, GitStatusEntry


class GitCommandError(RuntimeError):
    pass


class GitRepo:
    def __init__(self, repository_path: str):
        self.repository_path = repository_path

    def _run(self, args: list[str], timeout: float = 30.0) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.repository_path, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise GitCommandError((result.stderr or result.stdout).strip() or f"git {' '.join(args)} failed")
        return result.stdout

    def status(self) -> list[GitStatusEntry]:
        output = self._run(["status", "--porcelain"])
        entries = []
        for line in output.splitlines():
            if not line:
                continue
            entries.append(GitStatusEntry(status_code=line[:2], path=line[3:].strip()))
        return entries

    def diff(self, staged: bool = False) -> str:
        args = ["diff", "--staged"] if staged else ["diff"]
        return self._run(args)

    def log(self, max_count: int = 10) -> list[GitCommitRecord]:
        output = self._run(["log", f"-{max_count}", "--pretty=format:%H\t%s"])
        commits = []
        for line in output.splitlines():
            if not line:
                continue
            sha, _, message = line.partition("\t")
            commits.append(GitCommitRecord(sha=sha, message=message))
        return commits

    def current_branch(self) -> str:
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"]).strip()

    def create_branch(self, branch_name: str) -> None:
        self._run(["checkout", "-b", branch_name])

    def commit_all(self, message: str) -> GitCommitRecord:
        self._run(["add", "-A"])
        self._run(["commit", "-m", message])
        sha = self._run(["rev-parse", "HEAD"]).strip()
        return GitCommitRecord(sha=sha, message=message)

    def push(self, remote: str = "origin", branch: str | None = None) -> str:
        branch = branch or self.current_branch()
        self._run(["push", remote, branch])
        return branch
