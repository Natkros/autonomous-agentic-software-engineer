"""Regex-based, best-effort symbol extraction for TypeScript (.ts/.tsx).

IMPORTANT: this is NOT a real parse. esprima (used for plain JavaScript in
``javascript_extractor.py``) cannot parse TypeScript's type syntax, and no
pure-Python TypeScript parser is available, so full AST-based extraction for
TS/TSX is out of scope for this phase. This module recovers top-level
function/class/interface declarations and import statements with regular
expressions, which is reliable for typical top-level code but WILL miss or
misattribute symbols inside unusual formatting, multi-line signatures, or
deeply nested expressions. Treat its output as a best-effort index, not a
source of truth the way the Python/JavaScript AST extractors are.
"""
from __future__ import annotations

import re

from code_intelligence.ast_tools.symbols import ImportRecord, Symbol

_FUNCTION_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
)
_ARROW_CONST_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>",
    re.MULTILINE,
)
_CLASS_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE
)
_INTERFACE_RE = re.compile(r"^\s*export\s+interface\s+(\w+)", re.MULTILINE)
_IMPORT_RE = re.compile(
    r"^\s*import\s+(?:type\s+)?(?:\{([^}]*)\}|(\w+)|(\*\s+as\s+\w+))?\s*(?:,\s*\{([^}]*)\})?\s*from\s+[\"']([^\"']+)[\"']",
    re.MULTILINE,
)


def extract_symbols(source: str, file_path: str) -> tuple[list[Symbol], list[ImportRecord]]:
    symbols: list[Symbol] = []
    imports: list[ImportRecord] = []
    lines = source.splitlines()

    def line_of(offset: int) -> int:
        return source.count("\n", 0, offset) + 1

    for match in _FUNCTION_RE.finditer(source):
        ln = line_of(match.start())
        symbols.append(Symbol(name=match.group(1), kind="function", file_path=file_path, lineno=ln, end_lineno=ln))

    for match in _ARROW_CONST_RE.finditer(source):
        ln = line_of(match.start())
        symbols.append(Symbol(name=match.group(1), kind="function", file_path=file_path, lineno=ln, end_lineno=ln))

    for match in _CLASS_RE.finditer(source):
        ln = line_of(match.start())
        bases = [match.group(2)] if match.group(2) else []
        symbols.append(Symbol(name=match.group(1), kind="class", file_path=file_path, lineno=ln, end_lineno=ln, bases=bases))

    for match in _INTERFACE_RE.finditer(source):
        ln = line_of(match.start())
        symbols.append(Symbol(name=match.group(1), kind="interface", file_path=file_path, lineno=ln, end_lineno=ln))

    for match in _IMPORT_RE.finditer(source):
        ln = line_of(match.start())
        names = []
        for group in (match.group(1), match.group(2), match.group(4)):
            if group:
                names.extend(n.strip().split(" as ")[0].strip() for n in group.split(",") if n.strip())
        imports.append(ImportRecord(module=match.group(5), file_path=file_path, lineno=ln, names=names))

    return symbols, imports
