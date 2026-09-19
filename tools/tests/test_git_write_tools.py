import os
import subprocess
import tempfile

from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.git.git_read_tools import GitLogTool
from tools.git.git_repo import GitRepo
from tools.git.git_write_tools import GitBranchTool, GitCommitTool, GitPushTool


def test_branch_creates_and_switches(git_repo):
    result = GitBranchTool().run(
        AuditLog(), AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR,
        repository_path=git_repo, branch_name="agent/task-123",
    )
    assert result.success is True
    assert GitRepo(git_repo).current_branch() == "agent/task-123"


def test_branch_denied_below_git_write_autonomy(git_repo):
    result = GitBranchTool().run(
        AuditLog(), AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
        repository_path=git_repo, branch_name="agent/task-123",
    )
    assert result.success is False
    assert "requires permission" in result.error


def test_commit_creates_a_real_commit(git_repo):
    with open(os.path.join(git_repo, "new_file.py"), "w") as fh:
        fh.write("x = 1\n")

    result = GitCommitTool().run(
        AuditLog(), AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR,
        repository_path=git_repo, message="Add new_file.py",
    )
    assert result.success is True
    assert len(result.output["sha"]) == 40

    log_result = GitLogTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=git_repo)
    assert log_result.output["commits"][0]["message"] == "Add new_file.py"


def test_commit_succeeds_even_without_any_host_git_identity_configured(git_repo, monkeypatch, tmp_path):
    """Regression test for a real bug this project hit: the local dev
    machine happens to have git user.name/user.email configured globally,
    but GitHub Actions' fresh runners don't — commit_all() failed there
    with "Please tell me who you are" until GitRepo started passing an
    explicit identity via GIT_AUTHOR_NAME/EMAIL env vars. This test
    points HOME/USERPROFILE at an empty directory so no global gitconfig
    can be found, simulating exactly that CI condition.
    """
    fake_home = str(tmp_path / "fake_home")
    os.makedirs(fake_home, exist_ok=True)
    monkeypatch.setenv("HOME", fake_home)
    monkeypatch.setenv("USERPROFILE", fake_home)

    with open(os.path.join(git_repo, "new_file.py"), "w") as fh:
        fh.write("x = 1\n")

    result = GitCommitTool().run(
        AuditLog(), AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR,
        repository_path=git_repo, message="Add new_file.py",
    )
    assert result.success is True, result.error


def test_commit_with_nothing_to_commit_fails_cleanly(git_repo):
    result = GitCommitTool().run(
        AuditLog(), AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR,
        repository_path=git_repo, message="empty commit attempt",
    )
    assert result.success is False


def test_push_to_a_real_local_bare_remote(git_repo):
    with tempfile.TemporaryDirectory() as bare_dir:
        subprocess.run(["git", "init", "-q", "--bare", bare_dir], check=True)
        subprocess.run(["git", "remote", "add", "origin", bare_dir], cwd=git_repo, check=True)

        result = GitPushTool().run(
            AuditLog(), AutonomyLevel.LEVEL_4_AUTO_BRANCH_AND_PR,
            repository_path=git_repo, remote="origin",
        )
        assert result.success is True
        assert result.output["pushed"] is True

        # Verify against the real remote, not just the tool's return value.
        log_in_bare = subprocess.run(
            ["git", "log", "--oneline"], cwd=bare_dir, capture_output=True, text=True, check=True,
        )
        assert "initial commit" in log_in_bare.stdout


def test_push_denied_below_git_write_autonomy(git_repo):
    result = GitPushTool().run(
        AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
        repository_path=git_repo, remote="origin",
    )
    assert result.success is False
