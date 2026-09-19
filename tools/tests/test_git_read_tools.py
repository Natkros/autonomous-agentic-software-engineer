import os

from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.git.git_read_tools import GitDiffTool, GitLogTool, GitStatusTool


def test_status_reports_clean_repo(git_repo):
    result = GitStatusTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert result.success is True
    assert result.output["clean"] is True
    assert result.output["entries"] == []


def test_status_reports_untracked_and_modified_files(git_repo):
    with open(os.path.join(git_repo, "new_file.py"), "w") as fh:
        fh.write("x = 1\n")
    with open(os.path.join(git_repo, "README.md"), "a") as fh:
        fh.write("more text\n")

    result = GitStatusTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    paths = {e["path"] for e in result.output["entries"]}
    assert "new_file.py" in paths
    assert "README.md" in paths
    assert result.output["clean"] is False


def test_diff_shows_unstaged_changes(git_repo):
    with open(os.path.join(git_repo, "README.md"), "a") as fh:
        fh.write("appended line\n")

    result = GitDiffTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert "appended line" in result.output["diff"]


def test_diff_on_clean_repo_is_empty(git_repo):
    result = GitDiffTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert result.output["diff"] == ""


def test_log_lists_the_initial_commit(git_repo):
    result = GitLogTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert len(result.output["commits"]) == 1
    assert result.output["commits"][0]["message"] == "initial commit"
    assert len(result.output["commits"][0]["sha"]) == 40


def test_read_tools_available_at_lowest_autonomy(git_repo):
    result = GitStatusTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert result.success is True
