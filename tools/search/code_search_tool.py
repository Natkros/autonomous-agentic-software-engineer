"""``code.search`` — a READ_ONLY tool wrapping Phase 2's hybrid retriever
(semantic + keyword + symbol + file-path search combined)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from code_intelligence.indexing.repository_scanner import RepositoryScanner
from code_intelligence.retrieval.hybrid_search import HybridRetriever
from core.policies.permissions import PermissionLevel
from tools.base import Tool


class CodeSearchParams(BaseModel):
    repository_path: str
    query: str
    top_k: int = Field(default=10, ge=1, le=50)


class CodeSearchTool(Tool):
    name = "code.search"
    description = "Hybrid semantic+keyword+symbol+path search over a repository's code."
    permission = PermissionLevel.READ_ONLY
    timeout_seconds = 60.0
    input_schema = CodeSearchParams

    def _execute(self, params: CodeSearchParams) -> dict:
        index = RepositoryScanner().scan(params.repository_path)
        retriever = HybridRetriever(index)
        results = retriever.search(params.query, top_k=params.top_k)
        return {"results": [r.to_dict() for r in results]}
