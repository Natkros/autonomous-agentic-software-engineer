import os
import subprocess
import tempfile

import pytest

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git(args: list[str], cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=_GIT_ENV, capture_output=True, text=True)


@pytest.fixture()
def git_repo():
    """A real, freshly-initialized git repository with one commit — not a
    mock. Every git tool test runs actual `git` commands against this.
    """
    with tempfile.TemporaryDirectory() as root:
        _git(["init", "-q"], root)
        with open(os.path.join(root, "README.md"), "w") as fh:
            fh.write("# test repo\n")
        _git(["add", "-A"], root)
        _git(["commit", "-q", "-m", "initial commit"], root)
        yield root
