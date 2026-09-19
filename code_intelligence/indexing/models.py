"""Data structures produced by a repository scan."""
from __future__ import annotations

from dataclasses import dataclass, field

from code_intelligence.ast_tools.symbols import ImportRecord, Symbol


@dataclass
class FileRecord:
    path: str  # repo-relative, forward-slash separated
    language: str
    size_bytes: int
    is_test: bool
    is_config: bool
    is_entry_point: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "size_bytes": self.size_bytes,
            "is_test": self.is_test,
            "is_config": self.is_config,
            "is_entry_point": self.is_entry_point,
        }


@dataclass
class Dependency:
    name: str
    version: str | None
    source_file: str
    ecosystem: str  # "python" | "javascript"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "source_file": self.source_file,
            "ecosystem": self.ecosystem,
        }


@dataclass
class RepositoryIndex:
    root: str
    files: list[FileRecord] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportRecord] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    api_routes: list[dict] = field(default_factory=list)
    db_models: list[dict] = field(default_factory=list)
    readme_summary: str | None = None
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "file_count": len(self.files),
            "files": [f.to_dict() for f in self.files],
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "frameworks": self.frameworks,
            "entry_points": self.entry_points,
            "config_files": self.config_files,
            "test_files": self.test_files,
            "api_routes": self.api_routes,
            "db_models": self.db_models,
            "readme_summary": self.readme_summary,
            "parse_errors": self.parse_errors,
        }
