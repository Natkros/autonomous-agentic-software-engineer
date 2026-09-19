"""Real AST-based symbol extraction for JavaScript (.js/.jsx/.mjs/.cjs).

Uses ``esprima`` (a pure-Python ECMAScript parser) so results come from an
actual parse tree, not a regex guess. esprima does not understand TypeScript
type syntax, so ``.ts``/``.tsx`` files are handled separately by
``typescript_heuristic.py`` with that limitation documented explicitly.
"""
from __future__ import annotations

import esprima

from code_intelligence.ast_tools.symbols import ImportRecord, Symbol


class JavaScriptExtractionError(ValueError):
    pass


def _unwrap_declaration(node):
    """Export statements wrap the thing being exported; unwrap it."""
    if node.type in ("ExportNamedDeclaration", "ExportDefaultDeclaration"):
        return node.declaration
    return node


def extract_symbols(source: str, file_path: str) -> tuple[list[Symbol], list[ImportRecord]]:
    try:
        tree = esprima.parseModule(source, options={"loc": True, "jsx": True, "tolerant": True})
    except Exception as exc:  # esprima raises its own Error type
        raise JavaScriptExtractionError(f"{file_path}: {exc}") from exc

    symbols: list[Symbol] = []
    imports: list[ImportRecord] = []

    def visit_class(node, parent: str | None = None) -> None:
        bases = [node.superClass.name] if getattr(node, "superClass", None) is not None else []
        symbols.append(Symbol(
            name=node.id.name if node.id else "<anonymous>",
            kind="class",
            file_path=file_path,
            lineno=node.loc.start.line,
            end_lineno=node.loc.end.line,
            parent=parent,
            bases=bases,
        ))
        class_name = node.id.name if node.id else "<anonymous>"
        for member in node.body.body:
            if member.type == "MethodDefinition":
                fn = member.value
                symbols.append(Symbol(
                    name=member.key.name if hasattr(member.key, "name") else str(member.key.value),
                    kind="method",
                    file_path=file_path,
                    lineno=member.loc.start.line,
                    end_lineno=member.loc.end.line,
                    parent=class_name,
                ))

    def visit_function(node, name: str) -> None:
        symbols.append(Symbol(
            name=name,
            kind="function",
            file_path=file_path,
            lineno=node.loc.start.line,
            end_lineno=node.loc.end.line,
        ))

    for raw_node in tree.body:
        node = _unwrap_declaration(raw_node)
        if node is None:
            continue

        if node.type == "ClassDeclaration":
            visit_class(node)
        elif node.type == "FunctionDeclaration":
            visit_function(node, node.id.name if node.id else "<anonymous>")
        elif node.type == "VariableDeclaration":
            for decl in node.declarations:
                init = decl.init
                if init is not None and init.type in ("ArrowFunctionExpression", "FunctionExpression"):
                    if hasattr(decl.id, "name"):
                        visit_function(init, decl.id.name)
        elif node.type == "ImportDeclaration":
            names = []
            for spec in node.specifiers:
                if spec.type == "ImportDefaultSpecifier":
                    names.append(spec.local.name)
                elif spec.type == "ImportSpecifier":
                    names.append(spec.imported.name)
                elif spec.type == "ImportNamespaceSpecifier":
                    names.append(f"* as {spec.local.name}")
            imports.append(ImportRecord(
                module=node.source.value,
                file_path=file_path,
                lineno=node.loc.start.line,
                names=names,
            ))

    return symbols, imports
