"""Real GitHub REST API client for opening a pull request — same pattern
as `core/providers/llm_provider.py`'s `AnthropicLLMProvider` and
`code_intelligence/providers/embeddings.py`'s `OpenAIEmbeddingProvider`:
complete, real code, gated behind an environment variable, and
**NOT exercised in this project's test suite** (no network access or
GitHub token in this development environment). Do not treat this as
verified until someone runs it against a real repository with a real
token.

Deliberately does not push commits itself — that's `git.push`
(`git_write_tools.py`). This only calls the "create a pull request" API
once a branch already exists on the remote.
"""
from __future__ import annotations

import json
import os
import urllib.request


class GitHubClientError(RuntimeError):
    pass


class GitHubPullRequestClient:
    def __init__(self, owner: str, repo: str, token: str | None = None):
        self.owner = owner
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def create_pull_request(self, title: str, head_branch: str, base_branch: str, body: str = "") -> dict:
        if not self.token:
            raise GitHubClientError(
                "GITHUB_TOKEN is not set; cannot call the GitHub API to open a pull request. "
                "The branch/commit/push steps (tools/git/git_write_tools.py) work without it — "
                "only the final PR-creation call needs a token."
            )

        payload = json.dumps({
            "title": title, "head": head_branch, "base": base_branch, "body": body,
        }).encode("utf-8")

        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise GitHubClientError(f"GitHub API request failed: {exc}") from exc
