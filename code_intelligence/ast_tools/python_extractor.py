"""AST-based symbol extraction for Python source files.

Uses the standard library ``ast`` module rather than text/regex heuristics,
so results are structurally correct (a function named inside a string or
comment is never mistaken for a real definition).
"""
from __future__ import annotations

import ast

from code_intelligence.ast_tools.symbols import ImportRecord, Symbol


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ast.dump(node)


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_base_name(node.value)}.{node.attr}"
    return ast.dump(node)


class PythonExtractionError(ValueError):
    """Raised when a file cannot be parsed as valid Python."""


def extract_symbols(source: str, file_path: str) -> tuple[list[Symbol], list[ImportRecord]]:
    """Parse ``source`` and return every top-level/nested function, class,
    method, and import statement it defines.
    """
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        raise PythonExtractionError(f"{file_path}: {exc}") from exc

    symbols: list[Symbol] = []
    imports: list[ImportRecord] = []

    def visit_class(node: ast.ClassDef) -> None:
        symbols.append(Symbol(
            name=node.name,
            kind="class",
            file_path=file_path,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            decorators=[_decorator_name(d) for d in node.decorator_list],
            bases=[_base_name(b) for b in node.bases],
            docstring=ast.get_docstring(node),
        ))
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_function(item, parent=node.name)
            elif isinstance(item, ast.ClassDef):
                visit_class(item)

    def visit_function(node: ast.FunctionDef | ast.AsyncFunctionDef, parent: str | None = None) -> None:
        symbols.append(Symbol(
            name=node.name,
            kind="method" if parent else "function",
            file_path=file_path,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            parent=parent,
            decorators=[_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
        ))
        for item in ast.walk(node):
            if isinstance(item, ast.ClassDef) and item is not node:
                visit_class(item)

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            visit_class(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visit_function(node)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportRecord(
                    module=alias.name, file_path=file_path, lineno=node.lineno,
                    names=[alias.asname or alias.name],
                ))
        elif isinstance(node, ast.ImportFrom):
            imports.append(ImportRecord(
                module=node.module or "",
                file_path=file_path,
                lineno=node.lineno,
                names=[alias.name for alias in node.names],
                is_relative=node.level > 0,
            ))

    return symbols, imports
