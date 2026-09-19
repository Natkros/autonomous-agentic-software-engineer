"""A lightweight, file-level import graph.

Scope note: this resolves *import* relationships (which file imports which
module, and — where the target is inside the same repository — which file
that resolves to). It does NOT build a call graph (which function calls
which function) or a full symbol dependency graph; those require resolving
name bindings across files, which is out of scope for this phase. Answering
"which functions call this method?" from the project's design goals is
therefore not yet possible — only "which files import this module?" is.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from code_intelligence.ast_tools.symbols import ImportRecord


@dataclass
class ImportGraph:
    # file path -> set of file paths it imports (only edges resolved to a
    # file that exists within the scanned repository)
    edges: dict[str, set[str]] = field(default_factory=dict)
    # file path -> set of external (unresolved / third-party) module names
    external: dict[str, set[str]] = field(default_factory=dict)

    def importers_of(self, file_path: str) -> list[str]:
        """Which files import ``file_path`` (reverse edge lookup)."""
        return sorted(src for src, targets in self.edges.items() if file_path in targets)

    def to_dict(self) -> dict:
        return {
            "edges": {k: sorted(v) for k, v in self.edges.items()},
            "external": {k: sorted(v) for k, v in self.external.items()},
        }


def _resolve_python_module(module: str, from_file: str, all_files: set[str]) -> str | None:
    module_path = module.replace(".", "/")
    for suffix in ("/__init__.py", ".py"):
        candidate = module_path + suffix
        if candidate in all_files:
            return candidate
        # also try resolved relative to the importing file's directory
        local_candidate = os.path.normpath(os.path.join(os.path.dirname(from_file), candidate)).replace("\\", "/")
        if local_candidate in all_files:
            return local_candidate
    return None


def build_import_graph(imports: list[ImportRecord], all_file_paths: list[str]) -> ImportGraph:
    all_files = set(all_file_paths)
    graph = ImportGraph()

    for record in imports:
        graph.edges.setdefault(record.file_path, set())
        graph.external.setdefault(record.file_path, set())

        if not record.module:
            continue

        resolved = None
        if record.file_path.endswith(".py"):
            resolved = _resolve_python_module(record.module, record.file_path, all_files)

        if resolved and resolved != record.file_path:
            graph.edges[record.file_path].add(resolved)
        else:
            graph.external[record.file_path].add(record.module)

    return graph
