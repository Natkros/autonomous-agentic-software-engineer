import pytest

from tools.git.github_client import GitHubClientError, GitHubPullRequestClient


def test_create_pull_request_without_token_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    client = GitHubPullRequestClient(owner="example", repo="demo")

    with pytest.raises(GitHubClientError):
        client.create_pull_request(title="Add feature", head_branch="agent/task-1", base_branch="main")


def test_token_can_be_passed_explicitly_instead_of_env_var(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    client = GitHubPullRequestClient(owner="example", repo="demo", token="explicit-token")
    assert client.token == "explicit-token"
