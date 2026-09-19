"""Shared symbol data structures used by every language extractor."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    kind: str  # "function" | "class" | "method" | "import"
    file_path: str
    lineno: int
    end_lineno: int
    parent: str | None = None
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    docstring: str | None = None

    def qualified_name(self) -> str:
        return f"{self.parent}.{self.name}" if self.parent else self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "parent": self.parent,
            "decorators": self.decorators,
            "bases": self.bases,
            "docstring": self.docstring,
            "qualified_name": self.qualified_name(),
        }


@dataclass
class ImportRecord:
    module: str
    file_path: str
    lineno: int
    names: list[str] = field(default_factory=list)
    is_relative: bool = False

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "file_path": self.file_path,
            "lineno": self.lineno,
            "names": self.names,
            "is_relative": self.is_relative,
        }
