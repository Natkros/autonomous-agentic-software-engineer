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


class TaskExecutionError(RuntimeError):
    pass


def execute_task(repository_url: str, user_request: str) -> dict:
    """Clone ``repository_url`` into a throwaway workspace and run the
    Phase 3 agent pipeline (Requirement -> Repository -> Planner -> Coder)
    against it. Returns the final AgentState as a plain dict.

    Uses whichever LLM provider `core.providers.llm_provider.get_default_llm_provider`
    resolves to — MockLLMProvider unless ANTHROPIC_API_KEY is set. Runs
    synchronously on the request thread; there is no background job queue
    yet (Phase 4).
    """
    workspace = tempfile.mkdtemp(prefix="forgeai-task-")
    try:
        clone_dir = os.path.join(workspace, "repo")
        try:
            clone_repository(repository_url, clone_dir)
        except GitCloneError as exc:
            raise TaskExecutionError(f"Could not clone repository: {exc}") from exc

        return run_pipeline(user_request=user_request, repository_path=clone_dir)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
