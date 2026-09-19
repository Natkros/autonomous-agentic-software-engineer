"""``symbol.search`` — a READ_ONLY tool for exact/prefix lookup by symbol
name. Distinct from ``code.search``: this is a plain structural lookup over
extracted symbols (no embeddings, no ranking heuristics), for when the
caller already knows the name they're looking for.
"""
from __future__ import annotations

from pydantic import BaseModel

from code_intelligence.indexing.repository_scanner import RepositoryScanner
from core.policies.permissions import PermissionLevel
from tools.base import Tool


class SymbolSearchParams(BaseModel):
    repository_path: str
    symbol_name: str


class SymbolSearchTool(Tool):
    name = "symbol.search"
    description = "Exact/prefix lookup of a function, class, or method by name."
    permission = PermissionLevel.READ_ONLY
    timeout_seconds = 60.0
    input_schema = SymbolSearchParams

    def _execute(self, params: SymbolSearchParams) -> dict:
        index = RepositoryScanner().scan(params.repository_path)
        query = params.symbol_name.lower()
        matches = [
            s.to_dict() for s in index.symbols
            if query == s.name.lower() or query == s.qualified_name().lower() or s.name.lower().startswith(query)
        ]
        return {"matches": matches}
