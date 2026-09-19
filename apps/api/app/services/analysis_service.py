"""Bridges the API to the standalone `code_intelligence` package (Phase 2).

`code_intelligence` lives at the repository root, outside `apps/api`, as its
own independently testable package (see code_intelligence/README.md). It is
not yet published/installed as a proper dependency of the API service, so
this module adds the repository root to `sys.path` at import time. This is
a deliberate, documented simplification for Phase 2 — packaging
`code_intelligence` as an installable dependency (or moving it into the
Docker build context) is a cleanup item for a later phase, not something to
silently work around forever.
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
from code_intelligence.indexing.repository_scanner import RepositoryScanner  # noqa: E402


class RepositoryAnalysisError(RuntimeError):
    pass


def analyze_repository(url: str) -> dict:
    """Clone ``url`` into a throwaway workspace, scan it, and return the
    resulting index as a JSON-serializable dict. Raises
    RepositoryAnalysisError (never a raw GitCloneError) on failure so the
    caller has one exception type to handle.

    This runs synchronously on the request thread. Phase 2 has no background
    job queue yet (Celery/Redis workers are Phase 4) — for a large
    repository this endpoint will block until the clone and scan finish.
    """
    workspace = tempfile.mkdtemp(prefix="forgeai-analyze-")
    try:
        clone_dir = os.path.join(workspace, "repo")
        try:
            clone_repository(url, clone_dir)
        except GitCloneError as exc:
            raise RepositoryAnalysisError(f"Could not clone repository: {exc}") from exc

        index = RepositoryScanner().scan(clone_dir)
        return index.to_dict()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
