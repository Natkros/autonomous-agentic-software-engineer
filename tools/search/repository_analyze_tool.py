"""``repository.analyze`` — a READ_ONLY tool wrapping the Phase 2 scanner.

Rescans the repository on every call rather than caching a persistent
index keyed by repository — a deliberate simplification for this phase
(there is no index-storage service yet), not an oversight: the tool's
input signature (just a path) makes that scope obvious to any caller.
"""
from __future__ import annotations

from pydantic import BaseModel

from code_intelligence.indexing.repository_scanner import RepositoryScanner
from core.policies.permissions import PermissionLevel
from tools.base import Tool


class RepositoryAnalyzeParams(BaseModel):
    repository_path: str


class RepositoryAnalyzeTool(Tool):
    name = "repository.analyze"
    description = "Scan a repository on disk: file tree, dependencies, frameworks, and AST-based symbols."
    permission = PermissionLevel.READ_ONLY
    timeout_seconds = 60.0
    input_schema = RepositoryAnalyzeParams

    def _execute(self, params: RepositoryAnalyzeParams) -> dict:
        index = RepositoryScanner().scan(params.repository_path)
        return index.to_dict()
