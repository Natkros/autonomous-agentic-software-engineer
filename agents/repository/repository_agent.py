"""The Repository Explorer Agent: wraps the Phase 2 `code_intelligence`
scanner into the agent-pipeline interface, distilling a full RepositoryIndex
down to what the Planning Agent actually needs.

Deliberately has no LLM dependency — file tree analysis, language/framework
detection, and symbol counting are deterministic, so there is nothing here
for an LLM to add. This matches the project's own principle: don't spend a
model call on something a direct computation already answers correctly.
"""
from __future__ import annotations

from collections import Counter

from code_intelligence.indexing.models import RepositoryIndex
from code_intelligence.indexing.repository_scanner import RepositoryScanner
from core.state.schemas import RepositorySummary

_MAX_KEY_FILES = 10


class RepositoryExplorerAgent:
    def __init__(self, scanner: RepositoryScanner | None = None):
        self.scanner = scanner or RepositoryScanner()

    def explore(self, repository_path: str) -> RepositorySummary:
        index = self.scanner.scan(repository_path)
        return self._summarize(index)

    @staticmethod
    def _summarize(index: RepositoryIndex) -> RepositorySummary:
        languages = sorted({f.language for f in index.files if f.language != "unknown"})

        symbol_counts_by_file: Counter[str] = Counter(s.file_path for s in index.symbols)
        key_files = list(dict.fromkeys(index.entry_points))  # entry points first, de-duplicated
        for file_path, _ in symbol_counts_by_file.most_common():
            if len(key_files) >= _MAX_KEY_FILES:
                break
            if file_path not in key_files:
                key_files.append(file_path)

        return RepositorySummary(
            root=index.root,
            file_count=len(index.files),
            languages=languages,
            frameworks=index.frameworks,
            entry_points=index.entry_points,
            test_file_count=len(index.test_files),
            symbol_count=len(index.symbols),
            key_files=key_files[:_MAX_KEY_FILES],
            readme_summary=index.readme_summary,
        )
