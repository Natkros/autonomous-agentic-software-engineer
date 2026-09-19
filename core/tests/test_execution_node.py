"""Tests for `execution_node` (core/orchestration/graph.py) — the wiring
that actually reviews, self-corrects, security-scans, and (if autonomy
allows) commits the Coder's proposals, rather than stopping at "proposal
only" like the rest of the pipeline did through Phase 10.

Every assertion here is against a real run: a real temporary git
repository, the real Phase 5 self-correction loop, the real Phase 6
review/security agents, and a real `git commit` — no mocked internals
except the LLM calls themselves (MockLLMProvider).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest

from core.orchestration.graph import run_pipeline
from core.policies.permissions import AutonomyLevel
from core.providers.llm_provider import MockLLMProvider

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git(args: list[str], cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, env=_GIT_ENV, capture_output=True, text=True)


@pytest.fixture()
def real_git_copy_of_fixture():
    """A real, writable, git-initialized copy of the sample_repo fixture —
    a temp directory, not the fixture itself, so the test suite never
    mutates checked-in fixture files.
    """
    with tempfile.TemporaryDirectory() as root:
        repo_dir = os.path.join(root, "repo")
        shutil.copytree(FIXTURE_ROOT, repo_dir)
        _git(["init", "-q"], repo_dir)
        _git(["add", "-A"], repo_dir)
        _git(["commit", "-q", "-m", "initial commit"], repo_dir)
        yield repo_dir


def test_low_autonomy_stops_at_approval_and_writes_nothing():
    """At the conservative default (LEVEL_1_SUGGESTIONS), the execution
    node must review the proposals but never write to disk — it should
    hand back a structured SAFE_WRITE approval request instead.
    """
    final_state = run_pipeline(
        user_request="Add a health check endpoint. Do not break existing routes.",
        repository_path=FIXTURE_ROOT,
        llm_provider=MockLLMProvider(),
        autonomy_level=AutonomyLevel.LEVEL_1_SUGGESTIONS,
    )

    assert final_state["execution_status"] == "AWAITING_APPROVAL"
    assert len(final_state["review_results"]) >= 1
    assert len(final_state["approval_requests"]) == 1
    assert final_state["approval_requests"][0]["action"] == "apply_agent_generated_patches"
    # Nothing was ever applied — the fixture directory is untouched.
    assert final_state["correction_results"] == []
    assert final_state["git_commit"] is None


def test_full_autonomy_applies_tests_and_commits_for_real(real_git_copy_of_fixture):
    """At full autonomy, a safe additive patch should flow all the way
    through: review approves it, self-correction applies and tests it
    successfully on the first iteration (an additive stub can't break the
    existing passing test suite), the security scan doesn't block it, and
    a real `git commit` lands — independently verified here by reading
    the repository's own git log, not just trusting the tool's return
    value.
    """
    final_state = run_pipeline(
        user_request="Add a health check endpoint. Do not break existing routes.",
        repository_path=real_git_copy_of_fixture,
        llm_provider=MockLLMProvider(),
        autonomy_level=AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
    )

    assert final_state["execution_status"] == "COMPLETED", final_state["errors"]
    assert final_state["final_status"] == "COMPLETED", final_state["errors"]

    assert len(final_state["review_results"]) >= 1
    assert len(final_state["correction_results"]) >= 1
    assert final_state["correction_results"][0]["status"] == "success"

    assert final_state["security_scan_result"] is not None

    assert final_state["git_commit"] is not None
    committed_sha = final_state["git_commit"]["sha"]

    log = subprocess.run(
        ["git", "log", "--oneline", "-1"], cwd=real_git_copy_of_fixture,
        check=True, capture_output=True, text=True,
    ).stdout
    assert log.startswith(committed_sha[:7])
    assert "ForgeAI:" in log


def test_execution_status_is_no_patches_proposed_when_coder_has_nothing_to_propose():
    final_state = run_pipeline(
        user_request="Add a feature",
        repository_path="/path/does/not/exist",
        llm_provider=MockLLMProvider(),
        autonomy_level=AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
    )
    assert final_state["execution_status"] == "NO_PATCHES_PROPOSED"
