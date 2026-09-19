"""Bridges the API to the standalone `core`/`agents` packages (Phase 3).

Same documented simplification as `analysis_service.py`: `core` and
`agents` live at the repository root, not yet packaged as installable
dependencies, so this module adds the repo root to `sys.path` at import
time. See that file's docstring for the full rationale.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from code_intelligence.indexing.git_ingest import GitCloneError, clone_repository  # noqa: E402
from core.orchestration.graph import run_pipeline  # noqa: E402
from core.policies.permissions import AutonomyLevel  # noqa: E402


class TaskExecutionError(RuntimeError):
    pass


def execute_task(repository_url: str, user_request: str, autonomy_level: int = 1) -> dict:
    """Clone ``repository_url`` into a throwaway workspace and run the full
    agent pipeline (Requirement -> Repository -> Planner -> Coder ->
    Execution) against it. Returns the final AgentState as a plain dict.

    ``autonomy_level`` (0-5, see `core/policies/permissions.py`) bounds what
    the execution node is allowed to do without a human in the loop: at the
    default (1, LEVEL_1_SUGGESTIONS), nothing is written to the cloned
    repository — the response's `patch_proposals` and `approval_requests`
    are what a human would review. Raising it lets the pipeline actually
    apply, test, and (at 4+) commit approved patches — still only inside
    this throwaway clone, which is deleted once the request finishes; none
    of this ever pushes anywhere (`git.push` isn't called by this pipeline).

    Uses whichever LLM provider `core.providers.llm_provider.get_default_llm_provider`
    resolves to — MockLLMProvider unless ANTHROPIC_API_KEY is set. Runs
    synchronously on the request thread; there is no background job queue
    yet.
    """
    workspace = tempfile.mkdtemp(prefix="forgeai-task-")
    try:
        clone_dir = os.path.join(workspace, "repo")
        try:
            clone_repository(repository_url, clone_dir)
        except GitCloneError as exc:
            raise TaskExecutionError(f"Could not clone repository: {exc}") from exc

        return run_pipeline(
            user_request=user_request, repository_path=clone_dir,
            autonomy_level=AutonomyLevel(autonomy_level),
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
