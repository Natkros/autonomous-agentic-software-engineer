"""Walks a repository on disk and builds a RepositoryIndex.

This is the entry point for Phase 2 "repository understanding": file tree
analysis, language detection, dependency/framework detection, entry-point
and test discovery, README analysis, and AST-based symbol extraction.
"""
from __future__ import annotations

import os

from code_intelligence.ast_tools.extractor import SUPPORTED_LANGUAGES, extract_symbols
from code_intelligence.indexing import dependencies as deps_mod
from code_intelligence.indexing.models import Dependency, FileRecord, RepositoryIndex
from code_intelligence.parsers.language import (
    detect_language,
    is_config_file,
    is_entry_point,
    is_test_file,
    should_ignore_dir,
)

MAX_FILE_SIZE_BYTES = 2_000_000  # skip anything unusually large (generated bundles, etc.)

_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
_ORM_BASE_MARKERS = ("Base", "models.Model", "db.Model")


def _to_repo_relative(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return None


def _extract_readme_summary(root: str) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "readme.md"):
        candidate = os.path.join(root, name)
        if os.path.isfile(candidate):
            text = _read_text(candidate)
            if not text:
                continue
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            if paragraphs:
                return paragraphs[0][:1000]
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            return lines[0][:1000] if lines else None
    return None


def _detect_routes(symbols) -> list[dict]:
    routes = []
    for sym in symbols:
        for decorator in sym.decorators:
            if "." not in decorator:
                continue
            target, _, method = decorator.rpartition(".")
            if method.lower() in _ROUTE_METHODS and target.lower() in ("app", "router"):
                routes.append({
                    "handler": sym.qualified_name(),
                    "method": method.upper(),
                    "file_path": sym.file_path,
                    "lineno": sym.lineno,
                })
    return routes


def _detect_db_models(symbols) -> list[dict]:
    models = []
    for sym in symbols:
        if sym.kind != "class":
            continue
        if any(marker in sym.bases for marker in _ORM_BASE_MARKERS):
            models.append({
                "name": sym.name,
                "file_path": sym.file_path,
                "lineno": sym.lineno,
                "bases": sym.bases,
            })
    return models


class RepositoryScanner:
    """Scans a directory tree once and produces a complete RepositoryIndex."""

    def scan(self, root: str) -> RepositoryIndex:
        if not os.path.isdir(root):
            raise NotADirectoryError(root)

        index = RepositoryIndex(root=root)
        dependency_list: list[Dependency] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not should_ignore_dir(d)]

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = _to_repo_relative(root, full_path)

                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue

                language = detect_language(full_path)
                record = FileRecord(
                    path=rel_path,
                    language=language,
                    size_bytes=size,
                    is_test=is_test_file(rel_path),
                    is_config=is_config_file(full_path),
                    is_entry_point=is_entry_point(full_path),
                )
                index.files.append(record)

                if record.is_config:
                    index.config_files.append(rel_path)
                if record.is_entry_point:
                    index.entry_points.append(rel_path)
                if record.is_test:
                    index.test_files.append(rel_path)

                if filename == "requirements.txt" or filename == "requirements-dev.txt":
                    content = _read_text(full_path)
                    if content:
                        dependency_list.extend(deps_mod.parse_requirements_txt(content, rel_path))
                elif filename == "package.json":
                    content = _read_text(full_path)
                    if content:
                        dependency_list.extend(deps_mod.parse_package_json(content, rel_path))
                elif filename == "pyproject.toml":
                    content = _read_text(full_path)
                    if content:
                        dependency_list.extend(deps_mod.parse_pyproject_toml(content, rel_path))

                if language in SUPPORTED_LANGUAGES and size <= MAX_FILE_SIZE_BYTES:
                    source = _read_text(full_path)
                    if source is None:
                        continue
                    try:
                        symbols, imports = extract_symbols(source, rel_path, language)
                    except ValueError as exc:
                        index.parse_errors.append(str(exc))
                        continue
                    index.symbols.extend(symbols)
                    index.imports.extend(imports)

        index.dependencies = dependency_list
        index.frameworks = deps_mod.detect_frameworks(dependency_list)
        index.readme_summary = _extract_readme_summary(root)
        index.api_routes = _detect_routes(index.symbols)
        index.db_models = _detect_db_models(index.symbols)

        return index
